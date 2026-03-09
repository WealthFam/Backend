import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:mobile_app/core/config/app_config.dart';
import 'package:mobile_app/modules/auth/services/auth_service.dart';
import 'package:mobile_app/modules/home/models/dashboard_data.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';
import 'package:provider/provider.dart';
import 'package:flutter/widgets.dart';

class DashboardService extends ChangeNotifier {
  final AppConfig _config;
  final AuthService _auth;

  static DashboardService of(BuildContext context, {bool listen = true}) {
    return Provider.of<DashboardService>(context, listen: listen);
  }

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
  
  String get currencySymbol {
    final c = _data?.summary.currency ?? 'INR';
    return c == 'INR' ? '₹' : c;
  }

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
    
    // Load cached dashboard data
    final cachedData = prefs.getString('cached_dashboard_data');
    if (cachedData != null) {
      try {
        _data = DashboardData.fromJson(jsonDecode(cachedData));
      } catch (e) {
        debugPrint('DashboardService: Error loading cache: $e');
      }
    }
    
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
  
  String get _cacheKey => 'dashboard_cache_${_selectedYear}_${_selectedMonth}_${_selectedMemberId ?? 'all'}';

  Future<void> _loadCache() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final cachedJson = prefs.getString(_cacheKey);
      if (cachedJson != null) {
        _data = DashboardData.fromJson(jsonDecode(cachedJson));
        notifyListeners();
      }
    } catch (e) {
      debugPrint('DashboardService: Error loading cache: $e');
    }
  }

  Future<void> _saveCache() async {
    try {
      if (_data != null) {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString(_cacheKey, jsonEncode(_data!.toJson()));
      }
    } catch (e) {
      debugPrint('DashboardService: Error saving cache: $e');
    }
  }

  void setMonth(int month, int year) {
    if (_selectedMonth == month && _selectedYear == year) return;
    _selectedMonth = month;
    _selectedYear = year;
    _loadCache(); // Load immediately
    refresh();
  }
  
  void setMember(String? memberId) {
    if (_selectedMemberId == memberId) return;
    _selectedMemberId = memberId;
    _loadCache(); // Load immediately
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
    
    _isLoading = true;
    _error = null;
    notifyListeners();

    final List<Future> futures = [
      _fetchDashboardSummary(),
      _fetchDashboardTrends(),
      _fetchDashboardCategories(),
      _fetchDashboardInvestments(),
    ];

    try {
      if (_members.isEmpty) {
        futures.add(refreshMembers());
      }
      
      await Future.wait(futures);
      _error = null;
    } catch (e) {
      debugPrint('Dashboard Service Multi-Fetch Error: $e');
      _error = 'Some data failed to load';
    } finally {
      _isLoading = false;
      await _saveCache();
      notifyListeners();
    }
  }

  Future<void> _fetchDashboardSummary() async {
    final url = Uri.parse('${_config.backendUrl}/api/v1/mobile/dashboard/summary')
        .replace(queryParameters: _getQueryParams());
    
    final response = await http.get(url, headers: _getHeaders());
    if (response.statusCode == 200) {
      final data = jsonDecode(utf8.decode(response.bodyBytes));
      final summary = DashboardSummary.fromJson(data['summary']);
      final budget = BudgetSummary.fromJson(data['budget']);
      final txns = (data['recent_transactions'] as List)
          .map((i) => RecentTransaction.fromJson(i))
          .where((t) => !t.isHidden)
          .toList();
      
      _updateData((d) => d.copyWith(
        summary: summary,
        budget: budget,
        recentTransactions: txns,
        pendingTriageCount: data['pending_triage_count'],
        familyMembersCount: data['family_members_count'],
      ));
    }
  }

  Future<void> _fetchDashboardTrends() async {
    final url = Uri.parse('${_config.backendUrl}/api/v1/mobile/dashboard/trends')
        .replace(queryParameters: _getQueryParams());
    
    final response = await http.get(url, headers: _getHeaders());
    if (response.statusCode == 200) {
      final data = jsonDecode(utf8.decode(response.bodyBytes));
      final spendingTrend = (data['spending_trend'] as List)
          .map((i) => SpendingTrendItem.fromJson(i))
          .toList();
      final monthWiseTrend = (data['month_wise_trend'] as List)
          .map((i) => MonthTrendItem.fromJson(i))
          .toList();
      
      _updateData((d) => d.copyWith(
        spendingTrend: spendingTrend,
        monthWiseTrend: monthWiseTrend,
      ));
    }
  }

  Future<void> _fetchDashboardCategories() async {
    final url = Uri.parse('${_config.backendUrl}/api/v1/mobile/dashboard/categories')
        .replace(queryParameters: _getQueryParams());
    
    final response = await http.get(url, headers: _getHeaders());
    if (response.statusCode == 200) {
      final data = jsonDecode(utf8.decode(response.bodyBytes));
      final categories = (data['category_distribution'] as List)
          .map((i) => CategoryPieItem.fromJson(i))
          .toList();
      
      _updateData((d) => d.copyWith(categoryDistribution: categories));
    }
  }

  Future<void> _fetchDashboardInvestments() async {
    final url = Uri.parse('${_config.backendUrl}/api/v1/mobile/dashboard/investments')
        .replace(queryParameters: _getQueryParams());
    
    final response = await http.get(url, headers: _getHeaders());
    if (response.statusCode == 200) {
      final data = jsonDecode(utf8.decode(response.bodyBytes));
      InvestmentSummary? investmentSummary;
      if (data['investment_summary'] != null) {
        investmentSummary = InvestmentSummary.fromJson(data['investment_summary']);
      }
      
      _updateData((d) => d.copyWith(investmentSummary: investmentSummary));
    }
  }

  void _updateData(DashboardData Function(DashboardData) updater) {
    if (_data == null) {
      _data = DashboardData(
         summary: DashboardSummary(todayTotal: 0, monthlyTotal: 0, currency: 'INR'),
         budget: BudgetSummary(limit: 0, spent: 0, percentage: 0),
         spendingTrend: [],
         categoryDistribution: [],
         monthWiseTrend: [],
         recentTransactions: [],
       );
    }
    _data = updater(_data!);
    notifyListeners();
  }

  Map<String, String> _getQueryParams() {
    return {
      if (_selectedMonth != null) 'month': _selectedMonth.toString(),
      if (_selectedYear != null) 'year': _selectedYear.toString(),
      if (_selectedMemberId != null) 'member_id': _selectedMemberId!,
    };
  }

  Map<String, String> _getHeaders() {
    return {
      'Authorization': 'Bearer ${_auth.accessToken}',
      'Content-Type': 'application/json',
    };
  }
}
