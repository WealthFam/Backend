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
import 'package:intl/intl.dart';

class TransactionReviewScreen extends StatefulWidget {
  const TransactionReviewScreen({super.key});

  @override
  State<TransactionReviewScreen> createState() => _TransactionReviewScreenState();
}

class _TransactionReviewScreenState extends State<TransactionReviewScreen> {
  List<RecentTransaction> _triageItems = [];
  bool _isLoading = true;
  String? _error;
  
  final Map<String, String> _selectedCategories = {};
  final Map<String, bool> _createRuleFlags = {};

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final config = context.read<AppConfig>();
      final auth = context.read<AuthService>();
      final url = Uri.parse('${config.backendUrl}/api/v1/ingestion/triage');
      final response = await http.get(url, headers: {'Authorization': 'Bearer ${auth.accessToken}'});
      
      if (response.statusCode == 200) {
        final List raw = jsonDecode(utf8.decode(response.bodyBytes))['data'] ?? [];
        final items = raw.map((i) => RecentTransaction.fromJson(i)).toList();
        
        setState(() {
          _triageItems = items;
          for (var item in _triageItems) {
            _selectedCategories[item.id] = item.category;
            _createRuleFlags[item.id] = true;
          }
          _isLoading = false;
        });
      } else {
        throw Exception('Failed to load reviews');
      }
    } catch (e) {
      setState(() { _error = e.toString(); _isLoading = false; });
    }
  }

  Future<void> _processTriage(String id, bool approve) async {
    final config = context.read<AppConfig>();
    final auth = context.read<AuthService>();

    try {
      if (approve) {
         final url = Uri.parse('${config.backendUrl}/api/v1/ingestion/triage/$id/approve');
         final response = await http.post(
           url,
           headers: {'Authorization': 'Bearer ${auth.accessToken}', 'Content-Type': 'application/json'},
           body: jsonEncode({
             'category': _selectedCategories[id] ?? 'Uncategorized',
             'create_rule': _createRuleFlags[id] ?? false,
           }),
         );
         if (response.statusCode != 200) throw Exception('Approval failed');
      } else {
         final url = Uri.parse('${config.backendUrl}/api/v1/ingestion/triage/$id');
         final response = await http.delete(url, headers: {'Authorization': 'Bearer ${auth.accessToken}'});
         if (response.statusCode != 200) throw Exception('Discard failed');
      }
      
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(approve ? 'Approved' : 'Discarded')));
      _loadData();
      context.read<DashboardService>().refresh();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Action failed: $e'), backgroundColor: AppTheme.danger));
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final count = context.watch<DashboardService>().data?.pendingTriageCount ?? 0;

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      appBar: AppBar(
        title: Text('Review Hub ($count)', style: const TextStyle(fontWeight: FontWeight.w900)),
        elevation: 0,
      ),
      body: _isLoading 
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!, style: const TextStyle(color: AppTheme.danger)))
              : _triageItems.isEmpty
                  ? _buildEmptyState()
                  : RefreshIndicator(
                      onRefresh: _loadData,
                      child: ListView.separated(
                        padding: const EdgeInsets.all(16),
                        itemCount: _triageItems.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 16),
                        itemBuilder: (context, index) => _buildTriageCard(_triageItems[index]),
                      ),
                    ),
    );
  }

  Widget _buildEmptyState() {
     return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.check_circle_outline, size: 80, color: AppTheme.success.withOpacity(0.2)),
          const SizedBox(height: 20),
          const Text('All Clear!', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
          const Text('No pending reviews for now.', style: TextStyle(color: Colors.grey)),
        ],
      ),
    );
  }

  Widget _buildTriageCard(RecentTransaction item) {
    final theme = Theme.of(context);
    final dashboard = context.read<DashboardService>();
    final categories = context.watch<CategoriesService>().categories;
    final category = _selectedCategories[item.id] ?? 'Uncategorized';
    final createRule = _createRuleFlags[item.id] ?? true;

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: Colors.black.withOpacity(0.06)),
        boxShadow: [
          BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 15, offset: const Offset(0, 6)),
          BoxShadow(color: (item.amount < 0 ? AppTheme.danger : AppTheme.success).withOpacity(0.02), blurRadius: 10, spreadRadius: -5),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(item.description, 
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, letterSpacing: -0.5),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(color: theme.scaffoldBackgroundColor, borderRadius: BorderRadius.circular(8)),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.account_balance_wallet_outlined, size: 12, color: theme.colorScheme.onSurfaceVariant.withOpacity(0.5)),
                          const SizedBox(width: 6),
                          Flexible(child: Text('${item.source ?? "Unknown Source"} • ${item.accountName ?? "Unknown"} • ${item.formattedDate}', 
                            style: TextStyle(color: theme.colorScheme.onSurfaceVariant.withOpacity(0.7), fontSize: 11, fontWeight: FontWeight.w600),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          )),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text('${dashboard.currencySymbol}${(item.amount.abs() / dashboard.maskingFactor).toStringAsFixed(0)}', 
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 20, color: item.amount < 0 ? AppTheme.danger : AppTheme.success, letterSpacing: -0.5)),
                  Text(item.amount < 0 ? 'DEBIT' : 'CREDIT', style: TextStyle(fontSize: 9, fontWeight: FontWeight.w900, letterSpacing: 0.5, color: (item.amount < 0 ? AppTheme.danger : AppTheme.success).withOpacity(0.5))),
                ],
              ),
            ],
          ),
          const SizedBox(height: 20),
          _buildCategoryPicker(item.id, category, categories),
          const SizedBox(height: 12),
          Row(
            children: [
              Transform.scale(scale: 0.8, child: Switch(
                value: createRule, 
                onChanged: (v) => setState(() => _createRuleFlags[item.id] = v), 
                activeColor: AppTheme.primary,
                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
              )),
              Text('Sync as Rule', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: theme.colorScheme.onSurfaceVariant.withOpacity(0.8))),
              const Spacer(),
              TextButton(
                onPressed: () => _processTriage(item.id, false), 
                style: TextButton.styleFrom(foregroundColor: AppTheme.danger, padding: const EdgeInsets.symmetric(horizontal: 16)),
                child: const Text('Discard', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                onPressed: () => _processTriage(item.id, true), 
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.success, 
                  foregroundColor: Colors.white, 
                  elevation: 0,
                  minimumSize: const Size(80, 36),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                ),
                child: const Text('Approve', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w900)),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildCategoryPicker(String itemId, String current, List<TransactionCategory> categories) {
    final theme = Theme.of(context);
    return InkWell(
      onTap: () {
         showModalBottomSheet(
          context: context,
          isScrollControlled: true,
          backgroundColor: Colors.transparent,
          builder: (context) => DraggableScrollableSheet(
            initialChildSize: 0.7,
            maxChildSize: 0.95,
            minChildSize: 0.5,
            builder: (_, controller) => SearchableCategoryPicker(
              categories: categories,
              selected: current,
              onSelected: (cat) {
                 setState(() => _selectedCategories[itemId] = cat);
                 Navigator.pop(context);
              },
              scrollController: controller,
            ),
          ),
        );
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(color: theme.scaffoldBackgroundColor, borderRadius: BorderRadius.circular(16)),
        child: Row(children: [Expanded(child: Text(current, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13))), const Icon(Icons.keyboard_arrow_down, size: 20)]),
      ),
    );
  }
}

class SearchableCategoryPicker extends StatefulWidget {
  final List<TransactionCategory> categories;
  final String selected;
  final Function(String) onSelected;
  final ScrollController scrollController;

  const SearchableCategoryPicker({super.key, required this.categories, required this.selected, required this.onSelected, required this.scrollController});

  @override
  State<SearchableCategoryPicker> createState() => _SearchableCategoryPickerState();
}

class _SearchableCategoryPickerState extends State<SearchableCategoryPicker> {
  String _searchQuery = "";
  
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final List<TransactionCategory> filteredDisplay = [];
    
    for (var parent in widget.categories) {
      final bool parentMatches = parent.name.toLowerCase().contains(_searchQuery.toLowerCase());
      final List<TransactionCategory> matchingSubs = parent.subcategories.where((s) => s.name.toLowerCase().contains(_searchQuery.toLowerCase())).toList();
      
      if (parentMatches || matchingSubs.isNotEmpty) {
        if (_searchQuery.isNotEmpty) {
          if (parentMatches) filteredDisplay.add(parent);
          filteredDisplay.addAll(matchingSubs);
        } else {
          filteredDisplay.add(parent);
          filteredDisplay.addAll(parent.subcategories);
        }
      }
    }

    return Container(
      decoration: BoxDecoration(color: theme.scaffoldBackgroundColor, borderRadius: const BorderRadius.vertical(top: Radius.circular(30))),
      child: Column(
        children: [
          const SizedBox(height: 12),
          Container(width: 40, height: 4, decoration: BoxDecoration(color: theme.dividerColor.withOpacity(0.1), borderRadius: BorderRadius.circular(2))),
          Padding(
            padding: const EdgeInsets.all(24),
            child: TextField(
              autofocus: true,
              decoration: InputDecoration(hintText: 'Search categories...', prefixIcon: const Icon(Icons.search), filled: true, fillColor: theme.colorScheme.surface, border: OutlineInputBorder(borderRadius: BorderRadius.circular(100), borderSide: BorderSide.none)),
              onChanged: (v) => setState(() => _searchQuery = v),
            ),
          ),
          Expanded(
            child: ListView.builder(
              controller: widget.scrollController,
              itemCount: filteredDisplay.length,
              itemBuilder: (context, index) {
                final cat = filteredDisplay[index];
                final bool isSub = cat.parentId != null;
                String? parentName;
                if (isSub) parentName = widget.categories.firstWhere((p) => p.id == cat.parentId, orElse: () => TransactionCategory(id: '', name: 'Parent', type: 'expense')).name;

                if (!isSub && _searchQuery.isEmpty) {
                   return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Padding(padding: const EdgeInsets.fromLTRB(24, 16, 24, 8), child: Text(cat.name.toUpperCase(), style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900, color: theme.primaryColor, letterSpacing: 1.2))),
                    _buildCatTile(cat, isSub: false),
                   ]);
                }
                return _buildCatTile(cat, isSub: isSub, parentName: parentName);
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCatTile(TransactionCategory cat, {bool isSub = false, String? parentName}) {
    final isSelected = widget.selected == cat.name;
    final theme = Theme.of(context);
    return ListTile(
      contentPadding: EdgeInsets.symmetric(horizontal: 24),
      leading: Padding(padding: EdgeInsets.only(left: isSub ? 16 : 0), child: Text(cat.icon ?? (isSub ? '🔹' : '🏷️'), style: TextStyle(fontSize: isSub ? 14 : 18))),
      title: Text(isSub && _searchQuery.isNotEmpty ? '${parentName!} > ${cat.name}' : cat.name, style: TextStyle(fontWeight: isSelected ? FontWeight.w900 : (isSub ? FontWeight.w500 : FontWeight.bold), fontSize: isSub ? 13 : 14, color: isSub ? theme.colorScheme.onSurfaceVariant : theme.colorScheme.onSurface)),
      trailing: isSelected ? Icon(Icons.check_circle, color: AppTheme.success, size: 20) : null,
      onTap: () => widget.onSelected(cat.name),
    );
  }
}
