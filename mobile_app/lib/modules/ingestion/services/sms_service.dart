import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:mobile_app/core/config/app_config.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:telephony/telephony.dart';
import 'package:geolocator/geolocator.dart';
import 'package:mobile_app/modules/auth/services/auth_service.dart';
import 'package:mobile_app/core/services/notification_service.dart';
import 'package:flutter_foreground_task/flutter_foreground_task.dart' as flutter_foreground_task;

import 'package:mobile_app/core/services/foreground_service.dart';

extension PlatformCheck on TargetPlatform {
  bool get shouldUseTelephony => this == TargetPlatform.android;
}

// Top-level function for background execution
@pragma('vm:entry-point')
void backgroundMessageHandler(SmsMessage message) async {
  if (message.body == null || message.address == null) return;
  debugPrint("Background SMS: ${message.body}");
  
  try {
    // 1. Initialize Prefs
    final prefs = await SharedPreferences.getInstance();
    final isSyncEnabled = prefs.getBool('is_sync_enabled') ?? true;
    
    if (!isSyncEnabled) {
      debugPrint("Background SMS: Sync disabled");
      return;
    }

    final backendUrl = prefs.getString('backend_url');
    final accessToken = prefs.getString('access_token');
    final deviceId = prefs.getString('device_id') ?? 'BG_SERVICE';
    
    if (backendUrl == null || accessToken == null) {
      debugPrint("Background SMS: Missing credentials");
      // Queue for later? Complex in background. 
      // We rely on the app opening later and queuing via standard flow? 
      // Actually we can try to queue to 'sms_offline_queue' here
      return; 
    }

    // 2. Compute Hash (Duplicate logic from SmsService to avoid dependency issues)
    final date = message.date ?? DateTime.now().millisecondsSinceEpoch;
    final raw = "${message.address}-$date-${message.body}";
    final hash = sha256.convert(utf8.encode(raw)).toString();

    // 3. Check Cache
    if (prefs.containsKey('sms_hash_$hash')) {
       debugPrint("Background SMS: Already processed");
       return;
    }

    // 4. Try to get Location in background
    double? lat;
    double? lng;
    try {
      // Background location requires additional permissions and might be slow.
      // We check if we have permission first.
      Position? position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.low),
      ).timeout(const Duration(seconds: 5));
      if (position != null) {
        lat = position.latitude;
        lng = position.longitude;
      }
    } catch (e) {
      debugPrint("Background SMS: Location fetch failed: $e");
    }

    // 5. Send to Backend
    final url = Uri.parse('$backendUrl/api/v1/ingestion/sms');
    final response = await http.post(
      url,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $accessToken',
      },
      body: jsonEncode({
        'sender': message.address,
        'message': message.body,
        'device_id': deviceId, 
        'latitude': lat,
        'longitude': lng,
      }),
    );

    if (response.statusCode == 200 || response.statusCode == 201) {
       debugPrint("Background SMS: Sent successfully");
       // 5. Cache Hash
       await prefs.setBool('sms_hash_$hash', true);
       
       // Update stats if we can
       final current = prefs.getInt('msgs_synced_today') ?? 0;
       await prefs.setInt('msgs_synced_today', current + 1);
    } else {
       debugPrint("Background SMS: Failed ${response.statusCode}");
       // Add to offline queue
       final queue = prefs.getStringList('sms_offline_queue') ?? [];
       final item = {
          'address': message.address,
          'body': message.body,
          'date': date,
          'timestamp': DateTime.now().millisecondsSinceEpoch,
       };
       queue.add(jsonEncode(item));
       await prefs.setStringList('sms_offline_queue', queue);
    }
  } catch (e) {
     debugPrint("Background SMS Error: $e");
  }
}

class SmsService extends ChangeNotifier {
  final AppConfig _config;
  final AuthService _auth;

  final Telephony _telephony = Telephony.instance;
  late SharedPreferences _prefs;

  bool _isSyncEnabled = true;
  bool _isForegroundServiceEnabled = false;

  // Stats
  DateTime? _lastSyncTime;
  int _messagesSyncedToday = 0;
  String? _lastSyncStatus;

  bool get isSyncEnabled => _isSyncEnabled;
  bool get isForegroundServiceEnabled => _isForegroundServiceEnabled;
  DateTime? get lastSyncTime => _lastSyncTime;
  int get messagesSyncedToday => _messagesSyncedToday;
  String? get lastSyncStatus => _lastSyncStatus;
  int get queueCount => (_prefs.getStringList(keyQueue) ?? []).length;

  SmsService(this._config, this._auth);

  Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
    _isSyncEnabled = _prefs.getBool('is_sync_enabled') ?? true;
    _isForegroundServiceEnabled = _prefs.getBool('fg_service_enabled') ?? false;
    _messagesSyncedToday = _prefs.getInt('msgs_synced_today') ?? 0;
    final lastSyncMs = _prefs.getInt('last_sync_time');
    if (lastSyncMs != null) {
       _lastSyncTime = DateTime.fromMillisecondsSinceEpoch(lastSyncMs);
       final now = DateTime.now();
       if (_lastSyncTime!.day != now.day || _lastSyncTime!.month != now.month || _lastSyncTime!.year != now.year) {
         _messagesSyncedToday = 0;
         _prefs.setInt('msgs_synced_today', 0);
       }
    }
    
    if (kIsWeb || !defaultTargetPlatform.shouldUseTelephony) {
       debugPrint("SMS features disabled: Not on Android.");
       return;
    }

    final bool? result = await _telephony.requestPhoneAndSmsPermissions;
    if (result == true) {
      // Also request location permissions to ensure we can send location with SMS
      await _requestLocationPermissions();
      
      _startListening();
      if (_isForegroundServiceEnabled && _auth.accessToken != null) {
        await _saveCredentials();
        ForegroundServiceWrapper.start(
          url: _config.backendUrl,
          token: _auth.accessToken!,
        );
      }
      
      // Retry any queued messages from previous sessions
      retryQueue();
    }

    // Listen for config changes (e.g. backend URL update)
    _config.addListener(_handleConfigChange);
  }

  void _handleConfigChange() {
    if (_isForegroundServiceEnabled && _auth.accessToken != null) {
      debugPrint("SmsService: Config changed, updating foreground service...");
      _saveCredentials();
      ForegroundServiceWrapper.start(
        url: _config.backendUrl,
        token: _auth.accessToken!,
      );
    }
  }

  @override
  void dispose() {
    _config.removeListener(_handleConfigChange);
    super.dispose();
  }

  Future<void> toggleSync(bool enabled) async {
    _isSyncEnabled = enabled;
    await _prefs.setBool('is_sync_enabled', enabled);
    if (enabled) {
      retryQueue();
    }
    notifyListeners();
  }

  Future<void> toggleForegroundService(bool enabled) async {
    _isForegroundServiceEnabled = enabled;
    await _prefs.setBool('fg_service_enabled', enabled);

    if (enabled) {
      if (_auth.accessToken == null) {
        _isForegroundServiceEnabled = false;
        await _prefs.setBool('fg_service_enabled', false);
        notifyListeners();
        throw Exception("Authentication required to start sync service");
      }
      await _saveCredentials();
      
      // Attempt to start - on Android 14+ this may return false but still start successfully
      await ForegroundServiceWrapper.start(
        url: _config.backendUrl,
        token: _auth.accessToken!,
      );
      // Don't throw error based on return value - Android 14+ often returns false even on success
    } else {
      await ForegroundServiceWrapper.stop();
    }
    notifyListeners();
  }

  Future<void> _requestLocationPermissions() async {
    try {
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      
      if (permission == LocationPermission.always || permission == LocationPermission.whileInUse) {
        debugPrint("Location permissions granted");
      }
    } catch (e) {
      debugPrint("Error requesting location permissions: $e");
    }
  }

  void _startListening() {
    _telephony.listenIncomingSms(
      onNewMessage: (SmsMessage message) {
        _handleSms(message);
      },
      onBackgroundMessage: backgroundMessageHandler,
    );
  }

  Future<void> _handleSms(SmsMessage message) async {
    if (message.body == null || message.address == null) return;
    await processSms(message.address!, message.body!, message.date ?? DateTime.now().millisecondsSinceEpoch);
  }

  Future<Map<String, dynamic>> processSms(String address, String body, int date) async {
    if (!_isSyncEnabled) {
       return {'status': 'disabled', 'reason': 'Sync disabled'};
    }

    final String hash = _computeHash(address, date.toString(), body);
    
    if (_isCached(hash)) {
      return {'status': 'cached', 'hash': hash};
    }

    try {
      final res = await _sendToBackend(address, body, date);
      await _cacheHash(hash);
      _updateSyncStats(true);
      return res;
    } catch (e) {
      debugPrint("Failed to send SMS to backend: $e");
      _updateSyncStats(false);
      // Queue for offline Retry (Step 6 requirement)
      _queueForRetry(address, body, date);
      rethrow; // Rethrow for UI to see error if manual
    }
  }

  String computeHash(String address, String date, String body) {
    final raw = "$address-$date-$body";
    return sha256.convert(utf8.encode(raw)).toString();
  }

  String _computeHash(String address, String date, String body) => computeHash(address, date, body);

  bool isCached(String hash) {
    return _prefs.containsKey('sms_hash_$hash');
  }

  bool _isCached(String hash) => isCached(hash);

  Future<void> cacheHash(String hash) async {
    await _prefs.setBool('sms_hash_$hash', true);
  }

  Future<void> _cacheHash(String hash) async => cacheHash(hash);
  
  // Ensure credentials are saved for Background Isolate
  Future<void> _saveCredentials() async {
     await _prefs.setString('backend_url', _config.backendUrl);
     await _prefs.setString('device_id', _auth.deviceId ?? 'unknown');
     if (_auth.accessToken != null) {
        await _prefs.setString('access_token', _auth.accessToken!);
     }
  }
  
  Future<void> clearCache() async {
    final keys = _prefs.getKeys().where((k) => k.startsWith('sms_hash_'));
    for (final key in keys) {
      await _prefs.remove(key);
    }
    notifyListeners();
  }

  Future<Map<String, dynamic>> _sendToBackend(String address, String body, int date) async {
    if (!_auth.isAuthenticated || _auth.accessToken == null) {
      throw Exception("Not Authenticated");
    }

    // Get Location if possible
    double? lat;
    double? lng;
    try {
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      
      if (permission == LocationPermission.whileInUse || permission == LocationPermission.always) {
        Position position = await Geolocator.getCurrentPosition(
          locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
        ).timeout(const Duration(seconds: 10));
        lat = position.latitude;
        lng = position.longitude;
      }
    } catch (e) {
      debugPrint("SmsService: Error getting location: $e");
    }

    final url = Uri.parse('${_config.backendUrl}/api/v1/ingestion/sms');
    
    final response = await http.post(
      url,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ${_auth.accessToken}',
      },
      body: jsonEncode({
        'sender': address,
        'message': body,
        'device_id': _auth.deviceId,
        'latitude': lat,
        'longitude': lng,
      }),
    );

    if (response.statusCode != 200 && response.statusCode != 201) {
      final detail = jsonDecode(response.body)['detail'] ?? 'Backend Error';
      throw Exception("$detail (${response.statusCode})");
    }

    return jsonDecode(response.body);
  }

  // --- Offline Queue Logic ---
  static const String keyQueue = 'sms_offline_queue';

  Future<void> _queueForRetry(String address, String body, int date) async {
    final List<String> queue = _prefs.getStringList(keyQueue) ?? [];
    
    final item = {
      'address': address,
      'body': body,
      'date': date,
      'timestamp': DateTime.now().millisecondsSinceEpoch,
    };
    
    queue.add(jsonEncode(item));
    await _prefs.setStringList(keyQueue, queue);
    notifyListeners();
  }

  Future<void> retryQueue() async {
    final List<String> queue = _prefs.getStringList(keyQueue) ?? [];
    if (queue.isEmpty) return;

    final List<String> remaining = [];
    int successCount = 0;

    for (final itemStr in queue) {
      try {
        final item = jsonDecode(itemStr);
        final address = item['address'];
        final body = item['body'];
        final date = item['date'];
        
        final hash = _computeHash(address, date.toString(), body);
        if (!_isCached(hash)) {
          await _sendToBackend(address, body, date);
           await _cacheHash(hash);
        }
        successCount++;
        _updateSyncStats(true);
      } catch (e) {
        remaining.add(itemStr);
      }
    }
    
    await _prefs.setStringList(keyQueue, remaining);
    if (successCount > 0) notifyListeners();
  }
  
  // --- Manual Sync ---
  
  Future<int> syncLastHours(int hours) async {
    final cutoff = DateTime.now().subtract(Duration(hours: hours));
    return syncFromDate(cutoff);
  }
  
  Future<int> syncFromDate(DateTime fromDate) async {
    if (kIsWeb || !defaultTargetPlatform.shouldUseTelephony) {
       debugPrint("Manual Sync skipped: Not on Android.");
       return 0;
    }

    notifyListeners(); // Update UI loading state if binding
    
    final messages = await _telephony.getInboxSms(
      columns: [SmsColumn.ADDRESS, SmsColumn.BODY, SmsColumn.DATE],
    );
    
    final cutoffMs = fromDate.millisecondsSinceEpoch;
    
    int sent = 0;
    for (final msg in messages) {
       if (msg.date != null && msg.date! >= cutoffMs) {
         if (msg.body == null || msg.address == null) continue;
         
         final hash = _computeHash(msg.address!, msg.date.toString(), msg.body!);
         if (!_isCached(hash)) {
            try {
              await _sendToBackend(msg.address!, msg.body!, msg.date ?? 0);
              await _cacheHash(hash);
              sent++;
              _updateSyncStats(true);
            } catch (e) {
               _queueForRetry(msg.address!, msg.body!, msg.date ?? 0);
            }
         }
       }
    }
    return sent;
  }

  Future<List<SmsMessage>> getAllMessages() async {
    if (kIsWeb || !defaultTargetPlatform.shouldUseTelephony) return [];
    try {
      return await _telephony.getInboxSms(
        columns: [SmsColumn.ADDRESS, SmsColumn.BODY, SmsColumn.DATE],
      );
    } catch (e) {
      debugPrint("Error fetching SMS: $e");
      return [];
    }
  }

  Future<Map<String, dynamic>> sendSmsToBackend(String address, String body, int date) async {
    final res = await _sendToBackend(address, body, date);
    final hash = computeHash(address, date.toString(), body);
    await cacheHash(hash);
    _updateSyncStats(true);
    notifyListeners();
    return res;
  }

  void _updateSyncStats(bool success) {
    _lastSyncTime = DateTime.now();
    _prefs.setInt('last_sync_time', _lastSyncTime!.millisecondsSinceEpoch);
    
    if (success) {
      _messagesSyncedToday++;
      _prefs.setInt('msgs_synced_today', _messagesSyncedToday);
      _lastSyncStatus = "Success";
    } else {
      _lastSyncStatus = "Failed";
    }
    notifyListeners();
  }
}
