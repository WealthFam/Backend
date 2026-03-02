import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/core/theme/app_theme.dart';
import 'package:mobile_app/modules/home/services/goals_service.dart';
import 'package:mobile_app/core/widgets/app_shell.dart';

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
      drawer: const AppDrawer(),
      appBar: AppBar(
        leading: const DrawerMenuButton(),
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
          : _buildExpenseGroupsList(goalsService, goalsService.expenseGroups),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showAddGroupDialog(context),
        child: const Icon(Icons.add),
      ),
    );
  }

  void _showAddGroupDialog(BuildContext context) {
    final nameController = TextEditingController();
    final descriptionController = TextEditingController();

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('New Expense Group'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: nameController, decoration: const InputDecoration(labelText: 'Group Name')),
            TextField(controller: descriptionController, decoration: const InputDecoration(labelText: 'Description')),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          TextButton(
            onPressed: () async {
              final service = context.read<GoalsService>();
              final success = await service.createExpenseGroup({
                'name': nameController.text,
                'description': descriptionController.text,
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
          onLongPress: () => _showDeleteConfirm(context, group, service),
          leading: const Icon(Icons.group_work, color: AppTheme.primary),
          title: Text(group['name'] ?? 'Unnamed Group', style: const TextStyle(fontWeight: FontWeight.bold)),
          subtitle: Text(group['description'] ?? 'No description'),
          trailing: const Icon(Icons.chevron_right),
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
