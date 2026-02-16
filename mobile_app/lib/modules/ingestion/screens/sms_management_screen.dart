import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:telephony/telephony.dart';
import 'package:mobile_app/core/theme/app_theme.dart';
import 'package:mobile_app/modules/ingestion/services/sms_service.dart';
import 'package:intl/intl.dart';

class SmsManagementScreen extends StatefulWidget {
  const SmsManagementScreen({super.key});

  @override
  State<SmsManagementScreen> createState() => _SmsManagementScreenState();
}

class _SmsManagementScreenState extends State<SmsManagementScreen> {
  List<SmsMessage> _messages = [];
  bool _isLoading = true;
  bool _isProcessing = false;
  final Set<String> _selectedHashes = {};
  
  final TextEditingController _filterController = TextEditingController();
  List<SmsMessage> _filteredMessages = [];

  @override
  void dispose() {
    _filterController.dispose();
    super.dispose();
  }

  void _filterMessages() {
    final query = _filterController.text.toLowerCase();
    setState(() {
      _filteredMessages = _messages.where((msg) {
        final address = (msg.address ?? '').toLowerCase();
        final body = (msg.body ?? '').toLowerCase();
        return address.contains(query) || body.contains(query);
      }).toList();
    });
  }

  @override
  void initState() {
    super.initState();
    _loadMessages();
  }

  Future<void> _loadMessages() async {
    setState(() => _isLoading = true);
    final smsService = context.read<SmsService>();
    final msgs = await smsService.getAllMessages();
    
    msgs.sort((a, b) => (b.date ?? 0).compareTo(a.date ?? 0));
    
    if (mounted) {
      setState(() {
        _messages = msgs;
        _isLoading = false;
      });
    }
  }

  Future<void> _pushSingle(SmsMessage msg) async {
    setState(() => _isProcessing = true);
    try {
      final smsService = context.read<SmsService>();
      await smsService.sendSmsToBackend(msg.address!, msg.body!, msg.date!);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('SMS pushed successfully')));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed to push: $e'), backgroundColor: AppTheme.danger));
      }
    } finally {
      if (mounted) setState(() => _isProcessing = false);
    }
  }

  Future<void> _pushBulk() async {
    if (_selectedHashes.isEmpty) return;
    
    setState(() => _isProcessing = true);
    int success = 0;
    int failed = 0;

    final smsService = context.read<SmsService>();
    
    for (final msg in _messages) {
      final hash = smsService.computeHash(msg.address ?? '', (msg.date ?? 0).toString(), msg.body ?? '');
      if (_selectedHashes.contains(hash)) {
        try {
          await smsService.sendSmsToBackend(msg.address!, msg.body!, msg.date!);
          success++;
        } catch (e) {
          failed++;
        }
      }
    }

    if (mounted) {
      setState(() {
        _isProcessing = false;
        _selectedHashes.clear();
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Bulk push complete: $success success, $failed failed'))
      );
    }
  }

  Future<void> _pickAndSyncDate() async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: DateTime.now().subtract(const Duration(days: 1)),
      firstDate: DateTime(2023),
      lastDate: DateTime.now(),
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: ColorScheme.light(
              primary: Theme.of(context).primaryColor,
            ),
          ),
          child: child!,
        );
      },
    );

    if (picked != null && mounted) {
      final confirm = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Confirm Sync'),
          content: Text('Scan and sync all SMS from ${DateFormat('dd MMM yyyy').format(picked)}? This might take a moment.'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
            TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Start Sync')),
          ],
        ),
      );

      if (confirm == true && mounted) {
        setState(() => _isProcessing = true);
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Starting Sync...')));
        
        try {
          final count = await context.read<SmsService>().syncFromDate(picked);
          if (mounted) {
             ScaffoldMessenger.of(context).showSnackBar(
               SnackBar(
                 content: Text('Sync Complete. Pushed $count new messages.'),
                 backgroundColor: AppTheme.success,
               )
             );
          }
        } catch (e) {
          if (mounted) {
             ScaffoldMessenger.of(context).showSnackBar(
               SnackBar(
                 content: Text('Sync Error: $e'),
                 backgroundColor: AppTheme.danger,
               )
             );
          }
        } finally {
          if (mounted) {
            setState(() => _isProcessing = false);
            _loadMessages(); // Refresh list to show status changes
          }
        }
      }
    }
  }

  Future<void> _deepQueryAddress() async {
    final controller = TextEditingController();
    final address = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text("Deep Search Address"),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(labelText: "Enter Sender Address / Number"),
          style: TextStyle(color: Theme.of(context).colorScheme.onSurface),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text("Cancel")),
          TextButton(onPressed: () => Navigator.pop(context, controller.text), child: const Text("Search")),
        ],
      ),
    );

    if (address != null && address.isNotEmpty && mounted) {
      setState(() => _isLoading = true);
      final msgs = await context.read<SmsService>().querySpecificAddress(address);
      if (mounted) {
        setState(() {
          _messages = msgs;
          _isLoading = false;
          _filterController.clear(); // Clear local filter to show results
        });
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Found ${msgs.length} messages from $address")));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final smsService = context.watch<SmsService>();
    final theme = Theme.of(context);
    
    // Choose list to display
    final displayList = _filterController.text.isEmpty ? _messages : _filteredMessages;

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      appBar: AppBar(
        title: Container(
          height: 40,
          decoration: BoxDecoration(
            color: theme.colorScheme.onSurface.withOpacity(0.05),
            borderRadius: BorderRadius.circular(8),
          ),
          child: TextField(
            controller: _filterController,
            onChanged: (_) => _filterMessages(),
            style: TextStyle(color: theme.colorScheme.onSurface, fontSize: 16, height: 1.0),
            cursorColor: theme.colorScheme.primary,
            textAlignVertical: TextAlignVertical.center,
            decoration: InputDecoration(
               hintText: "Search SMS...",
               hintStyle: TextStyle(color: theme.colorScheme.onSurfaceVariant),
               border: InputBorder.none,
               prefixIcon: Icon(Icons.search, color: theme.colorScheme.onSurfaceVariant, size: 20),
               contentPadding: const EdgeInsets.symmetric(horizontal: 0, vertical: 0),
               isDense: true,
            ),
          ),
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.saved_search, color: theme.colorScheme.onSurface),
            tooltip: 'Deep Search Address',
            onPressed: _isProcessing ? null : _deepQueryAddress,
          ),
          IconButton(
            icon: Icon(Icons.calendar_month, color: theme.colorScheme.onSurface),
            tooltip: 'Sync from Date',
            onPressed: _isProcessing ? null : _pickAndSyncDate,
          ),
          IconButton(
            icon: Icon(Icons.refresh, color: theme.colorScheme.onSurface),
            onPressed: _isLoading ? null : _loadMessages,
          ),
          if (_selectedHashes.isNotEmpty)
            TextButton(
              onPressed: _isProcessing ? null : _pushBulk,
              child: Text('PUSH (${_selectedHashes.length})', style: TextStyle(color: theme.colorScheme.primary, fontWeight: FontWeight.bold)),
            ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : displayList.isEmpty
              ? Center(child: Text(_filterController.text.isEmpty ? 'No SMS messages found' : 'No matching SMS found', 
                  style: TextStyle(color: theme.colorScheme.onSurfaceVariant)))
              : ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: displayList.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (context, index) {
                    final msg = displayList[index];
                    final hash = smsService.computeHash(msg.address ?? '', (msg.date ?? 0).toString(), msg.body ?? '');
                    final isSynced = smsService.isCached(hash);
                    final isSelected = _selectedHashes.contains(hash);

                    return _buildSmsCard(msg, hash, isSynced, isSelected);
                  },
                ),
    );
  }

  Widget _buildSmsCard(SmsMessage msg, String hash, bool isSynced, bool isSelected) {
    final theme = Theme.of(context);
    final date = msg.date != null ? DateTime.fromMillisecondsSinceEpoch(msg.date!) : DateTime.now();
    final dateStr = DateFormat('dd MMM yyyy, hh:mm a').format(date);

    return InkWell(
      onLongPress: isSynced ? null : () {
        setState(() {
          if (isSelected) {
            _selectedHashes.remove(hash);
          } else {
            _selectedHashes.add(hash);
          }
        });
      },
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: isSelected ? theme.primaryColor.withOpacity(0.1) : theme.colorScheme.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isSelected ? theme.primaryColor : (isSynced ? AppTheme.success.withOpacity(0.3) : theme.dividerColor),
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  msg.address ?? 'Unknown',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: theme.colorScheme.onSurface),
                ),
                if (isSynced)
                  Row(
                    children: [
                      const Icon(Icons.cloud_done, color: AppTheme.success, size: 16),
                      const SizedBox(width: 4),
                      Text('Synced', style: TextStyle(color: AppTheme.success, fontSize: 12, fontWeight: FontWeight.bold)),
                    ],
                  )
                else
                  Row(
                    children: [
                      const Icon(Icons.cloud_off, color: AppTheme.warning, size: 16),
                      const SizedBox(width: 4),
                      Text('Pending', style: TextStyle(color: AppTheme.warning, fontSize: 12, fontWeight: FontWeight.bold)),
                    ],
                  ),
              ],
            ),
            const SizedBox(height: 4),
            Text(dateStr, style: TextStyle(color: theme.colorScheme.onSurfaceVariant, fontSize: 12)),
            const SizedBox(height: 12),
            Text(
              msg.body ?? '',
              style: TextStyle(color: theme.colorScheme.onSurface, fontSize: 14),
            ),
            if (!isSynced) ...[
              const SizedBox(height: 16),
              Align(
                alignment: Alignment.centerRight,
                child: ElevatedButton.icon(
                  onPressed: _isProcessing ? null : () => _pushSingle(msg),
                  icon: const Icon(Icons.upload, size: 16),
                  label: const Text('Push Now'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: theme.primaryColor,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
