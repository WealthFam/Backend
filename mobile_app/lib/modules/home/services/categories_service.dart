import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:mobile_app/core/config/app_config.dart';
import 'package:mobile_app/modules/auth/services/auth_service.dart';
import 'package:mobile_app/modules/home/models/transaction_category.dart';
// for RecentTransaction update

class CategoriesService extends ChangeNotifier {
  final AppConfig _config;
  final AuthService _auth;

  List<TransactionCategory> _categories = [];
  bool _isLoading = false;

  List<TransactionCategory> get categories => _categories;
  bool get isLoading => _isLoading;

  CategoriesService(this._config, this._auth);

  Future<void> fetchCategories({bool force = false}) async {
    if (_auth.accessToken == null) return;
    
    // Check if we already have categories to avoid spamming
    if (!force && _categories.isNotEmpty) return;

    _isLoading = true;
    notifyListeners();

    try {
      final url = Uri.parse('${_config.backendUrl}/api/v1/mobile/categories');
      final response = await http.get(
        url,
        headers: {
          'Authorization': 'Bearer ${_auth.accessToken}',
        },
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        _categories = data.map((e) => TransactionCategory.fromJson(e)).toList();
      }
    } catch (e) {
      debugPrint('Fetch Categories Error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> updateTransactionCategory(String txnId, String newCategory, {bool createRule = false, List<String>? keywords}) async {
    try {
      final url = Uri.parse('${_config.backendUrl}/api/v1/mobile/transactions/$txnId');
      final response = await http.patch(
        url,
        headers: {
          'Authorization': 'Bearer ${_auth.accessToken}',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'category': newCategory,
          'create_rule': createRule,
          'rule_keywords': keywords ?? [],
        }),
      );

      return response.statusCode == 200;
    } catch (e) {
      debugPrint('Update Category Error: $e');
      return false;
    }
  }

  Future<bool> createCategory(String name, String type, {String? icon, String? parentId}) async {
    try {
      final url = Uri.parse('${_config.backendUrl}/api/v1/finance/categories');
      final response = await http.post(
        url,
        headers: {
          'Authorization': 'Bearer ${_auth.accessToken}',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'name': name,
          'type': type,
          'icon': icon,
          'parent_id': parentId,
        }),
      );
      if (response.statusCode == 200) {
         await fetchCategories(force: true);
         return true;
      }
      return false;
    } catch (e) {
      debugPrint('Create Category Error: $e');
      return false;
    }
  }

  Future<bool> updateCategory(String id, String name, String type, {String? icon, String? parentId}) async {
    try {
      final url = Uri.parse('${_config.backendUrl}/api/v1/finance/categories/$id');
      final response = await http.put(
        url,
        headers: {
          'Authorization': 'Bearer ${_auth.accessToken}',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'name': name,
          'type': type,
          'icon': icon,
          'parent_id': parentId,
        }),
      );
      if (response.statusCode == 200) {
         await fetchCategories(force: true);
         return true;
      }
      return false;
    } catch (e) {
      debugPrint('Update Category Error: $e');
      return false;
    }
  }

  Future<bool> deleteCategory(String id) async {
    try {
      final url = Uri.parse('${_config.backendUrl}/api/v1/finance/categories/$id');
      final response = await http.delete(
        url,
        headers: {
          'Authorization': 'Bearer ${_auth.accessToken}',
        },
      );
      if (response.statusCode == 200) {
         await fetchCategories(force: true);
         return true;
      }
      return false;
    } catch (e) {
      debugPrint('Delete Category Error: $e');
      return false;
    }
  }
}
