import 'package:intl/intl.dart';

double _toDouble(dynamic value) {
  if (value == null) return 0.0;
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value) ?? 0.0;
  return 0.0;
}


class DashboardData {
  final DashboardSummary summary;
  final BudgetSummary budget;
  final InvestmentSummary? investmentSummary;
  final List<SpendingTrendItem> spendingTrend;
  final List<CategoryPieItem> categoryDistribution;
  final List<MonthTrendItem> monthWiseTrend;
  final List<RecentTransaction> recentTransactions;
  final int pendingTriageCount;
  final int pendingTrainingCount;
  final int? familyMembersCount;

  DashboardData({
    required this.summary,
    required this.budget,
    this.investmentSummary,
    required this.spendingTrend,
    required this.categoryDistribution,
    required this.monthWiseTrend,
    required this.recentTransactions,
    this.pendingTriageCount = 0,
    this.pendingTrainingCount = 0,
    this.familyMembersCount,
  });

  factory DashboardData.fromJson(Map<String, dynamic> json) {
    return DashboardData(
      summary: DashboardSummary.fromJson(json['summary']),
      budget: BudgetSummary.fromJson(json['budget']),
      investmentSummary: json['investment_summary'] != null ? InvestmentSummary.fromJson(json['investment_summary']) : null,
      spendingTrend: (json['spending_trend'] as List? ?? [])
          .map((i) => SpendingTrendItem.fromJson(i))
          .toList(),
      categoryDistribution: (json['category_distribution'] as List? ?? [])
          .map((i) => CategoryPieItem.fromJson(i))
          .toList(),
      monthWiseTrend: (json['month_wise_trend'] as List? ?? [])
          .map((i) => MonthTrendItem.fromJson(i))
          .toList(),
      recentTransactions: (json['recent_transactions'] as List? ?? [])
          .map((i) => RecentTransaction.fromJson(i))
          .toList(),
      pendingTriageCount: json['pending_triage_count'] ?? 0,
      pendingTrainingCount: json['pending_training_count'] ?? 0,
      familyMembersCount: json['family_members_count'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'summary': summary.toJson(),
      'budget': budget.toJson(),
      'investment_summary': investmentSummary?.toJson(),
      'spending_trend': spendingTrend.map((i) => i.toJson()).toList(),
      'category_distribution': categoryDistribution.map((i) => i.toJson()).toList(),
      'month_wise_trend': monthWiseTrend.map((i) => i.toJson()).toList(),
      'recent_transactions': recentTransactions.map((i) => i.toJson()).toList(),
      'pending_triage_count': pendingTriageCount,
      'pending_training_count': pendingTrainingCount,
      'family_members_count': familyMembersCount,
    };
  }

  DashboardData copyWith({
    DashboardSummary? summary,
    BudgetSummary? budget,
    InvestmentSummary? investmentSummary,
    List<SpendingTrendItem>? spendingTrend,
    List<CategoryPieItem>? categoryDistribution,
    List<MonthTrendItem>? monthWiseTrend,
    List<RecentTransaction>? recentTransactions,
    int? pendingTriageCount,
    int? pendingTrainingCount,
    int? familyMembersCount,
  }) {
    return DashboardData(
      summary: summary ?? this.summary,
      budget: budget ?? this.budget,
      investmentSummary: investmentSummary ?? this.investmentSummary,
      spendingTrend: spendingTrend ?? this.spendingTrend,
      categoryDistribution: categoryDistribution ?? this.categoryDistribution,
      monthWiseTrend: monthWiseTrend ?? this.monthWiseTrend,
      recentTransactions: recentTransactions ?? this.recentTransactions,
      pendingTriageCount: pendingTriageCount ?? this.pendingTriageCount,
      pendingTrainingCount: pendingTrainingCount ?? this.pendingTrainingCount,
      familyMembersCount: familyMembersCount ?? this.familyMembersCount,
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
      amount: _toDouble(json['amount']),
      dailyLimit: _toDouble(json['daily_limit']),
    );
  }

  Map<String, dynamic> toJson() => {
    'date': date,
    'amount': amount,
    'daily_limit': dailyLimit,
  };
  
  DateTime get dateTime => DateTime.parse(date).toLocal();
}

class CategoryPieItem {
  final String name;
  final double value;

  CategoryPieItem({required this.name, required this.value});

  factory CategoryPieItem.fromJson(Map<String, dynamic> json) {
    return CategoryPieItem(
      name: json['name'],
      value: _toDouble(json['value']),
    );
  }

  Map<String, dynamic> toJson() => {
    'name': name,
    'value': value,
  };
}

class DashboardSummary {
  final double todayTotal;
  final double yesterdayTotal;
  final double lastMonthSameDayTotal;
  final double monthlyTotal;
  final String currency;
  final double dailyBudgetLimit;
  final double proratedBudget;

  DashboardSummary({
    required this.todayTotal,
    this.yesterdayTotal = 0.0,
    this.lastMonthSameDayTotal = 0.0,
    required this.monthlyTotal,
    required this.currency,
    this.dailyBudgetLimit = 0.0,
    this.proratedBudget = 0.0,
  });

  factory DashboardSummary.fromJson(Map<String, dynamic> json) {
    return DashboardSummary(
      todayTotal: _toDouble(json['today_total']),
      yesterdayTotal: _toDouble(json['yesterday_total']),
      lastMonthSameDayTotal: _toDouble(json['last_month_same_day_total']),
      monthlyTotal: _toDouble(json['monthly_total']),
      currency: json['currency'] ?? 'INR',
      dailyBudgetLimit: _toDouble(json['daily_budget_limit']),
      proratedBudget: _toDouble(json['prorated_budget']),
    );
  }

  Map<String, dynamic> toJson() => {
    'today_total': todayTotal,
    'yesterday_total': yesterdayTotal,
    'last_month_same_day_total': lastMonthSameDayTotal,
    'monthly_total': monthlyTotal,
    'currency': currency,
    'daily_budget_limit': dailyBudgetLimit,
    'prorated_budget': proratedBudget,
  };
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
      limit: _toDouble(json['limit']),
      spent: _toDouble(json['spent']),
      percentage: _toDouble(json['percentage']),
    );
  }

  Map<String, dynamic> toJson() => {
    'limit': limit,
    'spent': spent,
    'percentage': percentage,
  };
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
      totalInvested: _toDouble(json['total_invested']),
      currentValue: _toDouble(json['current_value']),
      profitLoss: _toDouble(json['profit_loss']),
      xirr: json['xirr'] != null ? _toDouble(json['xirr']) : null,
      sparkline: (json['sparkline'] as List? ?? []).map((v) => _toDouble(v)).toList(),
      dayChange: _toDouble(json['day_change']),
      dayChangePercent: _toDouble(json['day_change_percent']),
    );
  }

  Map<String, dynamic> toJson() => {
    'total_invested': totalInvested,
    'current_value': currentValue,
    'profit_loss': profitLoss,
    'xirr': xirr,
    'sparkline': sparkline,
    'day_change': dayChange,
    'day_change_percent': dayChangePercent,
  };
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
  final String? expenseGroupId;
  final String? expenseGroupName;
  final String? source;

  RecentTransaction({
    required this.id,
    required this.date,
    required this.description,
    required this.amount,
    required this.category,
    this.accountName,
    this.accountOwnerName,
    this.isHidden = false,
    this.expenseGroupId,
    this.expenseGroupName,
    this.source,
  });

  factory RecentTransaction.fromJson(Map<String, dynamic> json) {
    return RecentTransaction(
      id: json['id'],
      date: DateTime.parse(json['date']).toLocal(),
      description: json['description'],
      amount: _toDouble(json['amount']),
      category: json['category'],
      accountName: json['account_name'],
      accountOwnerName: json['account_owner_name'],
      isHidden: json['is_hidden'] ?? false,
      expenseGroupId: json['expense_group_id'],
      expenseGroupName: json['expense_group_name'],
      source: json['source'],
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'date': date.toUtc().toIso8601String(),
    'description': description,
    'amount': amount,
    'category': category,
    'account_name': accountName,
    'account_owner_name': accountOwnerName,
    'is_hidden': isHidden,
    'expense_group_id': expenseGroupId,
    'expense_group_name': expenseGroupName,
    'source': source,
  };

  String get formattedDate => DateFormat('MMM d, h:mm a').format(date);
}

class MonthTrendItem {
  final String month;
  final double spent;
  final double budget;
  final bool isSelected;

  MonthTrendItem({
    required this.month, 
    required this.spent, 
    required this.budget,
    this.isSelected = false,
  });

  factory MonthTrendItem.fromJson(Map<String, dynamic> json) {
    return MonthTrendItem(
      month: json['month'],
      spent: _toDouble(json['spent']),
      budget: _toDouble(json['budget']),
      isSelected: json['is_selected'] ?? false,
    );
  }

  Map<String, dynamic> toJson() => {
    'month': month,
    'spent': spent,
    'budget': budget,
    'is_selected': isSelected,
  };
}
