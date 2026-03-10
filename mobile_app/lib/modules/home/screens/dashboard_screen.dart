import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/modules/ingestion/services/sms_service.dart';
import 'package:intl/intl.dart';
import 'package:mobile_app/core/theme/app_theme.dart';
import 'package:mobile_app/modules/home/services/dashboard_service.dart';
import 'package:mobile_app/modules/auth/services/auth_service.dart';
import 'package:mobile_app/modules/home/models/dashboard_data.dart';
import 'package:mobile_app/modules/home/screens/analytics_screen.dart';
import 'package:mobile_app/modules/home/screens/mutual_funds_screen.dart';
import 'package:mobile_app/modules/ingestion/screens/triage_screen.dart';
import 'package:mobile_app/modules/home/services/categories_service.dart';
import 'package:mobile_app/modules/home/models/transaction_category.dart';
import 'package:mobile_app/core/services/socket_service.dart';
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
       // Single call to load family overview data for current month
       context.read<DashboardService>().refresh();
       context.read<CategoriesService>().fetchCategories();
    });
  }

  @override
  Widget build(BuildContext context) {
    final dashboard = context.watch<DashboardService>();
    final theme = Theme.of(context);
    final currencyFormat = NumberFormat.currency(symbol: dashboard.currencySymbol, decimalDigits: 0);

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
                          'Family Overview',
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
                        preferredSize: const Size.fromHeight(180),
                        child: _buildSummarySection(context, dashboard.data!.summary, formatAmount),
                      )
                    : null,
                  actions: [
                    Consumer<SocketService>(
                      builder: (context, socket, _) => Tooltip(
                        message: socket.isConnected ? 'Real-time Connected' : 'Real-time Disconnected',
                        child: Padding(
                          padding: const EdgeInsets.only(right: 16),
                          child: Icon(
                            socket.isConnected ? Icons.bolt : Icons.bolt_outlined,
                            color: socket.isConnected ? AppTheme.success : AppTheme.danger,
                            size: 20,
                          ),
                        ),
                      ),
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
                  SliverToBoxAdapter(child: _buildInvestmentsEntry(context, dashboard.data!.investmentSummary, formatAmount)),
                  if (dashboard.data!.pendingTriageCount > 0)
                    SliverToBoxAdapter(
                      child: _buildTriageBanner(context, dashboard.data!.pendingTriageCount),
                    ),
                  SliverToBoxAdapter(child: _buildBudgetSection(context, dashboard.data!.budget, formatAmount)),
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(20, 24, 20, 12),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text('Recent Transactions', style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                          TextButton(
                            onPressed: () {
                               Navigator.push(context, MaterialPageRoute(builder: (_) => const AnalyticsScreen()));
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
    );
  }

  Widget _buildSummarySection(BuildContext context, DashboardSummary summary, Function(double) format) {
    // Trend for Today vs Yesterday
    final todayDiff = summary.todayTotal - summary.yesterdayTotal;
    final todayTrendIcon = todayDiff < 0 ? Icons.arrow_downward : (todayDiff > 0 ? Icons.arrow_upward : null);
    final todayTrendColor = todayDiff < 0 ? Colors.greenAccent : (todayDiff > 0 ? Colors.orangeAccent : Colors.white70);
    final todayTrendText = todayDiff != 0 ? '${todayDiff > 0 ? "+" : ""}${format(todayDiff.abs())}' : 'Same as yesterday';

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
              onTap: () {
                Navigator.push(context, MaterialPageRoute(builder: (_) => const AnalyticsScreen()));
              },
              trend: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 6),
                  Container(
                    height: 4,
                    width: 60,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(2),
                    ),
                    child: FractionallySizedBox(
                      alignment: Alignment.centerLeft,
                      widthFactor: (summary.proratedBudget > 0 ? (summary.monthlyTotal / (summary.proratedBudget * 1.5)) : 0.0).clamp(0.0, 1.0).toDouble(),
                      child: Container(
                        decoration: BoxDecoration(
                          color: summary.monthlyTotal > summary.proratedBudget ? Colors.orangeAccent : Colors.greenAccent,
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Prorated Budget',
                    style: TextStyle(color: Colors.white.withOpacity(0.6), fontSize: 8),
                  ),
                ],
              ),
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
              onTap: () {
                Navigator.push(context, MaterialPageRoute(builder: (_) => const AnalyticsScreen(showTodayOnly: true)));
              },
              trend: Row(
                children: [
                  if (todayTrendIcon != null) Icon(todayTrendIcon, size: 10, color: todayTrendColor),
                  const SizedBox(width: 2),
                  Text(
                    todayTrendText,
                    style: TextStyle(color: todayTrendColor, fontSize: 10, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryCard(BuildContext context, String title, String amount, List<Color> colors, IconData icon, {VoidCallback? onTap, Widget? trend}) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 140, // Fixed height for consistency with trend
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
              right: -5,
              bottom: -5,
              child: Icon(icon, color: Colors.white.withOpacity(0.1), size: 60),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(icon, color: Colors.white.withOpacity(0.8), size: 16),
                const SizedBox(height: 12),
                Text(title, style: TextStyle(color: Colors.white.withOpacity(0.8), fontSize: 12)),
                const SizedBox(height: 4),
                FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Text(
                    amount,
                    style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900, letterSpacing: -0.5),
                  ),
                ),
                if (trend != null) trend,
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInvestmentsEntry(BuildContext context, InvestmentSummary? summary, Function(double) format) {
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
                blurRadius: 10, offset: const Offset(0, 4),
              )
            ],
          ),
          child: Row(
            children: [
              // Sparkline on the left
              if (summary != null && summary.sparkline.isNotEmpty)
                Container(
                  width: 60,
                  height: 40,
                  margin: const EdgeInsets.only(right: 16),
                  child: LineChart(
                    LineChartData(
                      gridData: const FlGridData(show: false),
                      titlesData: const FlTitlesData(show: false),
                      borderData: FlBorderData(show: false),
                      lineBarsData: [
                        LineChartBarData(
                          spots: summary.sparkline.asMap().entries.map((e) => FlSpot(e.key.toDouble(), e.value)).toList(),
                          isCurved: true,
                          color: summary.profitLoss >= 0 ? Colors.greenAccent : Colors.redAccent,
                          barWidth: 2,
                          dotData: const FlDotData(show: false),
                          belowBarData: BarAreaData(show: false),
                        ),
                      ],
                    ),
                  ),
                )
              else
                Container(
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(right: 16),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.show_chart, color: Colors.greenAccent, size: 28),
                ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "Mutual Funds Overview",
                      style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                    ),
                    if (summary != null && summary.currentValue > 0) ...[
                      const SizedBox(height: 4),
                      // Current value + overall P&L
                      Row(
                        children: [
                          Text(
                            format(summary.currentValue),
                            style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w500),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            "${summary.profitLoss >= 0 ? '+' : ''}${format(summary.profitLoss)}",
                            style: TextStyle(
                              color: summary.profitLoss >= 0 ? Colors.greenAccent : Colors.redAccent,
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          if (summary.totalInvested > 0) ...[
                            const SizedBox(width: 4),
                            Text(
                              "(${((summary.profitLoss / summary.totalInvested) * 100).toStringAsFixed(1)}%)",
                              style: TextStyle(
                                color: summary.profitLoss >= 0 ? Colors.greenAccent.withOpacity(0.8) : Colors.redAccent.withOpacity(0.8),
                                fontSize: 10,
                              ),
                            ),
                          ],
                        ],
                      ),
                      const SizedBox(height: 2),
                      // Day change row
                      Row(
                        children: [
                          Icon(
                            summary.dayChange >= 0 ? Icons.arrow_drop_up : Icons.arrow_drop_down,
                            color: summary.dayChange >= 0 ? Colors.greenAccent : Colors.redAccent,
                            size: 14,
                          ),
                          Text(
                            "Today: ${summary.dayChange >= 0 ? '+' : ''}${format(summary.dayChange)} (${summary.dayChangePercent.toStringAsFixed(2)}%)",
                            style: TextStyle(
                              color: summary.dayChange >= 0 ? Colors.greenAccent : Colors.redAccent,
                              fontSize: 10,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          if (summary.xirr != null && summary.xirr! > 0) ...[
                            const SizedBox(width: 8),
                            Text(
                              "XIRR: ${summary.xirr!.toStringAsFixed(1)}%",
                              style: const TextStyle(color: Colors.white54, fontSize: 10),
                            ),
                          ],
                        ],
                      ),
                    ] else
                      const Text("Track your portfolio performance", style: TextStyle(color: Colors.white70, fontSize: 12)),
                  ],
                ),
              ),
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
    final summary = DashboardService.of(context).data?.summary;
    final prorated = summary?.proratedBudget ?? 0.0;
    final isOverProrated = budget.spent > prorated && prorated > 0;
    final healthLabel = isOverProrated ? 'Over Pace' : 'On Track';
    final healthColor = isOverProrated ? AppTheme.danger : AppTheme.success;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(30),
        border: Border.all(color: theme.dividerColor.withOpacity(0.5)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.03),
            blurRadius: 20,
            offset: const Offset(0, 10),
          )
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Family Budget', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
                  const SizedBox(height: 2),
                  Text(
                    'Monthly Limit: ${format(budget.limit)}',
                    style: TextStyle(color: theme.colorScheme.onSurfaceVariant, fontSize: 11),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: healthColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  healthLabel,
                  style: TextStyle(color: healthColor, fontWeight: FontWeight.bold, fontSize: 11),
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          Stack(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: LinearProgressIndicator(
                  value: (budget.percentage / 100).clamp(0, 1),
                  backgroundColor: theme.dividerColor.withOpacity(0.1),
                  color: color.withOpacity(0.3),
                  minHeight: 12,
                ),
              ),
              if (prorated > 0 && budget.limit > 0)
                Positioned(
                  left: (MediaQuery.of(context).size.width - 88) * (prorated / budget.limit),
                  child: Container(
                    width: 2,
                    height: 12,
                    color: theme.colorScheme.onSurface.withOpacity(0.5),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(width: 8, height: 8, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
                  const SizedBox(width: 6),
                  Text('Spent: ${format(budget.spent)}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                ],
              ),
              Text(
                'Pace: ${format(prorated)}',
                style: TextStyle(color: theme.colorScheme.onSurfaceVariant, fontSize: 11, fontStyle: FontStyle.italic),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // _buildTopCategoriesSection and _buildAnalysisTabs removed as they have been moved to AnalyticsScreen

  Widget _buildTransactionItem(BuildContext context, RecentTransaction txn, Function(double) format) {
    final theme = Theme.of(context);
    final isNegative = txn.amount < 0;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 6),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: theme.dividerColor),
      ),
      child: ListTile(
        onTap: () {
          Navigator.push(context, MaterialPageRoute(builder: (_) => const AnalyticsScreen()));
        },
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        leading: Consumer<CategoriesService>(
          builder: (context, catService, _) {
            final localTheme = Theme.of(context);
            // Find category case-insensitive or exact
            final matched = catService.categories
                .cast<TransactionCategory?>()
                .firstWhere(
                  (c) => c?.name.toLowerCase() == txn.category.toLowerCase(),
                  orElse: () => null,
                );
            
            if (matched?.icon != null) {
              return CircleAvatar(
                backgroundColor: localTheme.primaryColor.withOpacity(0.1),
                child: Text(matched!.icon!, style: const TextStyle(fontSize: 20)),
              );
            }
            
            return CircleAvatar(
              backgroundColor: localTheme.primaryColor.withOpacity(0.1),
              child: Text(
                (txn.accountOwnerName != null && txn.accountOwnerName!.isNotEmpty) 
                    ? txn.accountOwnerName![0].toUpperCase()
                    : (txn.category.isNotEmpty ? txn.category[0].toUpperCase() : '?'),
                style: TextStyle(color: localTheme.primaryColor, fontWeight: FontWeight.bold),
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
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${txn.category} • ${txn.accountName ?? 'Account'} • ${txn.formattedDate}',
              style: TextStyle(fontSize: 10, color: theme.colorScheme.onSurfaceVariant),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            if (txn.expenseGroupName != null) ...[
              const SizedBox(height: 4),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: AppTheme.primary.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.folder_shared_outlined, size: 8, color: AppTheme.primary),
                    const SizedBox(width: 4),
                    Text(
                      txn.expenseGroupName!,
                      style: const TextStyle(fontSize: 8, fontWeight: FontWeight.bold, color: AppTheme.primary),
                    ),
                  ],
                ),
              ),
            ],
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
        borderRadius: BorderRadius.circular(20),
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
              Icon(Icons.sync_problem_outlined, size: 18, color: sms.queueCount > 0 ? AppTheme.warning : theme.primaryColor),
              const SizedBox(width: 8),
              Text(
                sms.queueCount > 0 ? 'Action Required' : 'Sync Health', 
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)
              ),
              const Spacer(),
              if (sms.isSyncing)
                const SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.primary),
                )
              else
                Text(sms.lastSyncStatus ?? 'Healthy', 
                  style: TextStyle(
                    color: (sms.lastSyncStatus == 'Success' || sms.lastSyncStatus == null) 
                        ? AppTheme.success 
                        : (sms.lastSyncStatus == 'Failed' ? AppTheme.danger : AppTheme.warning),
                    fontSize: 12, fontWeight: FontWeight.bold
                  )
                ),
            ],
          ),
          const SizedBox(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildHealthStat(context, 'Last Sync', lastSyncStr),
              _buildHealthStat(context, 'Today', sms.messagesSyncedToday.toString()),
              _buildHealthStat(context, 'Unsynced', sms.queueCount.toString(), isWarning: sms.queueCount > 0),
            ],
          ),
          const Divider(height: 32),
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      sms.queueCount > 0 ? 'Messages pending sync' : 'All messages are up to date',
                      style: TextStyle(fontSize: 12, color: theme.colorScheme.onSurfaceVariant),
                    ),
                    if (sms.queueCount > 0)
                      const Text(
                        'Tap Sync Now to push items manually',
                        style: TextStyle(fontSize: 10, color: AppTheme.warning, fontWeight: FontWeight.bold),
                      ),
                  ],
                ),
              ),
              TextButton.icon(
                onPressed: sms.isSyncing ? null : () => sms.syncNow(),
                style: TextButton.styleFrom(
                  backgroundColor: theme.primaryColor.withOpacity(0.1),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                ),
                icon: sms.isSyncing 
                  ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.sync, size: 16),
                label: Text(sms.isSyncing ? 'Syncing...' : 'Sync Now', style: const TextStyle(fontWeight: FontWeight.bold)),
              ),
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
