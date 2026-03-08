import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:mobile_app/core/theme/app_theme.dart';
import 'package:mobile_app/modules/home/services/goals_service.dart';
import 'package:mobile_app/core/widgets/app_shell.dart';
import 'package:mobile_app/modules/home/screens/expense_group_details_screen.dart';

class ExpenseGroupsScreen extends StatefulWidget {
  const ExpenseGroupsScreen({super.key});

  @override
  State<ExpenseGroupsScreen> createState() => _ExpenseGroupsScreenState();
}

class _ExpenseGroupsScreenState extends State<ExpenseGroupsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<GoalsService>().fetchExpenseGroups();
    });
  }

  @override
  Widget build(BuildContext context) {
    final goalsService = context.watch<GoalsService>();
    final theme = Theme.of(context);

    return Scaffold(
      drawer: const AppDrawer(),
      appBar: AppBar(
        leading: const DrawerMenuButton(),
        title: const Text('Expense Groups'),
      ),
      body: RefreshIndicator(
        onRefresh: () => goalsService.fetchExpenseGroups(),
        child: goalsService.isLoading && goalsService.expenseGroups.isEmpty
            ? const Center(child: CircularProgressIndicator())
            : _buildExpenseGroupsList(goalsService, goalsService.expenseGroups),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showAddGroupDialog(context),
        child: const Icon(Icons.add),
      ),
    );
  }

  void _showAddGroupDialog(BuildContext context) {
    final nameController = TextEditingController();
    final descriptionController = TextEditingController();
    final budgetController = TextEditingController();
    final iconController = TextEditingController(text: '📁');

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('New Expense Group'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: iconController, 
                decoration: const InputDecoration(labelText: 'Icon (Emoji)', hintText: 'e.g. 🎒, 🏠'),
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 24),
              ),
              const SizedBox(height: 16),
              TextField(controller: nameController, decoration: const InputDecoration(labelText: 'Group Name', hintText: 'e.g. Goa Trip 2024')),
              const SizedBox(height: 8),
              TextField(controller: descriptionController, decoration: const InputDecoration(labelText: 'Description')),
              const SizedBox(height: 8),
              TextField(
                controller: budgetController, 
                decoration: const InputDecoration(labelText: 'Budget (Optional)', prefixText: '₹ '),
                keyboardType: TextInputType.number,
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () async {
              final service = context.read<GoalsService>();
              final success = await service.createExpenseGroup({
                'name': nameController.text,
                'description': descriptionController.text,
                'icon': iconController.text,
                'budget': double.tryParse(budgetController.text) ?? 0.0,
                'start_date': DateTime.now().toIso8601String(),
                'end_date': DateTime.now().add(const Duration(days: 30)).toIso8601String(),
              });
              if (success && mounted) Navigator.pop(context);
            },
            child: const Text('Create'),
          ),
        ],
      ),
    );
  }

  Widget _buildExpenseGroupsList(GoalsService service, List<dynamic> groups) {
    if (groups.isEmpty) {
      return ListView( // Needs to be scrollable for RefreshIndicator to work
        children: [
          SizedBox(height: MediaQuery.of(context).size.height * 0.3),
          Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.group_work_outlined, size: 80, color: AppTheme.primary.withOpacity(0.2)),
                const SizedBox(height: 24),
                Text('No expense groups found', 
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.grey[600])),
                const SizedBox(height: 8),
                const Text('Create a group for an event or shared trip', 
                  style: TextStyle(color: Colors.grey)),
              ],
            ),
          ),
        ],
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
      itemCount: groups.length,
      itemBuilder: (context, index) {
        final group = groups[index];
        final budget = (group['budget'] ?? 0.0).toDouble();
        final spent = (group['total_spend'] ?? 0.0).toDouble();
        final progress = budget > 0 ? (spent / budget).clamp(0.0, 1.0) : 0.0;
        final isOverBudget = spent > budget && budget > 0;
        final isActive = group['is_active'] ?? true;

        return Card(
          elevation: 0,
          margin: const EdgeInsets.only(bottom: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
            side: BorderSide(color: Colors.grey.withOpacity(0.1)),
          ),
          child: InkWell(
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => ExpenseGroupDetailsScreen(group: group),
                ),
              );
            },
            onLongPress: () => _showDeleteConfirm(context, group, service),
            borderRadius: BorderRadius.circular(16),
            child: Opacity(
              opacity: isActive ? 1.0 : 0.6,
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: AppTheme.primary.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: group['icon'] != null && group['icon'].isNotEmpty
                              ? Text(group['icon'], style: const TextStyle(fontSize: 24))
                              : const Icon(Icons.group_work, color: AppTheme.primary, size: 24),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Expanded(
                                  child: Text(
                                    group['name'] ?? 'Unnamed Group',
                                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
                                  ),
                                ),
                                  if (!isActive)
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                      decoration: BoxDecoration(
                                        color: Colors.grey[200],
                                        borderRadius: BorderRadius.circular(8),
                                      ),
                                      child: const Text(
                                        'Inactive',
                                        style: TextStyle(fontSize: 10, color: Colors.grey, fontWeight: FontWeight.bold),
                                      ),
                                    ),
                                ],
                              ),
                                if (group['description'] != null && group['description'].isNotEmpty)
                                  Text(
                                    group['description'],
                                    style: TextStyle(color: Colors.grey[600], fontSize: 13),
                                  ),
                                if (group['start_date'] != null || group['end_date'] != null)
                                  Padding(
                                    padding: const EdgeInsets.only(top: 4, bottom: 4),
                                    child: Row(
                                      children: [
                                        Icon(Icons.calendar_today_outlined, size: 11, color: Colors.grey[400]),
                                        const SizedBox(width: 4),
                                        Text(
                                          '${group['start_date'] != null ? DateFormat('MMM d, yyyy').format(DateTime.parse(group['start_date'])) : "..."}'
                                          ' - '
                                          '${group['end_date'] != null ? DateFormat('MMM d, yyyy').format(DateTime.parse(group['end_date'])) : "..."}',
                                          style: TextStyle(fontSize: 11, color: Colors.grey[600], fontWeight: FontWeight.w400),
                                        ),
                                      ],
                                    ),
                                  ),
                            ],
                          ),
                        ),
                        const Icon(Icons.chevron_right, color: Colors.grey),
                      ],
                    ),
                    if (budget > 0) ...[
                      const SizedBox(height: 20),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text('Spending Progress', style: TextStyle(color: Colors.grey[700], fontSize: 13, fontWeight: FontWeight.w500)),
                          Text(
                            '₹${spent.toStringAsFixed(0)} / ₹${budget.toStringAsFixed(0)}',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: isOverBudget ? AppTheme.danger : AppTheme.primary,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: progress,
                          minHeight: 8,
                          backgroundColor: (isOverBudget ? AppTheme.danger : AppTheme.primary).withOpacity(0.1),
                          valueColor: AlwaysStoppedAnimation<Color>(isOverBudget ? AppTheme.danger : AppTheme.primary),
                        ),
                      ),
                    ] else ...[
                      Row(
                        children: [
                          const Icon(Icons.wallet, size: 14, color: Colors.grey),
                          const SizedBox(width: 4),
                          Text('Total Spent: ₹${spent.toStringAsFixed(0)}', style: const TextStyle(color: Colors.grey, fontSize: 13)),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  void _showDeleteConfirm(BuildContext context, dynamic group, GoalsService service) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Group?'),
        content: Text('Are you sure you want to delete "${group['name']}"?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          TextButton(
            onPressed: () async {
              final success = await service.deleteExpenseGroup(group['id'].toString());
              if (success && mounted) Navigator.pop(context);
            },
            child: const Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }
}
