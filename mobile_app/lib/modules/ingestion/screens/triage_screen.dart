import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import 'package:mobile_app/core/config/app_config.dart';
import 'package:mobile_app/core/theme/app_theme.dart';
import 'package:mobile_app/modules/auth/services/auth_service.dart';
import 'package:mobile_app/modules/home/models/dashboard_data.dart';
import 'package:mobile_app/modules/home/services/dashboard_service.dart';
import 'package:mobile_app/modules/home/services/categories_service.dart';
import 'package:mobile_app/modules/home/models/transaction_category.dart';

class TriageScreen extends StatefulWidget {
  const TriageScreen({super.key});

  @override
  State<TriageScreen> createState() => _TriageScreenState();
}

class _TriageScreenState extends State<TriageScreen> {
  List<RecentTransaction> _items = [];
  bool _isLoading = true;
  String? _error;
  
  // Local state for each triage item
  final Map<String, String> _selectedCategories = {};
  final Map<String, bool> _createRuleFlags = {};

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    await Future.wait([
      _loadTriage(),
      context.read<CategoriesService>().fetchCategories(),
    ]);
  }

  Future<void> _loadTriage() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final config = context.read<AppConfig>();
      final auth = context.read<AuthService>();

      final url = Uri.parse('${config.backendUrl}/api/v1/mobile/triage');
      final response = await http.get(
        url,
        headers: {
          'Authorization': 'Bearer ${auth.accessToken}',
        },
      );

      if (response.statusCode == 200) {
        final List<dynamic> raw = jsonDecode(utf8.decode(response.bodyBytes));
        setState(() {
          _items = raw.map((i) => RecentTransaction.fromJson(i)).toList();
          _isLoading = false;
          
          // Initialize local state
          for (var item in _items) {
             _selectedCategories[item.id] = item.category;
             _createRuleFlags[item.id] = true; // Default to true as it's helpful
          }
        });
      } else {
        setState(() {
          _error = 'Failed to load: ${response.statusCode}';
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _error = 'Error: $e';
        _isLoading = false;
      });
    }
  }

  Future<void> _processTriage(String id, bool approve) async {
    final config = context.read<AppConfig>();
    final auth = context.read<AuthService>();

    if (approve) {
       final url = Uri.parse('${config.backendUrl}/api/v1/ingestion/triage/$id/approve');
       final category = _selectedCategories[id] ?? 'Uncategorized';
       final createRule = _createRuleFlags[id] ?? false;

       try {
         final response = await http.post(
           url,
           headers: {
             'Authorization': 'Bearer ${auth.accessToken}',
             'Content-Type': 'application/json',
           },
           body: jsonEncode({
             'category': category,
             'create_rule': createRule,
           }),
         );

         if (response.statusCode == 200) {
           _onSuccess(approve);
         } else {
           _onFailure(response.statusCode);
         }
       } catch (e) {
         _onError(e);
       }
    } else {
       // Discard / Reject
       final url = Uri.parse('${config.backendUrl}/api/v1/ingestion/triage/$id');
       try {
         final response = await http.delete(
           url,
           headers: {
             'Authorization': 'Bearer ${auth.accessToken}',
           },
         );

         if (response.statusCode == 200) {
           _onSuccess(approve);
         } else {
           _onFailure(response.statusCode);
         }
       } catch (e) {
         _onError(e);
       }
    }
  }

  void _onSuccess(bool approve) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(approve ? 'Transaction Approved' : 'Transaction Discarded'))
    );
    _loadTriage();
    context.read<DashboardService>().refresh();
  }

  void _onFailure(int code) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Action failed: $code'), backgroundColor: AppTheme.danger)
    );
  }

  void _onError(Object e) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Error: $e'), backgroundColor: AppTheme.danger)
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      appBar: AppBar(
        title: const Text('Transaction Triage'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadTriage,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!, style: const TextStyle(color: AppTheme.danger)))
              : _items.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.check_circle_outline, size: 64, color: AppTheme.success.withOpacity(0.5)),
                          const SizedBox(height: 16),
                          const Text('All caught up!', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                          Text('No transactions need review.', style: TextStyle(color: theme.colorScheme.onSurfaceVariant)),
                        ],
                      ),
                    )
                  : ListView.separated(
                      padding: const EdgeInsets.all(16),
                      itemCount: _items.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 16),
                      itemBuilder: (context, index) {
                        final item = _items[index];
                        return _buildTriageCard(item);
                      },
                    ),
    );
  }

  Widget _buildTriageCard(RecentTransaction item) {
    final theme = Theme.of(context);
    final currency = context.read<DashboardService>().data?.summary.currency ?? '₹';
    final categories = context.watch<CategoriesService>().categories;
    final selectedCategory = _selectedCategories[item.id] ?? 'Uncategorized';
    final createRule = _createRuleFlags[item.id] ?? false;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: theme.dividerColor),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.03),
            blurRadius: 10,
            offset: const Offset(0, 4),
          )
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item.description,
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 17),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),
                    Text(item.formattedDate, style: TextStyle(color: theme.colorScheme.onSurfaceVariant, fontSize: 12)),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Text(
                '$currency${item.amount.abs().toStringAsFixed(2)}',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 20,
                  color: item.amount < 0 ? AppTheme.danger : AppTheme.success,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          _buildInfoRow(Icons.account_balance_wallet_outlined, '${item.accountOwnerName != null ? "${item.accountOwnerName} - " : ""}${item.accountName ?? 'Unknown Account'}'),
          const Divider(height: 32),
          
          const Text('Select Category', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.1)),
          const SizedBox(height: 12),
          
          _buildCategoryPicker(item.id, selectedCategory, categories),
          
          const SizedBox(height: 16),
          
          Row(
            children: [
              SizedBox(
                height: 24,
                width: 24,
                child: Checkbox(
                  value: createRule,
                  onChanged: (v) => setState(() => _createRuleFlags[item.id] = v ?? false),
                  activeColor: AppTheme.primary,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: GestureDetector(
                  onTap: () => setState(() => _createRuleFlags[item.id] = !createRule),
                  child: const Text('Save as auto-categorization rule', style: TextStyle(fontSize: 13)),
                ),
              ),
            ],
          ),

          const SizedBox(height: 24),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () => _processTriage(item.id, false),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: theme.colorScheme.error,
                    side: BorderSide(color: theme.colorScheme.error.withOpacity(0.3)),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  child: const Text('Discard'),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: ElevatedButton(
                  onPressed: () => _processTriage(item.id, true),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.success,
                    foregroundColor: Colors.white,
                    elevation: 0,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  child: const Text('Approve', style: TextStyle(fontWeight: FontWeight.bold)),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildInfoRow(IconData icon, String text) {
    final theme = Theme.of(context);
    return Row(
      children: [
        Icon(icon, size: 14, color: theme.colorScheme.onSurfaceVariant),
        const SizedBox(width: 6),
        Text(text, style: TextStyle(color: theme.colorScheme.onSurfaceVariant, fontSize: 13)),
      ],
    );
  }

  Widget _buildCategoryPicker(String itemId, String current, List<TransactionCategory> categories) {
    final theme = Theme.of(context);
    
    return InkWell(
      onTap: () => _showCategoryPicker(itemId, current, categories),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: theme.scaffoldBackgroundColor,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: theme.dividerColor),
        ),
        child: Row(
          children: [
            Expanded(
              child: Text(current, style: const TextStyle(fontWeight: FontWeight.w500)),
            ),
            const Icon(Icons.keyboard_arrow_down, size: 20),
          ],
        ),
      ),
    );
  }

  void _showCategoryPicker(String itemId, String current, List<TransactionCategory> categories) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (context) {
        return Container(
          padding: const EdgeInsets.symmetric(vertical: 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 24),
                child: Text('Choose Category', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              ),
              const SizedBox(height: 16),
              Flexible(
                child: ListView.builder(
                  shrinkWrap: true,
                  itemCount: categories.length,
                  itemBuilder: (context, index) {
                    final cat = categories[index];
                    final isSelected = cat.name == current;
                    return ListTile(
                      leading: Text(cat.icon ?? '🏷️', style: const TextStyle(fontSize: 20)),
                      title: Text(cat.name, style: TextStyle(fontWeight: isSelected ? FontWeight.bold : FontWeight.normal)),
                      trailing: isSelected ? const Icon(Icons.check, color: AppTheme.success) : null,
                      onTap: () {
                        setState(() => _selectedCategories[itemId] = cat.name);
                        Navigator.pop(context);
                      },
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
