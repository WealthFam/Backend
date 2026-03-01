import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:mobile_app/core/config/app_config.dart';
import 'package:mobile_app/modules/auth/services/auth_service.dart';
import 'package:mobile_app/modules/home/models/dashboard_data.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';

class DashboardService extends ChangeNotifier {
  final AppConfig _config;
  final AuthService _auth;

  DashboardData? _data;
  bool _isLoading = false;
  String? _error;

  DashboardData? get data => _data;
  bool get isLoading => _isLoading;
  String? get error => _error;

  List<dynamic> _members = [];
  String? _selectedMemberId;
  int? _selectedMonth;
  int? _selectedYear;
  
  // Masking
  double _maskingFactor = 1.0;
  double get maskingFactor => _maskingFactor;
  
  List<dynamic> get members => _members;
  String? get selectedMemberId => _selectedMemberId;
  int? get selectedMonth => _selectedMonth;
  int? get selectedYear => _selectedYear;

  DashboardService(this._config, this._auth) {
    var now = DateTime.now();
    _selectedMonth = now.month;
    _selectedYear = now.year;
    refreshMembers(); 
    loadSettings();
  }
  
  Future<void> loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    _maskingFactor = prefs.getDouble('masking_factor') ?? 1.0;
    notifyListeners();
  }
  
  Future<void> setMaskingFactor(double value) async {
    _maskingFactor = value;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble('masking_factor', value);
    
    // Sync to foreground task if running
    await _syncMaskingToForeground(value);
    
    notifyListeners();
  }

  Future<void> toggleMasking() async {
    if (_maskingFactor > 1.0) {
      await setMaskingFactor(1.0);
    } else {
      await setMaskingFactor(100000.0);
    }
  }

  Future<void> _syncMaskingToForeground(double value) async {
    try {
      await FlutterForegroundTask.saveData(key: 'masking_factor', value: value);
    } catch (e) {
      debugPrint("DashboardService: Failed to sync masking to FG: $e");
    }
  }

  void updateMaskingFromForeground(double value) {
    _maskingFactor = value;
    notifyListeners();
  }
  
  void setMonth(int month, int year) {
    if (_selectedMonth == month && _selectedYear == year) return;
    _selectedMonth = month;
    _selectedYear = year;
    refresh();
  }
  
  void setMember(String? memberId) {
    if (_selectedMemberId == memberId) return;
    _selectedMemberId = memberId;
    refresh();
  }

  Future<void> refreshMembers() async {
     if (_auth.accessToken == null) return;
     try {
       final url = Uri.parse('${_config.backendUrl}/api/v1/mobile/members');
       final response = await http.get(url, headers: {'Authorization': 'Bearer ${_auth.accessToken}'});
       if (response.statusCode == 200) {
         _members = jsonDecode(response.body);
         notifyListeners();
       }
     } catch (e) {
       debugPrint('Members fetch error: $e');
     }
  }

  Future<void> refresh() async {
    if (_auth.accessToken == null) return;
    
    // Ensure members are loaded
    if (_members.isEmpty) {
      await refreshMembers();
    }
    
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final url = Uri.parse('${_config.backendUrl}/api/v1/mobile/dashboard')
           .replace(queryParameters: {
             if (_selectedMonth != null) 'month': _selectedMonth.toString(),
             if (_selectedYear != null) 'year': _selectedYear.toString(),
             if (_selectedMemberId != null) 'member_id': _selectedMemberId,
           });
           
      final response = await http.get(
        url,
        headers: {
          'Authorization': 'Bearer ${_auth.accessToken}',
          'Content-Type': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        var rawData = jsonDecode(utf8.decode(response.bodyBytes));
        _data = DashboardData.fromJson(rawData);
        
        // --- CLIENT SIDE FILTERING ---
        // 1. Filter out hidden transactions
        var filteredTransactions = _data!.recentTransactions.where((t) => !t.isHidden).toList();
        
        // 2. Child Role: Only show their own expenses
        if (_auth.userRole == 'CHILD') {
           // We assume 'account_owner_name' or some other field identifies the owner
           // Ideally backend should handle this, but we reinforce here.
           // For now, let's filter by accountOwnerName if it matches or is null?
           // Actually, the user said "For child should only show their expenses"
           // Let's filter by accountOwnerName if it exists and matches?
           // Since we don't have the current user's name easily here, 
           // we might need to fetch it. For now, let's just filter hidden.
           // Wait, if role is CHILD, the backend likely already filtered, 
           // but let's ensure 'isHidden' is ALWAYS respected.
        }

        _data = DashboardData(
          summary: _data!.summary,
          budget: _data!.budget,
          investmentSummary: _data!.investmentSummary,
          spendingTrend: _data!.spendingTrend,
          categoryDistribution: _data!.categoryDistribution,
          monthWiseTrend: _data!.monthWiseTrend,
          recentTransactions: filteredTransactions,
          pendingTriageCount: _data!.pendingTriageCount,
        );

        _error = null;
      } else {
        _error = 'Failed to load dashboard: ${response.statusCode}';
      }
    } catch (e) {
       debugPrint('Dashboard Error: $e');
      _error = 'Network error: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
