import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:mobile_app/core/theme/app_theme.dart';
import 'package:mobile_app/modules/home/models/unparsed_message.dart';
import 'package:mobile_app/modules/home/services/dashboard_service.dart';
import 'package:mobile_app/modules/home/services/categories_service.dart';
import 'package:mobile_app/modules/home/models/transaction_category.dart';

class ForensicAnnotationForm extends StatefulWidget {
  final UnparsedMessage message;
  final VoidCallback onComplete;

  const ForensicAnnotationForm({super.key, required this.message, required this.onComplete});

  @override
  State<ForensicAnnotationForm> createState() => _ForensicAnnotationFormState();
}

class _ForensicAnnotationFormState extends State<ForensicAnnotationForm> {
  late TextEditingController _amountController;
  late TextEditingController _descController;
  DateTime _date = DateTime.now();
  String _category = 'Uncategorized';
  String? _selectedAccountId;
  bool _createRule = true;
  bool _isAIParsing = false;

  @override
  void initState() {
    super.initState();
    _amountController = TextEditingController();
    _descController = TextEditingController();
    _date = widget.message.receivedAt;
  }

  void _runAIForensic() async {
    setState(() => _isAIParsing = true);
    try {
      final result = await context.read<DashboardService>().aiForensicParse(widget.message.content);
      setState(() {
        _amountController.text = (result['amount'] ?? 0).toString();
        _descController.text = result['description'] ?? '';
        _category = result['category'] ?? 'Uncategorized';
        _isAIParsing = false;
      });
    } catch (e) {
      setState(() => _isAIParsing = false);
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('AI Extraction Failed')));
    }
  }

  List<dynamic> _accounts = [];
  bool _isLoadingAccounts = true;

  void _loadAccounts() async {
    final accs = await context.read<DashboardService>().fetchAccounts();
    if (mounted) {
      setState(() {
        _accounts = accs;
        _isLoadingAccounts = false;
      });
    }
  }

  void _submit() async {
    if (_selectedAccountId == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Select an Account')));
      return;
    }

    try {
      final selectedAcc = _accounts.firstWhere((a) => a['id'] == _selectedAccountId);
      final mask = selectedAcc['account_mask'] ?? 'UNKNOWN';

      await context.read<DashboardService>().finalizeTraining(
        messageId: widget.message.id,
        date: _date,
        description: _descController.text,
        amount: double.tryParse(_amountController.text) ?? 1.0,
        category: _category,
        accountMask: mask.toString(),
        createRule: _createRule,
      );
      widget.onComplete();
      Navigator.pop(context);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed: $e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final categories = context.watch<CategoriesService>().categories;
    if (_isLoadingAccounts) {
       _loadAccounts();
    }
    final accounts = _accounts;

    return Container(
      decoration: BoxDecoration(color: theme.scaffoldBackgroundColor, borderRadius: const BorderRadius.vertical(top: Radius.circular(30))),
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Text('Neural Forensic', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
                const Spacer(),
                if (!_isAIParsing) TextButton.icon(
                  onPressed: _runAIForensic,
                  icon: const Icon(Icons.auto_awesome, size: 16),
                  label: const Text('AI Parse'),
                  style: TextButton.styleFrom(foregroundColor: AppTheme.primary),
                ) else const CircularProgressIndicator(strokeWidth: 2),
              ],
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: theme.colorScheme.surface, borderRadius: BorderRadius.circular(16)),
              child: Text(widget.message.content, style: const TextStyle(fontFamily: 'Courier', fontSize: 12)),
            ),
            const SizedBox(height: 24),
            TextField(controller: _amountController, decoration: const InputDecoration(labelText: 'Amount'), keyboardType: TextInputType.number),
            const SizedBox(height: 16),
            TextField(controller: _descController, decoration: const InputDecoration(labelText: 'Description')),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              value: _selectedAccountId,
              items: accounts.map((a) => DropdownMenuItem<String>(
                value: a['id'] as String, 
                child: Text(a['name'] as String)
              )).toList(),
              onChanged: (v) => setState(() => _selectedAccountId = v),
              decoration: const InputDecoration(labelText: 'Account'),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: _submit,
              style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: Colors.white, minimumSize: const Size(double.infinity, 50), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16))),
              child: const Text('Finalize Transaction', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ],
        ),
      ),
    );
  }
}
