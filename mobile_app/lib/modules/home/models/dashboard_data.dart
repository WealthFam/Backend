import 'package:intl/intl.dart';

class DashboardData {
  final DashboardSummary summary;
  final BudgetSummary budget;
  final InvestmentSummary? investmentSummary;
  final List<SpendingTrendItem> spendingTrend;
  final List<CategoryPieItem> categoryDistribution;
  final List<MonthTrendItem> monthWiseTrend;
  final List<RecentTransaction> recentTransactions;
  final int pendingTriageCount;

  DashboardData({
    required this.summary,
    required this.budget,
    this.investmentSummary,
    required this.spendingTrend,
    required this.categoryDistribution,
    required this.monthWiseTrend,
    required this.recentTransactions,
    this.pendingTriageCount = 0,
  });

  factory DashboardData.fromJson(Map<String, dynamic> json) {
    return DashboardData(
      summary: DashboardSummary.fromJson(json['summary']),
      budget: BudgetSummary.fromJson(json['budget']),
      investmentSummary: json['investment_summary'] != null ? InvestmentSummary.fromJson(json['investment_summary']) : null,
      spendingTrend: (json['spending_trend'] as List)
          .map((i) => SpendingTrendItem.fromJson(i))
          .toList(),
      categoryDistribution: (json['category_distribution'] as List)
          .map((i) => CategoryPieItem.fromJson(i))
          .toList(),
      monthWiseTrend: (json['month_wise_trend'] as List? ?? [])
          .map((i) => MonthTrendItem.fromJson(i))
          .toList(),
      recentTransactions: (json['recent_transactions'] as List)
          .map((i) => RecentTransaction.fromJson(i))
          .toList(),
      pendingTriageCount: json['pending_triage_count'] ?? 0,
    );
  }
}

class SpendingTrendItem {
  final String date;
  final double amount;
  final double dailyLimit;

  SpendingTrendItem({required this.date, required this.amount, required this.dailyLimit});

  factory SpendingTrendItem.fromJson(Map<String, dynamic> json) {
    return SpendingTrendItem(
      date: json['date'],
      amount: (json['amount'] as num).toDouble(),
      dailyLimit: (json['daily_limit'] as num).toDouble(),
    );
  }
  
  DateTime get dateTime => DateTime.parse(date);
}

class CategoryPieItem {
  final String name;
  final double value;

  CategoryPieItem({required this.name, required this.value});

  factory CategoryPieItem.fromJson(Map<String, dynamic> json) {
    return CategoryPieItem(
      name: json['name'],
      value: (json['value'] as num).toDouble(),
    );
  }
}

class DashboardSummary {
  final double todayTotal;
  final double monthlyTotal;
  final String currency;

  DashboardSummary({
    required this.todayTotal,
    required this.monthlyTotal,
    required this.currency,
  });

  factory DashboardSummary.fromJson(Map<String, dynamic> json) {
    return DashboardSummary(
      todayTotal: (json['today_total'] as num).toDouble(),
      monthlyTotal: (json['monthly_total'] as num).toDouble(),
      currency: json['currency'] ?? 'INR',
    );
  }
}

class BudgetSummary {
  final double limit;
  final double spent;
  final double percentage;

  BudgetSummary({
    required this.limit,
    required this.spent,
    required this.percentage,
  });

  factory BudgetSummary.fromJson(Map<String, dynamic> json) {
    return BudgetSummary(
      limit: (json['limit'] as num).toDouble(),
      spent: (json['spent'] as num).toDouble(),
      percentage: (json['percentage'] as num).toDouble(),
    );
  }
}

class InvestmentSummary {
  final double totalInvested;
  final double currentValue;
  final double profitLoss;
  final double? xirr;
  final List<double> sparkline;
  final double dayChange;
  final double dayChangePercent;

  InvestmentSummary({
    required this.totalInvested,
    required this.currentValue,
    required this.profitLoss,
    this.xirr,
    this.sparkline = const [],
    this.dayChange = 0.0,
    this.dayChangePercent = 0.0,
  });

  factory InvestmentSummary.fromJson(Map<String, dynamic> json) {
    return InvestmentSummary(
      totalInvested: (json['total_invested'] as num).toDouble(),
      currentValue: (json['current_value'] as num).toDouble(),
      profitLoss: (json['profit_loss'] as num).toDouble(),
      xirr: json['xirr'] != null ? (json['xirr'] as num).toDouble() : null,
      sparkline: (json['sparkline'] as List? ?? []).map((v) => (v as num).toDouble()).toList(),
      dayChange: (json['day_change'] as num? ?? 0).toDouble(),
      dayChangePercent: (json['day_change_percent'] as num? ?? 0).toDouble(),
    );
  }
}

class CategorySpending {
  final String name;
  final double amount;

  CategorySpending({
    required this.name,
    required this.amount,
  });

  factory CategorySpending.fromJson(Map<String, dynamic> json) {
    return CategorySpending(
      name: json['name'],
      amount: (json['amount'] as num).toDouble(),
    );
  }
}

class RecentTransaction {
  final String id;
  final DateTime date;
  final String description;
  final double amount;
  final String category;
  final String? accountName;
  final String? accountOwnerName;
  final bool isHidden;

  RecentTransaction({
    required this.id,
    required this.date,
    required this.description,
    required this.amount,
    required this.category,
    this.accountName,
    this.accountOwnerName,
    this.isHidden = false,
  });

  factory RecentTransaction.fromJson(Map<String, dynamic> json) {
    return RecentTransaction(
      id: json['id'],
      date: DateTime.parse(json['date']),
      description: json['description'],
      amount: (json['amount'] as num).toDouble(),
      category: json['category'],
      accountName: json['account_name'],
      accountOwnerName: json['account_owner_name'],
      isHidden: json['is_hidden'] ?? false,
    );
  }

  String get formattedDate => DateFormat('MMM d, h:mm a').format(date);
}

class MonthTrendItem {
  final String month;
  final double spent;
  final double budget;

  MonthTrendItem({required this.month, required this.spent, required this.budget});

  factory MonthTrendItem.fromJson(Map<String, dynamic> json) {
    return MonthTrendItem(
      month: json['month'],
      spent: (json['spent'] as num).toDouble(),
      budget: (json['budget'] as num).toDouble(),
    );
  }
}
