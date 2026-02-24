import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:mobile_app/core/config/app_config.dart';
import 'package:mobile_app/core/theme/app_theme.dart';
import 'package:mobile_app/modules/auth/services/auth_service.dart';
import 'package:mobile_app/modules/auth/services/security_service.dart';
import 'package:mobile_app/modules/ingestion/services/sms_service.dart';
import 'package:mobile_app/modules/ingestion/screens/sms_management_screen.dart';


class SyncSettingsScreen extends StatefulWidget {
  const SyncSettingsScreen({super.key});

  @override
  State<SyncSettingsScreen> createState() => _SyncSettingsScreenState();
}

class _SyncSettingsScreenState extends State<SyncSettingsScreen> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _backendCtrl;
  late TextEditingController _deviceIdCtrl;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    final config = context.read<AppConfig>();
    final auth = context.read<AuthService>();
    _backendCtrl = TextEditingController(text: config.backendUrl);
    _deviceIdCtrl = TextEditingController(text: auth.deviceId ?? '');
  }

  @override
  void dispose() {
    _backendCtrl.dispose();
    _deviceIdCtrl.dispose();
    super.dispose();
  }

  Future<void> _saveConfig() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isLoading = true);
    
    await context.read<AppConfig>().setUrls(
      backend: _backendCtrl.text.trim(),
      webUi: context.read<AppConfig>().webUiUrl, // Keep old one around internally so we don't break AppConfig method
    );

    if (_deviceIdCtrl.text.isNotEmpty) {
      await context.read<AuthService>().setDeviceId(_deviceIdCtrl.text.trim());
    }
    
    await Future.delayed(const Duration(milliseconds: 500));
    if (mounted) {
       setState(() => _isLoading = false);
       ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Configuration Saved')));
    }
  }
  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();
    final config = context.watch<AppConfig>();
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Device Status',
              style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 24),
            
            _buildStatusCard(
              context,
              icon: Icons.check_circle,
              color: AppTheme.success,
              title: 'Authenticated',
              subtitle: 'Logged in as tenant ${auth.isApproved ? "(Approved)" : "(Pending)"}',
            ),
            
            const SizedBox(height: 32),
            Text(
              'Configuration',
              style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: theme.colorScheme.surface,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: theme.dividerColor),
              ),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('SERVER SETUP', style: TextStyle(color: theme.colorScheme.onSurfaceVariant, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 1.1)),
                      if (_isLoading)
                        const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      else
                        IconButton(
                          icon: const Icon(Icons.save, size: 16, color: AppTheme.primary),
                          onPressed: _saveConfig,
                          tooltip: 'Save Configuration',
                        ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _backendCtrl,
                    style: TextStyle(color: theme.colorScheme.onSurface, fontSize: 13),
                    decoration: InputDecoration(
                      labelText: 'Backend API URL',
                      contentPadding: EdgeInsets.zero,
                      isDense: true,
                    ),
                    validator: (v) => v!.isEmpty ? 'Required' : null,
                  ),
                  const SizedBox(height: 24),
                  Text('APP SECURITY', style: TextStyle(color: theme.colorScheme.onSurfaceVariant, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 1.1)),
                  const SizedBox(height: 8),
                  _buildSecurityToggle(
                    context,
                    title: 'Biometric Lock',
                    subtitle: 'Require fingerprint/face to open',
                    value: context.watch<SecurityService>().isBiometricEnabled,
                    onChanged: (v) => context.read<SecurityService>().setBiometricEnabled(v),
                  ),
                  _buildSecurityToggle(
                    context,
                    title: 'Privacy Masking',
                    subtitle: 'Blur app in multitasking view',
                    value: context.watch<SecurityService>().isPrivacyEnabled,
                    onChanged: (v) => context.read<SecurityService>().setPrivacyEnabled(v),
                  ),
                  _buildSecurityToggle(
                    context,
                    title: 'Show Data In Backend',
                    subtitle: 'Include location & complete payload',
                    value: config.sendDebugPayload,
                    onChanged: (v) => context.read<AppConfig>().setDebugPayload(v),
                  ),
                  Divider(height: 32, color: theme.dividerColor),
                  Text('DEVICE IDENTIFIER', style: TextStyle(color: theme.colorScheme.onSurfaceVariant, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 1.1)),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _deviceIdCtrl,
                    style: TextStyle(color: theme.colorScheme.onSurface, fontSize: 13, fontFamily: 'monospace'),
                    decoration: InputDecoration(
                      labelText: 'Device ID',
                      contentPadding: EdgeInsets.zero,
                      isDense: true,
                      suffixIcon: IconButton(
                        icon: const Icon(Icons.copy, size: 16),
                        onPressed: () {
                           Clipboard.setData(ClipboardData(text: _deviceIdCtrl.text));
                           ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Copied!')));
                        },
                      )
                    ),
                    validator: (v) => v!.isEmpty ? 'Required' : null,
                  ),
                ],
              ),
            ),
            ),
            
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton(
                onPressed: () {
                  context.read<AuthService>().logout();
                },
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppTheme.danger,
                  side: const BorderSide(color: AppTheme.danger),
                  padding: const EdgeInsets.all(16),
                ),
                child: const Text('Sign Out'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildConfigItem(String label, String value) {
    final theme = Theme.of(context);
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(width: 70, child: Text('$label:', style: TextStyle(color: theme.colorScheme.onSurfaceVariant, fontSize: 12))),
        Expanded(child: Text(value, style: TextStyle(color: theme.colorScheme.onSurface, fontSize: 12, overflow: TextOverflow.ellipsis))),
      ],
    );
  }

  Widget _buildStatusCard(BuildContext context, {
    required IconData icon, 
    required Color color, 
    required String title, 
    required String subtitle,
    Widget? trailing,
  }) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: theme.dividerColor),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: color.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, color: color),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                Text(subtitle, style: TextStyle(color: theme.colorScheme.onSurfaceVariant, fontSize: 14)),
              ],
            ),
          ),
          if (trailing != null) trailing,
        ],
      ),
    );
  }

  // Removed _buildSyncHealthCard and _buildHealthStat as they were moved to Dashboard

  Widget _buildSecurityToggle(BuildContext context, {
    required String title,
    required String subtitle,
    required bool value,
    required Function(bool) onChanged,
  }) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      title: Text(title, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
      subtitle: Text(subtitle, style: const TextStyle(fontSize: 12)),
      trailing: Switch(
        value: value,
        onChanged: onChanged,
        activeThumbColor: AppTheme.primary,
      ),
    );
  }
}
