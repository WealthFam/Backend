double _toDouble(dynamic value) {
  if (value == null) return 0.0;
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value) ?? 0.0;
  return 0.0;
}

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
      units: _toDouble(json['units']),
      currentValue: _toDouble(json['current_value']),
      investedValue: _toDouble(json['invested_value']),
      profitLoss: _toDouble(json['profit_loss']),
      lastUpdated: json['last_updated'] ?? '',
      dayChange: _toDouble(json['day_change']),
      dayChangePercentage: _toDouble(json['day_change_percentage']),
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
      totalInvested: _toDouble(json['total_invested']),
      totalCurrent: _toDouble(json['total_current']),
      totalPl: _toDouble(json['total_pl']),
      dayChange: _toDouble(json['day_change']),
      dayChangePercentage: _toDouble(json['day_change_percentage']),
      holdings: (json['holdings'] as List)
          .map((i) => FundHolding.fromJson(i))
          .toList(),
    );
  }
}
