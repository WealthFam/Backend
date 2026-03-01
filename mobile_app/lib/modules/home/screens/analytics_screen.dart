import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:http/http.dart' as http;
import 'package:mobile_app/core/config/app_config.dart';
import 'package:mobile_app/core/theme/app_theme.dart';
import 'package:mobile_app/modules/auth/services/auth_service.dart';
import 'package:mobile_app/modules/home/models/dashboard_data.dart';
import 'package:mobile_app/modules/home/models/transaction_category.dart';
import 'package:mobile_app/modules/home/services/dashboard_service.dart';
import 'package:mobile_app/modules/home/services/categories_service.dart';
import 'package:mobile_app/core/widgets/app_shell.dart';

class AnalyticsScreen extends StatefulWidget {
  final bool showTodayOnly;
  const AnalyticsScreen({super.key, this.showTodayOnly = false});

  @override
  State<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends State<AnalyticsScreen> {
  final List<dynamic> _transactions = [];
  bool _isTxnLoading = false;
  bool _hasMore = true;
  int _page = 1;
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final dashboard = context.read<DashboardService>();
      dashboard.refresh();
      _fetchTransactions(reset: true);
      context.read<CategoriesService>().fetchCategories();
    });

    _scrollController.addListener(() {
      if (_scrollController.position.pixels >= _scrollController.position.maxScrollExtent - 200) {
        _fetchTransactions();
      }
    });
  }

  Future<void> _fetchTransactions({bool reset = false}) async {
    if (_isTxnLoading || (!reset && !_hasMore)) return;

    setState(() {
      if (reset) {
        _page = 1;
        _transactions.clear();
        _hasMore = true;
      }
      _isTxnLoading = true;
    });

    final config = context.read<AppConfig>();
    final auth = context.read<AuthService>();
    final dashboard = context.read<DashboardService>();

    final url = Uri.parse('${config.backendUrl}/api/v1/mobile/transactions').replace(queryParameters: {
      'page': _page.toString(),
      'page_size': '20',
      if (dashboard.selectedMonth != null) 'month': (widget.showTodayOnly ? DateTime.now().month : dashboard.selectedMonth).toString(),
      if (dashboard.selectedYear != null) 'year': (widget.showTodayOnly ? DateTime.now().year : dashboard.selectedYear).toString(),
      if (widget.showTodayOnly) 'day': DateTime.now().day.toString(),
      if (dashboard.selectedMemberId != null) 'member_id': dashboard.selectedMemberId,
    });

    try {
      final response = await http.get(
        url,
        headers: {'Authorization': 'Bearer ${auth.accessToken}'},
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final List items = data['items'];
        final nextPage = data['next_page'];

        if (mounted) {
          setState(() {
            _transactions.addAll(items.where((i) => i['is_hidden'] != true));
            _hasMore = nextPage != null;
            _page++;
          });
        }
      }
    } catch (e) {
      debugPrint("Error fetching analytics transactions: $e");
    } finally {
      if (mounted) {
        setState(() => _isTxnLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final dashboard = context.watch<DashboardService>();
    final theme = Theme.of(context);
    final currencyFormat = NumberFormat.simpleCurrency(name: dashboard.data?.summary.currency ?? 'INR');

    String formatAmount(double amount) {
      return currencyFormat.format(amount / dashboard.maskingFactor);
    }

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      drawer: const AppDrawer(),
      appBar: AppBar(
        leading: const DrawerMenuButton(),
        title: const Text('Insights', style: TextStyle(fontWeight: FontWeight.bold)),
        actions: [
          if (dashboard.members.isNotEmpty)
            PopupMenuButton<String>(
              icon: const Icon(Icons.people_outline),
              initialValue: dashboard.selectedMemberId,
              onSelected: (val) => dashboard.setMember(val == 'all' ? null : val),
              itemBuilder: (context) => <PopupMenuEntry<String>>[
                const PopupMenuItem(value: 'all', child: Text('Full Family')),
                ...dashboard.members.map((m) => PopupMenuItem(
                      value: m['id'].toString(),
                      child: Text(m['name']),
                    ))
              ],
            ),
          IconButton(
            icon: const Icon(Icons.calendar_month_outlined),
            onPressed: () => _showMonthPicker(context),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
           await dashboard.refresh();
           await _fetchTransactions(reset: true);
        },
        child: SingleChildScrollView(
                controller: _scrollController,
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (dashboard.data != null) ...[
                      _buildHeaderSummary(context, dashboard.data!, formatAmount),
                      const SizedBox(height: 24),
                      _buildSectionTitle(context, 'Monthly Trend (6m)'),
                      const SizedBox(height: 12),
                      _buildMonthTrendChart(context, dashboard.data!.monthWiseTrend, dashboard.maskingFactor),
                      const SizedBox(height: 32),
                      _buildSectionTitle(context, 'Daily Spending (${DateFormat('MMMM').format(DateTime(dashboard.selectedYear ?? 2024, dashboard.selectedMonth ?? 1))})'),
                      const SizedBox(height: 12),
                      _buildDailyTrendChart(context, dashboard.data!.spendingTrend, dashboard.maskingFactor),
                      const SizedBox(height: 32),
                      _buildCategoryPieChart(context, dashboard.data!.categoryDistribution, formatAmount),
                      const SizedBox(height: 32),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          _buildSectionTitle(context, 'Transactions'),
                          Text(
                            'Month Total: ${formatAmount(dashboard.data!.summary.monthlyTotal)}',
                            style: TextStyle(fontSize: 12, color: theme.colorScheme.onSurfaceVariant),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      _buildTransactionList(context),
                      const SizedBox(height: 48),
                    ] else if (dashboard.error != null) ...[
                      Center(child: Text(dashboard.error!, style: const TextStyle(color: AppTheme.danger))),
                    ] else ...[
                      const Center(child: Text('No data for selected filters')),
                    ],
                  ],
                ),
              ),
      ),
    );
  }

  Widget _buildSectionTitle(BuildContext context, String title) {
    return Text(
      title,
      style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
    );
  }

  Widget _buildHeaderSummary(BuildContext context, DashboardData data, Function(double) format) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.primaryContainer.withOpacity(0.3),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Theme.of(context).colorScheme.primary.withOpacity(0.1)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Total Spent', style: TextStyle(fontSize: 12, color: Colors.grey)),
              const SizedBox(height: 4),
              Text(format(data.summary.monthlyTotal), style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
            ],
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              const Text('Budget Utilization', style: TextStyle(fontSize: 12, color: Colors.grey)),
              const SizedBox(height: 4),
              Text('${data.budget.percentage.toStringAsFixed(1)}%', 
                style: TextStyle(
                  fontSize: 20, 
                  fontWeight: FontWeight.bold,
                  color: data.budget.percentage > 100 ? AppTheme.danger : AppTheme.success,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMonthTrendChart(BuildContext context, List<MonthTrendItem> trend, double maskingFactor) {
    if (trend.isEmpty) {
      return const SizedBox(height: 150, child: Center(child: Text("No Trend Data")));
    }

    double maxY = 0;
    for (var m in trend) {
      if (m.spent > maxY) maxY = m.spent;
      if (m.budget > maxY) maxY = m.budget;
    }
    maxY = maxY * 1.2;

    return Container(
      height: 200,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Theme.of(context).dividerColor),
      ),
      child: BarChart(
        BarChartData(
          maxY: maxY,
          barGroups: trend.asMap().entries.map((e) {
            return BarChartGroupData(
              x: e.key,
              barRods: [
                BarChartRodData(
                  toY: e.value.spent,
                  color: e.value.spent > e.value.budget && e.value.budget > 0 ? AppTheme.danger : AppTheme.primary,
                  width: 12,
                  borderRadius: BorderRadius.circular(4),
                ),
              ],
            );
          }).toList(),
          titlesData: FlTitlesData(
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 40,
                getTitlesWidget: (val, meta) => Text(
                  NumberFormat.compact().format(val / maskingFactor),
                  style: const TextStyle(fontSize: 8, color: Colors.grey),
                ),
              ),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (val, meta) {
                  int idx = val.toInt();
                  if (idx >= 0 && idx < trend.length) {
                    return Padding(
                      padding: const EdgeInsets.only(top: 8.0),
                      child: Text(trend[idx].month.split(' ')[0], style: const TextStyle(fontSize: 8, color: Colors.grey)),
                    );
                  }
                  return const SizedBox.shrink();
                },
              ),
            ),
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          ),
          gridData: const FlGridData(show: false),
          borderData: FlBorderData(show: false),
        ),
      ),
    );
  }

  Widget _buildDailyTrendChart(BuildContext context, List<SpendingTrendItem> trend, double maskingFactor) {
    if (trend.isEmpty) {
      return const SizedBox(height: 150, child: Center(child: Text("No Data")));
    }

    double maxY = 0;
    for (var item in trend) {
      if (item.amount > maxY) maxY = item.amount;
      if (item.dailyLimit > maxY) maxY = item.dailyLimit;
    }
    maxY = maxY * 1.2;

    return Container(
      height: 200,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Theme.of(context).dividerColor),
      ),
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
                  return Text(
                    NumberFormat.compact().format(value / maskingFactor),
                    style: const TextStyle(fontSize: 8, color: Colors.grey),
                  );
                },
              ),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (value, meta) {
                  int idx = value.toInt();
                  if (idx >= 0 && idx < trend.length) {
                    if (idx % 5 != 0) return const SizedBox.shrink();
                    DateTime date = DateTime.parse(trend[idx].date);
                    return Padding(
                      padding: const EdgeInsets.only(top: 8.0),
                      child: Text(DateFormat('d').format(date), style: const TextStyle(fontSize: 8, color: Colors.grey)),
                    );
                  }
                  return const SizedBox.shrink();
                },
              ),
            ),
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          ),
          gridData: const FlGridData(show: true, drawVerticalLine: false),
          borderData: FlBorderData(show: false),
          lineBarsData: [
            LineChartBarData(
              spots: trend.asMap().entries.map((e) => FlSpot(e.key.toDouble(), e.value.amount)).toList(),
              isCurved: true,
              color: AppTheme.primary,
              barWidth: 3,
              dotData: const FlDotData(show: false),
              belowBarData: BarAreaData(
                show: true,
                gradient: LinearGradient(
                  colors: [AppTheme.primary.withOpacity(0.2), AppTheme.primary.withOpacity(0.0)],
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCategoryPieChart(BuildContext context, List<CategoryPieItem> distribution, Function(double) format) {
    if (distribution.isEmpty) return const SizedBox(height: 150, child: Center(child: Text("No Data")));

    final List<Color> colors = [
      const Color(0xFF4F46E5), const Color(0xFF10B981), const Color(0xFFF59E0B),
      const Color(0xFFEF4444), const Color(0xFF8B5CF6), const Color(0xFFEC4899),
    ];

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Theme.of(context).dividerColor),
      ),
      child: Row(
        children: [
          Expanded(
            flex: 1,
            child: SizedBox(
              height: 150,
              child: PieChart(
                PieChartData(
                  sectionsSpace: 2,
                  centerSpaceRadius: 30,
                  sections: distribution.asMap().entries.map((entry) {
                    final index = entry.key;
                    final item = entry.value;
                    return PieChartSectionData(
                      color: colors[index % colors.length],
                      value: item.value,
                      title: '',
                      radius: 40,
                    );
                  }).toList(),
                ),
              ),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            flex: 1,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: distribution.take(5).toList().asMap().entries.map((e) {
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Row(
                    children: [
                      Container(width: 8, height: 8, color: colors[e.key % colors.length]),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          e.value.name,
                          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w500),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      Text(format(e.value.value), style: const TextStyle(fontSize: 10, color: Colors.grey)),
                    ],
                  ),
                );
              }).toList(),
            ),
          ),
        ],
      ),
    );
  }

  void _showMonthPicker(BuildContext context) {
    showModalBottomSheet(
      context: context,
      builder: (context) {
        return SizedBox(
          height: 350,
          child: Column(
            children: [
              const Padding(
                padding: EdgeInsets.all(16.0),
                child: Text('Select Month', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
              ),
              Expanded(
                child: ListView.builder(
                  itemCount: 12,
                  itemBuilder: (context, index) {
                    final monthDate = DateTime(DateTime.now().year, DateTime.now().month - index, 1);
                    return ListTile(
                      title: Text(DateFormat('MMMM yyyy').format(monthDate), textAlign: TextAlign.center),
                      onTap: () {
                      context.read<DashboardService>().setMonth(monthDate.month, monthDate.year);
                        _fetchTransactions(reset: true);
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

  Widget _buildTransactionList(BuildContext context) {
    if (_transactions.isEmpty && _isTxnLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    
    if (_transactions.isEmpty) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(32),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(20),
        ),
        child: const Column(
          children: [
            Icon(Icons.receipt_long_outlined, size: 48, color: Colors.grey),
            SizedBox(height: 16),
            Text('No transactions found for this period', style: TextStyle(color: Colors.grey)),
          ],
        ),
      );
    }

    return Column(
      children: [
        ListView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: _transactions.length,
          itemBuilder: (context, index) {
            final txn = _transactions[index];
            return _buildTransactionItem(context, txn);
          },
        ),
        if (_hasMore)
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: _isTxnLoading 
              ? const CircularProgressIndicator()
              : TextButton(
                  onPressed: () => _fetchTransactions(),
                  child: const Text('Load More'),
                ),
          ),
      ],
    );
  }

  Widget _buildTransactionItem(BuildContext context, dynamic txn) {
    final theme = Theme.of(context);
    final dashboard = context.read<DashboardService>();
    final amount = (txn['amount'] as num).toDouble();
    final date = DateTime.parse(txn['date']);
    
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 6),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: theme.dividerColor),
      ),
      child: ListTile(
        onTap: () => _showEditCategoryDialog(context, txn),
        leading: Consumer<CategoriesService>(
          builder: (context, catService, _) {
            final catName = txn['category'] as String;
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
              child: Text(
                catName.isNotEmpty ? catName[0].toUpperCase() : '?',
                style: TextStyle(color: theme.primaryColor, fontWeight: FontWeight.bold),
              ),
            );
          },
        ),
        title: Text(
          txn['description'],
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 13),
        ),
        subtitle: Text(
          '${DateFormat('MMM d, h:mm a').format(date)} • ${txn['account_name'] ?? 'Account'}',
          style: TextStyle(fontSize: 10, color: theme.colorScheme.onSurfaceVariant),
        ),
        trailing: Text(
          NumberFormat.simpleCurrency(name: 'INR').format(amount / dashboard.maskingFactor),
          style: TextStyle(
            color: amount < 0 ? AppTheme.danger : AppTheme.success,
            fontWeight: FontWeight.bold,
            fontSize: 14,
          ),
        ),
      ),
    );
  }

  void _showEditCategoryDialog(BuildContext context, dynamic txn) {
    // Re-use logic or just keep it Simple for now
    // Actually we should probably have this shared, but for now I'll just skip detailed edit
    // to focus on the main UI restructuring.
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Transaction details coming soon'), behavior: SnackBarBehavior.floating),
    );
  }
}
