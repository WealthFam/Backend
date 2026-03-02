import 'package:flutter_foreground_task/flutter_foreground_task.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

@pragma('vm:entry-point')
void startCallback() {
  FlutterForegroundTask.setTaskHandler(SyncTaskHandler());
}

@pragma('vm:entry-point')
class SyncTaskHandler extends TaskHandler {
  int _eventCount = 0;

  @override
  @pragma('vm:entry-point')
  Future<void> onStart(DateTime timestamp, TaskStarter starter) async {
    // Immediate refresh on startup
    _updateNotificationAsync();
  }

  @override
  @pragma('vm:entry-point')
  void onRepeatEvent(DateTime timestamp) {
    _eventCount++;
    _updateNotificationAsync();
  }

  @override
  @pragma('vm:entry-point')
  void onNotificationButtonPressed(String id) async {
    debugPrint("ForegroundTask: Button pressed: $id");
    if (id == 'toggle_mask') {
      final currentFactor = await FlutterForegroundTask.getData<double>(key: 'masking_factor') ?? 1.0;
      final newFactor = currentFactor > 1.0 ? 1.0 : 500000.0; 
      
      await FlutterForegroundTask.saveData(key: 'masking_factor', value: newFactor);
      
      // Notify Main Isolate
      FlutterForegroundTask.sendDataToMain({
        'type': 'masking_update',
        'value': newFactor,
      });
      
      _updateNotificationAsync();
    } else if (id == 'refresh') {
      _updateNotificationAsync();
    }
  }

  @override
  @pragma('vm:entry-point')
  Future<void> onDestroy(DateTime timestamp, bool isTimeout) async {
    debugPrint("ForegroundTask: onDestroy (timeout: $isTimeout)");
  }

  @pragma('vm:entry-point')
  void _updateNotificationAsync() {
    () async {
      try {
        final url = await FlutterForegroundTask.getData<String>(key: 'backend_url');
        final token = await FlutterForegroundTask.getData<String>(key: 'access_token');
        
        if (url == null || token == null) {
          debugPrint("ForegroundTask: Credentials missing");
          return;
        }

        final response = await http.get(
          Uri.parse('$url/api/v1/mobile/mobile-summary'),
          headers: {'Authorization': 'Bearer $token'},
        ).timeout(const Duration(seconds: 15));

        if (response.statusCode == 200) {
          final data = jsonDecode(response.body);
          final rawToday = (data['today_total'] ?? 0.0).toDouble();
          final rawMonth = (data['monthly_total'] ?? 0.0).toDouble();
          
          final maskingFactor = await FlutterForegroundTask.getData<double>(key: 'masking_factor') ?? 1.0;
          
          final today = (rawToday / maskingFactor).toStringAsFixed(0);
          final month = (rawMonth / maskingFactor).toStringAsFixed(0);
          
          final symbol = '₹';
          final time = DateTime.now();
          final timeStr = "${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}";

          await FlutterForegroundTask.updateService(
            notificationTitle: 'WealthFam Guard',
            notificationText: 'Today: $symbol$today • Month: $symbol$month\nLast Updated: $timeStr',
          );

          // --- PUSH NOTIFICATION POLLING ---
          final alertsResponse = await http.get(
            Uri.parse('$url/api/v1/mobile/alerts'),
            headers: {'Authorization': 'Bearer $token'},
          ).timeout(const Duration(seconds: 5));

          if (alertsResponse.statusCode == 200) {
            final List alerts = jsonDecode(alertsResponse.body);
            if (alerts.isNotEmpty) {
              for (var alert in alerts) {
                final title = alert['title'] ?? 'Alert';
                final body = alert['body'] ?? '';
                
                await FlutterForegroundTask.updateService(
                  notificationTitle: '🔔 $title',
                  notificationText: body,
                );
                await Future.delayed(const Duration(seconds: 10));
              }
              // Re-show stats after all alerts are shown
              await FlutterForegroundTask.updateService(
                notificationTitle: 'WealthFam Guard',
                notificationText: 'Today: $symbol$today • Month: $symbol$month\nLast Updated: $timeStr',
              );
            }
          }
        } else {
          debugPrint("ForegroundTask: Server error ${response.statusCode}");
        }
      } catch (e) {
        debugPrint("ForegroundTask: Update error: $e");
      }
    }();
  }
}
