import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/modules/ingestion/services/sms_service.dart';
import 'package:intl/intl.dart';
import 'package:mobile_app/core/theme/app_theme.dart';
import 'package:mobile_app/modules/home/services/dashboard_service.dart';
import 'package:mobile_app/modules/auth/services/auth_service.dart';
import 'package:mobile_app/modules/home/models/dashboard_data.dart';
import 'package:mobile_app/modules/home/screens/transaction_list_screen.dart';
import 'package:mobile_app/modules/home/screens/mutual_funds_screen.dart';
import 'package:mobile_app/modules/ingestion/screens/triage_screen.dart';
import 'package:mobile_app/modules/home/services/categories_service.dart';
import 'package:mobile_app/modules/home/models/transaction_category.dart';
import 'package:fl_chart/fl_chart.dart';

class DashboardScreen extends StatefulWidget {
  final VoidCallback? onMenuPressed;
  const DashboardScreen({super.key, this.onMenuPressed});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<DashboardService>().refresh();
    });
  }

  @override
  Widget build(BuildContext context) {
    final dashboard = context.watch<DashboardService>();
    final theme = Theme.of(context);
    final currencyFormat = NumberFormat.simpleCurrency(name: dashboard.data?.summary.currency ?? 'INR');

    // Helper to format with masking
    String formatAmount(double amount) {
       return currencyFormat.format(amount / dashboard.maskingFactor);
    }

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      body: RefreshIndicator(
        onRefresh: () => dashboard.refresh(),
        child: dashboard.isLoading && dashboard.data == null
            ? const Center(child: CircularProgressIndicator())
            : CustomScrollView(
                slivers: [
                                SliverAppBar(
                  floating: true,
                  pinned: true,
                  leading: widget.onMenuPressed != null ? IconButton(
                    icon: const Icon(Icons.menu),
                    onPressed: widget.onMenuPressed,
                  ) : null,
                  title: GestureDetector(
                    onDoubleTap: () {
                       dashboard.toggleMasking();
                       ScaffoldMessenger.of(context).showSnackBar(
                         SnackBar(
                           content: Text(dashboard.maskingFactor > 1.0 ? 'Privacy Masking ON (Panic Mode)' : 'Privacy Masking OFF'),
                           duration: const Duration(seconds: 1),
                         )
                       );
                    },
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'Overview',
                          style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                        ),
                        if (dashboard.maskingFactor > 1.0) ...[
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: AppTheme.warning.withOpacity(0.2),
                              borderRadius: BorderRadius.circular(4),
                              border: Border.all(color: AppTheme.warning.withOpacity(0.5)),
                            ),
                            child: const Text(
                              'PRIVACY',
                              style: TextStyle(
                                color: AppTheme.warning,
                                fontSize: 8,
                                fontWeight: FontWeight.bold,
                                letterSpacing: 0.5,
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  bottom: dashboard.data != null 
                    ? PreferredSize(
                        preferredSize: const Size.fromHeight(130),
                        child: _buildSummarySection(context, dashboard.data!.summary, formatAmount),
                      )
                    : null,
                  actions: [
                    if (dashboard.members.isNotEmpty) 
                       PopupMenuButton<String>(
                         icon: const Icon(Icons.people),
                         initialValue: dashboard.selectedMemberId,
                         onSelected: (val) => dashboard.setMember(val == 'all' ? null : val),
                         itemBuilder: (context) => <PopupMenuEntry<String>>[
                           const PopupMenuItem(value: 'all', child: Text('All Family')),
                           ...dashboard.members.map((m) => PopupMenuItem(
                             value: m['id'].toString(), 
                             child: Text(m['name']),
                           ))
                         ],
                       ),
                    IconButton(
                      icon: const Icon(Icons.calendar_month),
                      onPressed: () => _showMonthPicker(context),
                    ),
                    IconButton(
                      icon: const Icon(Icons.settings),
                      onPressed: () => _showSettingsDialog(context),
                    ),
                    IconButton(
                      icon: const Icon(Icons.refresh),
                      onPressed: () => dashboard.refresh(),
                    ),
                  ],
                ),
                if (dashboard.error != null)
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.all(20),
                      child: Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: AppTheme.danger.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AppTheme.danger.withOpacity(0.3)),
                        ),
                        child: Text(dashboard.error!, style: const TextStyle(color: AppTheme.danger)),
                      ),
                    ),
                  ),
                if (dashboard.data != null) ...[
                  SliverToBoxAdapter(child: _buildInvestmentsEntry(context)), // Restored Entry Point
                
                // Triage Banner
                if (dashboard.data!.pendingTriageCount > 0)
                  SliverToBoxAdapter(
                    child: _buildTriageBanner(context, dashboard.data!.pendingTriageCount),
                  ),

                  SliverToBoxAdapter(child: _buildBudgetSection(context, dashboard.data!.budget, formatAmount)),
                  SliverToBoxAdapter(child: _buildTopCategoriesSection(context, dashboard.data!, formatAmount)),
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(20, 24, 20, 12),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text('Recent Transactions', style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                          TextButton(
                            onPressed: () {
                               Navigator.push(context, MaterialPageRoute(builder: (_) => const TransactionListScreen()));
                            },
                            child: const Text('See All'),
                          ),
                        ],
                      ),
                    ),
                  ),
                  SliverList(
                    delegate: SliverChildBuilderDelegate(
                      (context, index) {
                        final txn = dashboard.data!.recentTransactions[index];
                        return _buildTransactionItem(context, txn, formatAmount);
                      },
                      childCount: dashboard.data!.recentTransactions.length,
                    ),
                  ),
                  SliverToBoxAdapter(child: _buildSyncHealthCard(context)),
                  const SliverToBoxAdapter(child: SizedBox(height: 32)),
                ],
              ],
            ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          Navigator.push(context, MaterialPageRoute(builder: (_) => const AddTransactionScreen()))
              .then((_) => dashboard.refresh());
        },
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildSummarySection(BuildContext context, DashboardSummary summary, Function(double) format) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Row(
        children: [
          Expanded(
            child: _buildSummaryCard(
              context,
              'This Month',
              format(summary.monthlyTotal),
              [const Color(0xFF6366F1), const Color(0xFF4F46E5)],
              Icons.calendar_month,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: _buildSummaryCard(
              context,
              'Today',
              format(summary.todayTotal),
              [const Color(0xFF10B981), const Color(0xFF059669)],
              Icons.today,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryCard(BuildContext context, String title, String amount, List<Color> colors, IconData icon) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: colors, begin: Alignment.topLeft, end: Alignment.bottomRight),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: colors.last.withOpacity(0.3),
            blurRadius: 12,
            offset: const Offset(0, 6),
          )
        ],
      ),
      child: Stack(
        children: [
          // Background Icon
          Positioned(
            right: -10,
            bottom: -10,
            child: Icon(icon, color: Colors.white.withOpacity(0.15), size: 80),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, color: Colors.white.withOpacity(0.8), size: 20),
              const SizedBox(height: 12),
              Text(title, style: TextStyle(color: Colors.white.withOpacity(0.8), fontSize: 13)),
              const SizedBox(height: 4),
              FittedBox(
                fit: BoxFit.scaleDown,
                child: Text(
                  amount,
                  style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildAnalysisTabs(BuildContext context, DashboardData data, Function(double) format) {
    return DefaultTabController(
      length: 2,
      child: Column(
        children: [
          const TabBar(
            tabs: [
              Tab(text: "Spending Trend"),
              Tab(text: "Distribution"),
            ],
          ),
          SizedBox(
            height: 300,
            child: TabBarView(
              children: [
                _buildTrendChart(context, data.spendingTrend, format),
                _buildPieChart(context, data.categoryDistribution, format),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTrendChart(BuildContext context, List<SpendingTrendItem> trend, Function(double) format) {
    if (trend.isEmpty) return const Center(child: Text("No Data"));
    
    final dashboard = context.read<DashboardService>(); 

    // Find max Y for scaling
    double maxY = 0;
    for (var item in trend) {
      if (item.amount > maxY) maxY = item.amount;
      if (item.dailyLimit > maxY) maxY = item.dailyLimit;
    }
    maxY = maxY * 1.2; 

    return Padding(
      padding: const EdgeInsets.only(right: 16, left: 12, top: 24, bottom: 12),
      child: LineChart(
        LineChartData(
          maxY: maxY,
          minY: 0,
          titlesData: FlTitlesData(
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true, 
                reservedSize: 40,
                getTitlesWidget: (value, meta) {
                   if (value == 0) return const SizedBox.shrink();
                   final val = value / dashboard.maskingFactor;
                   return Text(
                     NumberFormat.compact().format(val), 
                     style: const TextStyle(fontSize: 10, color: Colors.grey),
                   );
                },
              ),
            ),
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (value, meta) {
                  int idx = value.toInt();
                  if (idx >= 0 && idx < trend.length) {
                     // Check if it's start or end or reasonable step to avoid clutter
                     if (idx % 2 != 0 && idx != trend.length - 1) return const SizedBox.shrink(); 
                     
                     DateTime date = DateTime.parse(trend[idx].date);
                     return Padding(
                       padding: const EdgeInsets.only(top: 8.0),
                       child: Text(
                         DateFormat('d').format(date), 
                         style: const TextStyle(fontSize: 10, color: Colors.grey),
                       ),
                     );
                  }
                  return const SizedBox.shrink();
                },
              ),
            ),
          ),
          borderData: FlBorderData(show: false),
          gridData: const FlGridData(show: true, drawVerticalLine: false),
          lineBarsData: [
            // Spending Line
            LineChartBarData(
              spots: trend.asMap().entries.map((e) => FlSpot(e.key.toDouble(), e.value.amount)).toList(),
              isCurved: true,
              color: AppTheme.primary,
              barWidth: 3,
              isStrokeCapRound: true,
              dotData: const FlDotData(show: true),
              belowBarData: BarAreaData(
                show: true,
                color: AppTheme.primary.withOpacity(0.15),
                gradient: LinearGradient(
                  colors: [AppTheme.primary.withOpacity(0.3), AppTheme.primary.withOpacity(0.05)],
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                ),
              ),
            ),
            // Daily Limit Line (dashed)
            LineChartBarData(
              spots: trend.asMap().entries.map((e) => FlSpot(e.key.toDouble(), e.value.dailyLimit)).toList(),
              isCurved: false, 
              color: AppTheme.success.withOpacity(0.5),
              barWidth: 2,
              dashArray: [5, 5],
              dotData: const FlDotData(show: false),
            ),
          ],
          lineTouchData: LineTouchData(
            touchTooltipData: LineTouchTooltipData(
              getTooltipItems: (touchedSpots) {
                return touchedSpots.map((LineBarSpot touchedSpot) {
                   if (touchedSpot.barIndex == 1) return null; // Skip limit tooltip
                   final idx = touchedSpot.x.toInt();
                   if (idx < 0 || idx >= trend.length) return null;
                   
                   final date = DateTime.parse(trend[idx].date);
                   final amount = trend[idx].amount / dashboard.maskingFactor;
                   
                   return LineTooltipItem(
                     '${DateFormat('MMM d').format(date)}\n${NumberFormat.compactCurrency(symbol: '₹').format(amount)}',
                     const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                   );
                }).toList();
              },
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildPieChart(BuildContext context, List<CategoryPieItem> distribution, Function(double) format) {
     if (distribution.isEmpty) return const Center(child: Text("No Data"));
     
     // Generate colors dynamically if not provided
     final List<Color> colors = [
       const Color(0xFF4F46E5), const Color(0xFF10B981), const Color(0xFFF59E0B), 
       const Color(0xFFEF4444), const Color(0xFF8B5CF6), const Color(0xFFEC4899),
       const Color(0xFF6366F1), const Color(0xFF14B8A6),
     ];
     
     return Row(
       children: [
         Expanded(
           flex: 2,
           child: PieChart(
             PieChartData(
               sectionsSpace: 2,
               centerSpaceRadius: 40,
               sections: distribution.asMap().entries.map((entry) {
                 final index = entry.key;
                 final item = entry.value;
                 final color = colors[index % colors.length];
                 
                 return PieChartSectionData(
                   color: color,
                   value: item.value,
                   title: '${(item.value / distribution.fold(0.0, (p,c) => p + c.value) * 100).toStringAsFixed(0)}%',
                   radius: 50,
                   titleStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white),
                 );
               }).toList(),
             ),
           ),
         ),
         Expanded(
           flex: 1,
           child: ListView.builder(
             itemCount: distribution.length,
             itemBuilder: (context, index) {
                final item = distribution[index];
                final color = colors[index % colors.length];
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(
                    children: [
                       Container(width: 12, height: 12, color: color),
                       const SizedBox(width: 8),
                       Expanded(child: Text(item.name, style: const TextStyle(fontSize: 12), overflow: TextOverflow.ellipsis)),
                    ],
                  ),
                );
             },
           ),
         ),
       ],
     );
  }

  Widget _buildInvestmentsEntry(BuildContext context) {
    if (context.read<AuthService>().userRole == 'CHILD') return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      child: GestureDetector(
        onTap: () {
          Navigator.push(context, MaterialPageRoute(builder: (_) => const MutualFundsScreen()));
        },
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF0F172A), Color(0xFF1E293B)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF0F172A).withOpacity(0.3),
                blurRadius: 10,
                offset: const Offset(0, 4),
              )
            ],
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.show_chart, color: Colors.greenAccent, size: 28),
              ),
              const SizedBox(width: 16),
              const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text("Mutual Funds", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
                  Text("Track your portfolio", style: TextStyle(color: Colors.white70, fontSize: 12)),
                ],
              ),
              const Spacer(),
              const Icon(Icons.arrow_forward_ios, color: Colors.white54, size: 16),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBudgetSection(BuildContext context, BudgetSummary budget, Function(double) format) {
    final theme = Theme.of(context);
    final isOver = budget.percentage > 100;
    final color = isOver ? AppTheme.danger : (budget.percentage > 80 ? AppTheme.warning : AppTheme.success);

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: theme.dividerColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Monthly Budget', style: TextStyle(fontWeight: FontWeight.bold)),
              Text(
                '${budget.percentage.toStringAsFixed(1)}%',
                style: TextStyle(color: color, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 16),
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: LinearProgressIndicator(
              value: (budget.percentage / 100).clamp(0, 1),
              backgroundColor: theme.dividerColor,
              color: color,
              minHeight: 10,
            ),
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Spent: ${format(budget.spent)}', style: TextStyle(color: theme.colorScheme.onSurfaceVariant, fontSize: 12)),
              Text('Limit: ${format(budget.limit)}', style: TextStyle(color: theme.colorScheme.onSurfaceVariant, fontSize: 12)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildTopCategoriesSection(BuildContext context, DashboardData data, Function(double) format) {
    if (data.categoryDistribution.isEmpty && data.spendingTrend.isEmpty) return const SizedBox.shrink();
    
    final theme = Theme.of(context);
    return Column(
      children: [
         Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('Analysis', style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
              ],
            ),
         ),
         Container(
           height: 350,
           margin: const EdgeInsets.symmetric(horizontal: 20),
           decoration: BoxDecoration(
             color: theme.colorScheme.surface,
             borderRadius: BorderRadius.circular(20),
             border: Border.all(color: theme.dividerColor),
           ),
           child: _buildAnalysisTabs(context, data, format),
         ),
      ],
    );
  }

    Widget _buildTransactionItem(BuildContext context, RecentTransaction txn, Function(double) format) {
    final theme = Theme.of(context);
    final isNegative = txn.amount < 0; // Assuming amount is signed
    
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 6),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: theme.dividerColor),
      ),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        onTap: null, // Navigation removed per user request
        leading: Consumer<CategoriesService>(
          builder: (context, catService, _) {
            // Find category case-insensitive or exact
            final matched = catService.categories
                .cast<TransactionCategory?>()
                .firstWhere(
                  (c) => c?.name.toLowerCase() == txn.category.toLowerCase(),
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
              child: Text(
                (txn.accountOwnerName != null && txn.accountOwnerName!.isNotEmpty) 
                    ? txn.accountOwnerName![0].toUpperCase()
                    : (txn.category.isNotEmpty ? txn.category[0].toUpperCase() : '?'),
                style: TextStyle(color: theme.primaryColor, fontWeight: FontWeight.bold),
              ),
            );
          },
        ),
        title: Text(
          txn.description,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontWeight: FontWeight.w500),
        ),
        subtitle: Row(
          children: [
            Expanded(
              child: Text(
                '${txn.category} • ${txn.accountName ?? 'Account'} • ${txn.formattedDate}',
                style: TextStyle(fontSize: 10, color: theme.colorScheme.onSurfaceVariant),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        trailing: Text(
          format(txn.amount),
          style: TextStyle(
            color: isNegative ? AppTheme.danger : AppTheme.success,
            fontWeight: FontWeight.bold,
            fontSize: 15,
          ),
        ),
      ),
    );
  }

  void _showMonthPicker(BuildContext context) {
      showModalBottomSheet(
        context: context,
        builder: (BuildContext context) {
          return SizedBox(
            height: 300,
            child: Column(
              children: [
                const Padding(
                  padding: EdgeInsets.all(16.0),
                  child: Text("Select Month", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                ),
                Expanded(
                  child: ListView.builder(
                    itemCount: 12,
                    itemBuilder: (context, index) {
                       final date = DateTime(DateTime.now().year, index + 1, 1);
                       final label = DateFormat('MMMM yyyy').format(date);
                       return ListTile(
                         title: Text(label, textAlign: TextAlign.center),
                         onTap: () {
                           context.read<DashboardService>().setMonth(index + 1, DateTime.now().year);
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

  void _showSettingsDialog(BuildContext context) {
    final dashboard = context.read<DashboardService>();
    final controller = TextEditingController(text: dashboard.maskingFactor.toString());
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Settings'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
             const Text('Masking Factor (Privacy)'),
             const SizedBox(height: 8),
             TextField(
               controller: controller,
               keyboardType: const TextInputType.numberWithOptions(decimal: true),
               decoration: const InputDecoration(
                 border: OutlineInputBorder(),
                 hintText: 'Enter factor (e.g. 1.0 for none)',
                 labelText: 'Divider',
               ),
             ),
             const Padding(
               padding: EdgeInsets.only(top: 8),
               child: Text('Divide all amounts by this value to hide actual wealth.', style: TextStyle(fontSize: 12, color: Colors.grey)),
             ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          TextButton(
            onPressed: () {
               final val = double.tryParse(controller.text) ?? 1.0;
               dashboard.setMaskingFactor(val);
               Navigator.pop(context);
            }, 
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  Widget _buildTriageBanner(BuildContext context, int count) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      child: InkWell(
        onTap: () {
          Navigator.push(context, MaterialPageRoute(builder: (_) => const TriageScreen()));
        },
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppTheme.warning.withOpacity(0.1),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppTheme.warning.withOpacity(0.5)),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppTheme.warning.withOpacity(0.2),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.info_outline, color: AppTheme.warning, size: 20),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '$count Transactions to Review',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                    ),
                    Text(
                      'Tap to triage unverified items',
                      style: TextStyle(color: theme.colorScheme.onSurfaceVariant, fontSize: 12),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.arrow_forward_ios, size: 14, color: AppTheme.warning),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSyncHealthCard(BuildContext context) {
    final sms = context.watch<SmsService>();
    final theme = Theme.of(context);
    final lastSyncStr = sms.lastSyncTime != null 
        ? DateFormat('HH:mm').format(sms.lastSyncTime!) 
        : 'Never';

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: theme.dividerColor),
        boxShadow: [
          BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 10, offset: const Offset(0, 4))
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.health_and_safety_outlined, size: 16, color: theme.primaryColor),
              const SizedBox(width: 8),
              const Text('Sync Health', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
              const Spacer(),
              Text(sms.lastSyncStatus ?? 'Standby', 
                style: TextStyle(
                  color: sms.lastSyncStatus == 'Success' ? AppTheme.success : theme.colorScheme.onSurfaceVariant,
                  fontSize: 12, fontWeight: FontWeight.bold
                )
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildHealthStat(context, 'Last Sync', lastSyncStr),
              _buildHealthStat(context, 'Today', sms.messagesSyncedToday.toString()),
              _buildHealthStat(context, 'Queue', sms.queueCount.toString(), isWarning: sms.queueCount > 0),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildHealthStat(BuildContext context, String label, String value, {bool isWarning = false}) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: TextStyle(color: theme.colorScheme.onSurfaceVariant, fontSize: 11)),
        Text(value, style: TextStyle(
          fontWeight: FontWeight.bold, 
          fontSize: 16,
          color: isWarning ? AppTheme.warning : theme.colorScheme.onSurface
        )),
      ],
    );
  }

}
