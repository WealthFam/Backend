class FundHolding {
  final String schemeCode;
  final String schemeName;
  final double units;
  final double currentValue;
  final double investedValue;
  final double profitLoss;
  final double dayChange;
  final double dayChangePercentage;
  final String lastUpdated;

  FundHolding({
    required this.schemeCode,
    required this.schemeName,
    required this.units,
    required this.currentValue,
    required this.investedValue,
    required this.profitLoss,
    required this.lastUpdated,
    this.dayChange = 0.0,
    this.dayChangePercentage = 0.0,
  });

  factory FundHolding.fromJson(Map<String, dynamic> json) {
    return FundHolding(
      schemeCode: json['scheme_code'],
      schemeName: json['scheme_name'],
      units: (json['units'] as num).toDouble(),
      currentValue: (json['current_value'] as num).toDouble(),
      investedValue: (json['invested_value'] as num).toDouble(),
      profitLoss: (json['profit_loss'] as num).toDouble(),
      lastUpdated: json['last_updated'] ?? '',
      dayChange: (json['day_change'] as num?)?.toDouble() ?? 0.0,
      dayChangePercentage: (json['day_change_percentage'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class PortfolioSummary {
  final double totalInvested;
  final double totalCurrent;
  final double totalPl;
  final double dayChange;
  final double dayChangePercentage;
  final List<FundHolding> holdings;

  PortfolioSummary({
    required this.totalInvested,
    required this.totalCurrent,
    required this.totalPl,
    this.dayChange = 0.0,
    this.dayChangePercentage = 0.0,
    required this.holdings,
  });

  factory PortfolioSummary.fromJson(Map<String, dynamic> json) {
    return PortfolioSummary(
      totalInvested: (json['total_invested'] as num).toDouble(),
      totalCurrent: (json['total_current'] as num).toDouble(),
      totalPl: (json['total_pl'] as num).toDouble(),
      dayChange: (json['day_change'] as num?)?.toDouble() ?? 0.0,
      dayChangePercentage: (json['day_change_percentage'] as num?)?.toDouble() ?? 0.0,
      holdings: (json['holdings'] as List)
          .map((i) => FundHolding.fromJson(i))
          .toList(),
    );
  }
}
