import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:mobile_app/core/theme/app_theme.dart';
import 'package:mobile_app/modules/home/services/funds_service.dart';
import 'package:mobile_app/modules/home/services/dashboard_service.dart';
import 'package:mobile_app/modules/home/models/fund_models.dart';
import 'package:fl_chart/fl_chart.dart';
import 'dart:math' as math;

class MutualFundsScreen extends StatefulWidget {
  const MutualFundsScreen({super.key});

  @override
  State<MutualFundsScreen> createState() => _MutualFundsScreenState();
}

class _MutualFundsScreenState extends State<MutualFundsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      // Sync member selection from dashboard if needed, or just default to null (All)
      // For now, start fresh or use local state.
      // Let's assume independent filter for this screen.
      context.read<FundsService>().fetchFunds();
    });
  }

  @override
  Widget build(BuildContext context) {
    final fundsService = context.watch<FundsService>();
    final dashboardService = context.watch<DashboardService>(); // reusing members list & masking
    final theme = Theme.of(context);
    
    // Masking Helper
    final currencyFormat = NumberFormat.currency(symbol: '₹', decimalDigits: 0);
    String formatAmount(double amount) {
       return currencyFormat.format(amount / dashboardService.maskingFactor);
    }
 
    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Investments'),
            if (dashboardService.maskingFactor > 1.0) ...[
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
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ],
        ),
        actions: [
            if (dashboardService.members.isNotEmpty) 
               PopupMenuButton<String>(
                 icon: const Icon(Icons.people),
                 initialValue: fundsService.selectedMemberId,
                 onSelected: (val) => fundsService.setMember(val == 'all' ? null : val),
                 itemBuilder: (context) => <PopupMenuEntry<String>>[
                   const PopupMenuItem(value: 'all', child: Text('All Family')),
                   ...dashboardService.members.map((m) => PopupMenuItem(
                     value: m['id'].toString(), 
                     child: Text(m['name']),
                   ))
                 ],
               ),
            IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: () => fundsService.fetchFunds(),
            ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => fundsService.fetchFunds(),
        child: fundsService.isLoading && fundsService.portfolio == null
            ? const Center(child: CircularProgressIndicator())
            : fundsService.error != null
                ? Center(child: Text(fundsService.error!, style: const TextStyle(color: Colors.red)))
                : _buildContent(context, fundsService.portfolio!, formatAmount),
      ),
    );
  }

  Widget _buildContent(BuildContext context, PortfolioSummary portfolio, Function(double) format) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _buildSummaryCard(context, portfolio, format),
        const SizedBox(height: 24),
        _buildPortfolioCharts(context, portfolio),
        const SizedBox(height: 24),
        const Text(
          "Holdings",
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        ...portfolio.holdings.map((h) => _buildHoldingItem(context, h, format)),
        const SizedBox(height: 32),
      ],
    );
  }

  Widget _buildSummaryCard(BuildContext context, PortfolioSummary p, Function(double) format) {
    final theme = Theme.of(context);
    final isProfit = p.totalPl >= 0;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [Colors.blueGrey.shade900, Colors.blueGrey.shade800],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(color: Colors.black.withOpacity(0.2), blurRadius: 10, offset: const Offset(0, 5)),
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
                  const Text("Current Value", style: TextStyle(color: Colors.white70, fontSize: 13)),
                  const SizedBox(height: 4),
                  Text(
                    format(p.totalCurrent),
                    style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  const Text("Total Returns %", style: TextStyle(color: Colors.white70, fontSize: 13)),
                  const SizedBox(height: 4),
                  Text(
                    "${(p.totalPl / p.totalInvested * 100).toStringAsFixed(2)}%",
                    style: TextStyle(
                      color: isProfit ? Colors.greenAccent : Colors.redAccent,
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("Invested", style: TextStyle(color: Colors.white54, fontSize: 12)),
                  Text(format(p.totalInvested), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  const Text("Total Returns", style: TextStyle(color: Colors.white54, fontSize: 12)),
                  Text(
                    "${isProfit ? '+' : ''}${format(p.totalPl)}",
                    style: TextStyle(
                      color: isProfit ? Colors.greenAccent : Colors.redAccent,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildPortfolioCharts(BuildContext context, PortfolioSummary portfolio) {
    if (portfolio.holdings.isEmpty) return const SizedBox.shrink();

    final theme = Theme.of(context);
    final List<Color> colors = [
      AppTheme.primary,
      AppTheme.success,
      AppTheme.warning,
      AppTheme.danger,
      Colors.purple,
      Colors.orange,
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text("Asset Allocation", style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
        const SizedBox(height: 16),
        Container(
          height: 200,
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: theme.cardColor,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: theme.dividerColor.withOpacity(0.5)),
          ),
          child: Row(
            children: [
              Expanded(
                flex: 1,
                child: PieChart(
                  PieChartData(
                    sectionsSpace: 2,
                    centerSpaceRadius: 30,
                    sections: portfolio.holdings.asMap().entries.map((entry) {
                      final index = entry.key;
                      final h = entry.value;
                      final percentage = (h.currentValue / portfolio.totalCurrent) * 100;
                      return PieChartSectionData(
                        color: colors[index % colors.length],
                        value: h.currentValue,
                        radius: 40,
                        showTitle: percentage > 10,
                        title: '${percentage.toStringAsFixed(0)}%',
                        titleStyle: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.white),
                      );
                    }).toList(),
                  ),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                flex: 1,
                child: ListView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: math.min(portfolio.holdings.length, 5),
                  itemBuilder: (context, index) {
                    final h = portfolio.holdings[index];
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2),
                      child: Row(
                        children: [
                          Container(width: 10, height: 10, color: colors[index % colors.length]),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              h.schemeName,
                              style: const TextStyle(fontSize: 10),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildHoldingItem(BuildContext context, FundHolding h, Function(double) format) {
    final theme = Theme.of(context);
    final isProfit = h.profitLoss >= 0;
    
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.cardColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: theme.dividerColor.withOpacity(0.5)),
        boxShadow: [
           BoxShadow(color: Colors.black.withOpacity(0.02), blurRadius: 4, offset: const Offset(0, 2))
        ]
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            h.schemeName,
            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("Current", style: TextStyle(color: Colors.grey, fontSize: 11)),
                  const SizedBox(height: 2),
                  Text(format(h.currentValue), style: const TextStyle(fontWeight: FontWeight.bold)),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                   const Text("Returns", style: TextStyle(color: Colors.grey, fontSize: 11)),
                   const SizedBox(height: 2),
                   Text(
                     "${isProfit ? '+' : ''}${format(h.profitLoss)}",
                     style: TextStyle(
                       color: isProfit ? AppTheme.success : AppTheme.danger,
                       fontWeight: FontWeight.bold,
                       fontSize: 13,
                     ),
                   )
                ],
              )
            ],
          )
        ],
      ),
    );
  }
}
