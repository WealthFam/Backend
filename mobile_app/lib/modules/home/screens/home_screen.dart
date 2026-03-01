import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:provider/provider.dart';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';
import 'package:mobile_app/modules/home/screens/dashboard_screen.dart';
import 'package:mobile_app/core/theme/app_theme.dart';
import 'package:mobile_app/modules/auth/services/auth_service.dart';
import 'package:mobile_app/modules/ingestion/services/sms_service.dart';
import 'package:mobile_app/modules/config/screens/config_screen.dart';
import 'package:mobile_app/modules/vault/screens/vault_screen.dart';
import 'package:mobile_app/modules/home/screens/categories_management_screen.dart';
import 'package:mobile_app/modules/home/screens/goals_screen.dart';
import 'package:mobile_app/modules/home/screens/expense_groups_screen.dart';

import 'package:mobile_app/modules/config/screens/sync_settings_screen.dart';
import 'package:mobile_app/modules/home/screens/mutual_funds_screen.dart';
import 'package:mobile_app/modules/ingestion/screens/sms_management_screen.dart';


class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();

  @override
  void initState() {
    super.initState();
    // Sync unsynced messages on app open
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<SmsService>().syncUnsyncedOnStart();
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    final scaffold = WithForegroundTask(
      child: Scaffold(
        key: _scaffoldKey,
        backgroundColor: theme.scaffoldBackgroundColor,
        // No AppBar here; DashboardScreen handles its own SliverAppBar
        drawer: _buildDrawer(context),
        body: SafeArea(
          child: DashboardScreen(
            onMenuPressed: () => _scaffoldKey.currentState?.openDrawer(),
          ),
        ),
      ),
    );

    if (kIsWeb) {
      return Center(
        child: Container(
          constraints: const BoxConstraints(maxWidth: 450),
          decoration: BoxDecoration(
            color: theme.scaffoldBackgroundColor,
            border: Border.symmetric(vertical: BorderSide(color: theme.dividerColor, width: 1)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.2),
                blurRadius: 20,
                offset: const Offset(0, 10),
              )
            ],
          ),
          child: scaffold,
        ),
      );
    }
    
    return scaffold;
  }

  Widget _buildDrawer(BuildContext context) {
    final auth = context.read<AuthService>();
    final theme = Theme.of(context);
    final userName = "User";
    final userEmail = auth.userRole ?? "Family Member";

    return Drawer(
      child: Column(
        children: [
          UserAccountsDrawerHeader(
            accountName: Text(auth.isApproved ? "Hi $userName" : "Pending Approval", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
            accountEmail: Text(userEmail),
            currentAccountPicture: CircleAvatar(
              backgroundColor: Colors.white,
              child: Icon(Icons.person, color: theme.primaryColor, size: 40),
            ),
            decoration: BoxDecoration(color: theme.primaryColor),
          ),
          ListTile(
            leading: const Icon(Icons.dashboard_outlined),
            title: const Text('Dashboard'),
            onTap: () {
              Navigator.pop(context);
            },
          ),
          ListTile(
            leading: const Icon(Icons.message_outlined),
            title: const Text('SMS Management'),
            onTap: () {
              Navigator.pop(context);
              Navigator.push(context, MaterialPageRoute(builder: (_) => const SmsManagementScreen()));
            },
          ),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.trending_up),
            title: const Text('Mutual Funds'),
            onTap: () {
              Navigator.pop(context);
              Navigator.push(context, MaterialPageRoute(builder: (_) => const MutualFundsScreen()));
            },
          ),
          ListTile(
            leading: const Icon(Icons.group_outlined),
            title: const Text('Expense Groups'),
            onTap: () {
              Navigator.pop(context);
              Navigator.push(context, MaterialPageRoute(builder: (_) => const ExpenseGroupsScreen()));
            },
          ),
          ListTile(
            leading: const Icon(Icons.track_changes),
            title: const Text('Investment Goals'),
            onTap: () {
              Navigator.pop(context);
              Navigator.push(context, MaterialPageRoute(builder: (_) => const GoalsScreen()));
            },
          ),
          ListTile(
            leading: const Icon(Icons.local_offer_outlined),
            title: const Text('Categories'),
            onTap: () {
              Navigator.pop(context);
              Navigator.push(context, MaterialPageRoute(builder: (_) => const CategoriesManagementScreen()));
            },
          ),
          ListTile(
            leading: const Icon(Icons.folder_shared_outlined),
            title: const Text('Documents Vault'),
            onTap: () {
              Navigator.pop(context);
              Navigator.push(context, MaterialPageRoute(builder: (_) => const VaultScreen()));
            },
          ),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.settings_outlined),
            title: const Text('Settings'),
            onTap: () {
              Navigator.pop(context);
              Navigator.push(context, MaterialPageRoute(builder: (_) => const SyncSettingsScreen()));
            },
          ),

          const Spacer(),
          ListTile(
            leading: const Icon(Icons.logout, color: AppTheme.danger),
            title: const Text('Sign Out', style: TextStyle(color: AppTheme.danger)),
            onTap: () => _confirmSignOut(context),
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  void _confirmSignOut(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Sign Out'),
        content: const Text('Are you sure you want to sign out from WealthFam?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context); // Close dialog
              Navigator.pop(context); // Close drawer
              context.read<AuthService>().logout();
            },
            child: const Text('Sign Out', style: TextStyle(color: AppTheme.danger)),
          ),
        ],
      ),
    );
  }
}
