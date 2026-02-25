import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/core/theme/app_theme.dart';
import 'package:mobile_app/modules/home/services/goals_service.dart';

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

    return Scaffold(
      appBar: AppBar(
        title: const Text('Expense Groups'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              goalsService.fetchExpenseGroups();
            },
          ),
        ],
      ),
      body: goalsService.isLoading
          ? const Center(child: CircularProgressIndicator())
          : _buildExpenseGroupsList(goalsService.expenseGroups),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          // TODO: Implement addition
        },
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildExpenseGroupsList(List<dynamic> groups) {
    if (groups.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.account_balance_wallet, size: 64, color: AppTheme.primary.withOpacity(0.5)),
            const SizedBox(height: 16),
            const Text('No expense groups found', style: TextStyle(fontWeight: FontWeight.bold)),
          ],
        ),
      );
    }

    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: groups.length,
      separatorBuilder: (_, __) => const Divider(),
      itemBuilder: (context, index) {
        final group = groups[index];
        return ListTile(
          leading: const Icon(Icons.group_work, color: AppTheme.primary),
          title: Text(group['name'] ?? 'Unnamed Group', style: const TextStyle(fontWeight: FontWeight.bold)),
          subtitle: Text(group['description'] ?? 'No description'),
          trailing: const Icon(Icons.chevron_right),
        );
      },
    );
  }
}
