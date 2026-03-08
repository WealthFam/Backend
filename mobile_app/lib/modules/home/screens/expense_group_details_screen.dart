import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import 'package:intl/intl.dart';
import 'package:mobile_app/core/config/app_config.dart';
import 'package:mobile_app/core/theme/app_theme.dart';
import 'package:mobile_app/modules/auth/services/auth_service.dart';
import 'package:mobile_app/modules/home/services/categories_service.dart';
import 'package:mobile_app/modules/home/models/transaction_category.dart';
import 'package:mobile_app/modules/home/services/dashboard_service.dart';
import 'package:mobile_app/modules/home/screens/manage_group_transactions_screen.dart';

class ExpenseGroupDetailsScreen extends StatefulWidget {
  final dynamic group;
  const ExpenseGroupDetailsScreen({super.key, required this.group});

  @override
  State<ExpenseGroupDetailsScreen> createState() => _ExpenseGroupDetailsScreenState();
}

class _ExpenseGroupDetailsScreenState extends State<ExpenseGroupDetailsScreen> {
  late dynamic _group;
  List<dynamic> _transactions = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _group = widget.group;
    // Fetch categories and transactions
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<CategoriesService>().fetchCategories();
      refreshData();
    });
  }

  Future<void> refreshData() async {
    await Future.wait([
      _fetchGroupDetails(),
      fetchExpenseGroupTransactions(),
    ]);
  }

  Future<void> _fetchGroupDetails() async {
    final config = context.read<AppConfig>();
    final auth = context.read<AuthService>();

    try {
      final response = await http.get(
        Uri.parse('${config.backendUrl}/api/v1/mobile/expense-groups/${_group['id']}'),
        headers: {'Authorization': 'Bearer ${auth.accessToken}'},
      );

      if (response.statusCode == 200) {
        if (mounted) {
          setState(() {
            _group = jsonDecode(response.body);
          });
        }
      }
    } catch (e) {
      debugPrint('Error fetching group: $e');
    }
  }

  Future<void> fetchExpenseGroupTransactions() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    final config = context.read<AppConfig>();
    final auth = context.read<AuthService>();

    try {
      final url = Uri.parse('${config.backendUrl}/api/v1/mobile/transactions').replace(queryParameters: {
        'expense_group_id': widget.group['id'].toString(),
        'page_size': '100', // Load all relevant for the group
      });

      final response = await http.get(
        url,
        headers: {'Authorization': 'Bearer ${auth.accessToken}'},
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final List<dynamic> items = data['items'] ?? [];
        
        // Final sanity check filtering on client side too
        final filtered = items.where((t) {
          final gid = t['expense_group_id']?.toString();
          return gid == _group['id'].toString();
        }).toList();

        if (mounted) {
          setState(() {
            _transactions = filtered;
            _isLoading = false;
          });
        }
      } else {
        setState(() {
          _error = 'Failed to load transactions: ${response.statusCode}';
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

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final group = _group;
    final budget = (group['budget'] ?? 0.0).toDouble();
    
    // Calculate spent from transactions as the source of truth for this view
    // We only sum NEGATIVE amounts (debits/expenses)
    double spent = 0;
    for (var txn in _transactions) {
      final amt = (txn['amount'] as num).toDouble();
      if (amt < 0) {
        spent += amt.abs();
      }
    }
    
    final progress = budget > 0 ? (spent / budget).clamp(0.0, 1.0) : 0.0;
    final isOverBudget = spent > budget && budget > 0;
    final isActive = group['is_active'] ?? true;
    final currency = context.read<DashboardService>().data?.summary.currency ?? '₹';
    final maskingFactor = context.read<DashboardService>().maskingFactor;

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      appBar: AppBar(
        title: Text(group['name'] ?? 'Group Details'),
        actions: [
          if (!isActive)
            const Padding(
              padding: EdgeInsets.only(right: 16),
              child: Center(
                child: Text(
                  'INACTIVE',
                  style: TextStyle(color: Colors.grey, fontWeight: FontWeight.bold, fontSize: 10),
                ),
              ),
            ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: refreshData,
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: AppTheme.primary.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text(group['icon'] ?? '📁', style: const TextStyle(fontSize: 40)),
                        ),
                        const SizedBox(width: 20),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                group['name'] ?? 'Unnamed Group',
                                style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                              ),
                              if (group['description'] != null && group['description'].isNotEmpty)
                                Text(
                                  group['description'],
                                  style: TextStyle(color: theme.colorScheme.onSurfaceVariant),
                                ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    if (group['start_date'] != null || group['end_date'] != null)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        decoration: BoxDecoration(
                          color: theme.colorScheme.surface,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: theme.dividerColor.withOpacity(0.5)),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.calendar_today, size: 16, color: AppTheme.primary),
                            const SizedBox(width: 12),
                            Text(
                              '${group['start_date'] != null ? DateFormat('MMM d, yyyy').format(DateTime.parse(group['start_date'])) : "Start"} — ${group['end_date'] != null ? DateFormat('MMM d, yyyy').format(DateTime.parse(group['end_date'])) : "End"}',
                              style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500, color: theme.colorScheme.onSurface),
                            ),
                          ],
                        ),
                      ),
                    const SizedBox(height: 24),
                    _buildSummaryCard(theme, spent, budget, progress, isOverBudget, currency, maskingFactor),
                    const SizedBox(height: 32),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Linked Transactions',
                              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                            ),
                            Text(
                              '${_transactions.length} items',
                              style: TextStyle(color: theme.disabledColor, fontSize: 12),
                            ),
                          ],
                        ),
                        TextButton.icon(
                          onPressed: () async {
                            final result = await Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => ManageGroupTransactionsScreen(group: _group),
                              ),
                            );
                            if (result == true) {
                              refreshData();
                            }
                          },
                          icon: const Icon(Icons.edit_note, size: 20),
                          label: const Text('Manage'),
                          style: TextButton.styleFrom(
                            foregroundColor: AppTheme.primary,
                            backgroundColor: AppTheme.primary.withOpacity(0.1),
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                  ],
                ),
              ),
            ),
            if (_isLoading)
              const SliverFillRemaining(child: Center(child: CircularProgressIndicator()))
            else if (_error != null)
              SliverFillRemaining(child: Center(child: Text(_error!, style: const TextStyle(color: AppTheme.danger))))
            else if (_transactions.isEmpty)
              SliverFillRemaining(
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.receipt_long_outlined, size: 64, color: theme.dividerColor),
                      const SizedBox(height: 16),
                      Text('No transactions linked to this group', style: TextStyle(color: theme.colorScheme.onSurfaceVariant)),
                    ],
                  ),
                ),
              )
            else
              SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, index) {
                    final txn = _transactions[index];
                    return _buildTransactionTile(context, txn, currency, maskingFactor);
                  },
                  childCount: _transactions.length,
                ),
              ),
            const SliverToBoxAdapter(child: SizedBox(height: 40)),
          ],
        ),
      ),
    );
  }

  Widget _buildSummaryCard(
    ThemeData theme, 
    double spent, 
    double budget, 
    double progress, 
    bool isOverBudget, 
    String currency,
    double maskingFactor
  ) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: theme.dividerColor),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.02),
            blurRadius: 10,
            offset: const Offset(0, 4),
          )
        ],
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Total Spent', style: TextStyle(color: Colors.grey, fontSize: 12)),
                  const SizedBox(height: 4),
                  Text(
                    '$currency${(spent / maskingFactor).toStringAsFixed(2)}',
                    style: TextStyle(
                      fontSize: 24, 
                      fontWeight: FontWeight.bold,
                      color: isOverBudget ? AppTheme.danger : theme.colorScheme.onSurface,
                    ),
                  ),
                ],
              ),
              if (budget > 0)
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    const Text('Total Budget', style: TextStyle(color: Colors.grey, fontSize: 12)),
                    const SizedBox(height: 4),
                    Text(
                      '$currency${(budget / maskingFactor).toStringAsFixed(0)}',
                      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
            ],
          ),
          if (budget > 0) ...[
            const SizedBox(height: 24),
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(
                value: progress,
                minHeight: 12,
                backgroundColor: (isOverBudget ? AppTheme.danger : AppTheme.primary).withOpacity(0.1),
                valueColor: AlwaysStoppedAnimation<Color>(isOverBudget ? AppTheme.danger : AppTheme.primary),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '${(progress * 100).toStringAsFixed(1)}% consumed',
                  style: TextStyle(fontSize: 12, color: theme.colorScheme.onSurfaceVariant),
                ),
                if (isOverBudget)
                  const Text(
                    'OVER BUDGET',
                    style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppTheme.danger),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildTransactionTile(BuildContext context, dynamic txn, String currency, double maskingFactor) {
    final theme = Theme.of(context);
    final amount = (txn['amount'] as num).toDouble();
    final date = DateTime.parse(txn['date']).toLocal();

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: theme.dividerColor.withOpacity(0.5)),
      ),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        leading: Consumer<CategoriesService>(
          builder: (context, catService, _) {
            final catName = (txn['category'] as String?) ?? 'Uncategorized';
            final matched = catService.categories
                .cast<TransactionCategory?>()
                .firstWhere(
                  (c) => c?.name.toLowerCase() == catName.toLowerCase(),
                  orElse: () => null,
                );
            
            if (matched?.icon != null) {
              return CircleAvatar(
                backgroundColor: theme.primaryColor.withOpacity(0.1),
                child: Text(matched!.icon!, style: const TextStyle(fontSize: 20)),
              );
            }
            
            return CircleAvatar(
              backgroundColor: theme.primaryColor.withOpacity(0.1),
              child: const Icon(Icons.receipt_long, color: AppTheme.primary),
            );
          },
        ),
        title: Text(
          txn['description'],
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
        ),
        subtitle: Text(
          DateFormat('dd MMM yyyy, HH:mm').format(date),
          style: TextStyle(fontSize: 12, color: theme.colorScheme.onSurfaceVariant),
        ),
        trailing: Text(
          '$currency${(amount.abs() / maskingFactor).toStringAsFixed(1)}',
          style: TextStyle(
            fontWeight: FontWeight.bold,
            color: amount < 0 ? AppTheme.danger : AppTheme.success,
          ),
        ),
      ),
    );
  }
}
