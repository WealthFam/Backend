import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/core/config/app_config.dart';
import 'package:mobile_app/core/theme/app_theme.dart';
import 'package:mobile_app/modules/auth/screens/login_screen.dart';
import 'package:mobile_app/modules/auth/services/auth_service.dart';
import 'package:mobile_app/modules/ingestion/services/sms_service.dart';
import 'package:mobile_app/modules/auth/services/security_service.dart';
import 'package:mobile_app/modules/auth/components/biometric_gate.dart';
import 'package:mobile_app/modules/home/screens/home_screen.dart';
import 'package:mobile_app/core/services/notification_service.dart';
import 'package:mobile_app/modules/home/services/dashboard_service.dart';
import 'package:mobile_app/modules/home/services/funds_service.dart';
import 'package:mobile_app/modules/home/services/categories_service.dart';
import 'package:mobile_app/modules/home/services/goals_service.dart';
import 'package:mobile_app/modules/vault/services/vault_service.dart';
import 'package:mobile_app/core/services/foreground_service.dart';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize communication port for Foreground Task (v9.0+)
  FlutterForegroundTask.initCommunicationPort();
  
  // 1. Critical Services (Blocking)
  final config = AppConfig();
  await config.init();
  
  final auth = AuthService(config);
  await auth.init();

  final security = SecurityService();
  await security.init();

  final sms = SmsService(config, auth);
  await sms.init(); 

  // 2. Secondary Services (Non-blocking)
  _initSecondaryServices();

  final dashboard = DashboardService(config, auth);
  final funds = FundsService(config, auth);
  final categories = CategoriesService(config, auth);
  final vault = VaultService(config, auth);
  final goals = GoalsService(config, auth);
  
  // Listen for data from Foreground Task Isolate
  FlutterForegroundTask.addTaskDataCallback((data) {
    if (data is Map && data['type'] == 'masking_update') {
      dashboard.updateMaskingFromForeground(data['value']);
    }
  });

  runApp(MyApp(
    config: config, 
    auth: auth, 
    sms: sms, 
    security: security, 
    dashboard: dashboard, 
    funds: funds,
    categories: categories,
    vault: vault,
    goals: goals,
  ));
}

/// Start background services without blocking main app startup
Future<void> _initSecondaryServices() async {
  try {
    await NotificationService().init().timeout(const Duration(seconds: 5));
    await ForegroundServiceWrapper.init().timeout(const Duration(seconds: 5));
    debugPrint("Secondary services (Notifications, Foreground) initialized.");
  } catch (e) {
    debugPrint("Background Service Init Error: $e");
  }
}

class MyApp extends StatelessWidget {
  final AppConfig config;
  final AuthService auth;
  final SmsService sms;
  final SecurityService security;
  final DashboardService dashboard;
  final FundsService funds;
  final CategoriesService categories;
  final VaultService vault;
  final GoalsService goals;

  const MyApp({
    super.key, 
    required this.config, 
    required this.auth, 
    required this.sms, 
    required this.security, 
    required this.dashboard,
    required this.funds,
    required this.categories,
    required this.vault,
    required this.goals,
  });

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: config),
        ChangeNotifierProvider.value(value: auth),
        ChangeNotifierProvider.value(value: security),
        ChangeNotifierProvider.value(value: sms),
        ChangeNotifierProvider.value(value: dashboard),
        ChangeNotifierProvider.value(value: funds),
        ChangeNotifierProvider.value(value: categories),
        ChangeNotifierProvider.value(value: vault),
        ChangeNotifierProvider.value(value: goals),
      ],
      child: Consumer<AuthService>(
        builder: (context, auth, _) {
          return MaterialApp(
            title: 'WealthFam',
            debugShowCheckedModeBanner: false,
            theme: AppTheme.lightTheme,
            home: auth.isAuthenticated 
                ? BiometricGate(child: const HomeScreen()) 
                : const LoginScreen(),
          );
        },
      ),
    );
  }
}
