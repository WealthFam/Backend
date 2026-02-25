import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/core/theme/app_theme.dart';
import 'package:mobile_app/modules/home/services/goals_service.dart';

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
      appBar: AppBar(
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
              : _buildInvestmentGoalsList(goalsService.goals),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          // TODO: Implement addition
        },
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildInvestmentGoalsList(List<dynamic> goals) {
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
}
