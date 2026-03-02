import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/core/theme/app_theme.dart';
import 'package:mobile_app/modules/home/services/goals_service.dart';
import 'package:mobile_app/core/widgets/app_shell.dart';

class GoalsScreen extends StatefulWidget {
  const GoalsScreen({super.key});

  @override
  State<GoalsScreen> createState() => _GoalsScreenState();
}

class _GoalsScreenState extends State<GoalsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<GoalsService>().fetchGoals();
    });
  }

  @override
  Widget build(BuildContext context) {
    final goalsService = context.watch<GoalsService>();

    return Scaffold(
      drawer: const AppDrawer(),
      appBar: AppBar(
        leading: const DrawerMenuButton(),
        title: const Text('Investment Goals'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              goalsService.fetchGoals();
            },
          ),
        ],
      ),
      body: goalsService.isLoading
          ? const Center(child: CircularProgressIndicator())
          : goalsService.error != null
              ? Center(child: Padding(
                  padding: const EdgeInsets.all(32),
                  child: Text(goalsService.error!, style: const TextStyle(color: Colors.red), textAlign: TextAlign.center),
                ))
              : _buildInvestmentGoalsList(goalsService, goalsService.goals),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showAddGoalDialog(context),
        child: const Icon(Icons.add),
      ),
    );
  }

  void _showAddGoalDialog(BuildContext context) {
    final nameController = TextEditingController();
    final targetController = TextEditingController();
    final descriptionController = TextEditingController();

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('New Investment Goal'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: nameController, decoration: const InputDecoration(labelText: 'Goal Name')),
            TextField(
              controller: targetController, 
              decoration: const InputDecoration(labelText: 'Target Amount'),
              keyboardType: TextInputType.number,
            ),
            TextField(controller: descriptionController, decoration: const InputDecoration(labelText: 'Description')),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          TextButton(
            onPressed: () async {
              final service = context.read<GoalsService>();
              final success = await service.createGoal({
                'name': nameController.text,
                'target_amount': double.tryParse(targetController.text) ?? 0,
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

  Widget _buildInvestmentGoalsList(GoalsService service, List<dynamic> goals) {
    if (goals.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.track_changes, size: 64, color: AppTheme.primary.withOpacity(0.5)),
            const SizedBox(height: 16),
            const Text('No investment goals found', style: TextStyle(fontWeight: FontWeight.bold)),
          ],
        ),
      );
    }

    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: goals.length,
      separatorBuilder: (_, __) => const SizedBox(height: 12),
      itemBuilder: (context, index) {
        final goal = goals[index];
        final double current = double.tryParse(goal['current_amount']?.toString() ?? '0') ?? 0;
        final double target = double.tryParse(goal['target_amount']?.toString() ?? '1') ?? 1;
        final progress = target > 0 ? current / target : 0.0;
        
        return Card(
          child: ListTile(
            onLongPress: () => _showDeleteConfirm(context, goal, service),
            title: Text(goal['name'] ?? 'Unnamed Goal', style: const TextStyle(fontWeight: FontWeight.bold)),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 8),
                LinearProgressIndicator(value: progress.clamp(0.0, 1.0)),
                const SizedBox(height: 4),
                Text('Target: ${target.toStringAsFixed(0)} | Current: ${current.toStringAsFixed(0)}'),
              ],
            ),
            isThreeLine: true,
          ),
        );
      },
    );
  }

  void _showDeleteConfirm(BuildContext context, dynamic goal, GoalsService service) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Goal?'),
        content: Text('Are you sure you want to delete "${goal['name']}"?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          TextButton(
            onPressed: () async {
              final success = await service.deleteGoal(goal['id'].toString());
              if (success && mounted) Navigator.pop(context);
            },
            child: const Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }
}
