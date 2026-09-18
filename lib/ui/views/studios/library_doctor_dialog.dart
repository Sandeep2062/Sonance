import 'dart:async';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import '../../../core/services/python_engine_service.dart';
import '../../../core/theme/app_theme.dart';

class LibraryDoctorDialog extends StatefulWidget {
  const LibraryDoctorDialog({super.key});

  @override
  State<LibraryDoctorDialog> createState() => _LibraryDoctorDialogState();
}

class _LibraryDoctorDialogState extends State<LibraryDoctorDialog> {
  String? _selectedFolder;
  bool _isScanning = false;
  final StringBuffer _logs = StringBuffer();
  StreamSubscription<String>? _sub;
  final ScrollController _scrollController = ScrollController();

  @override
  void dispose() {
    _sub?.cancel();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _pickFolder() async {
    final folder = await FilePicker.platform.getDirectoryPath();
    if (folder != null) {
      setState(() {
        _selectedFolder = folder;
      });
    }
  }

  void _startDoctorScan() {
    if (_selectedFolder == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please choose a music folder to scan.')),
      );
      return;
    }

    setState(() {
      _isScanning = true;
      _logs.clear();
      _logs.writeln('=== Sonance Library Doctor — Integrity & Health Diagnostic ===');
      _logs.writeln('Target Library: $_selectedFolder');
      _logs.writeln('Scanning audio bitstreams, companion .lrc lyrics, and duplicate hashes...\n');
    });

    final stream = pythonEngineService.runLibraryDoctor(_selectedFolder!);

    _sub = stream.listen(
      (chunk) {
        setState(() {
          _logs.write(chunk);
        });
        if (_scrollController.hasClients) {
          _scrollController.animateTo(
            _scrollController.position.maxScrollExtent,
            duration: const Duration(milliseconds: 100),
            curve: Curves.easeOut,
          );
        }
      },
      onDone: () {
        setState(() {
          _isScanning = false;
        });
      },
      onError: (e) {
        setState(() {
          _logs.writeln('\n[Doctor Error]: $e');
          _isScanning = false;
        });
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Dialog(
      backgroundColor: isDark ? SonanceTheme.darkSurface : SonanceTheme.lightSurface,
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: Theme.of(context).colorScheme.outline),
      ),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 820, maxHeight: 680),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: SonanceTheme.emerald.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Icon(Icons.health_and_safety_rounded, color: SonanceTheme.emerald),
                      ),
                      const SizedBox(width: 12),
                      const Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Sonance Library Doctor',
                            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                          ),
                          Text(
                            'Scan health score, detect duplicate audio files, fix broken tags, and audit missing LRCs',
                            style: TextStyle(fontSize: 11, color: Colors.grey),
                          ),
                        ],
                      ),
                    ],
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
              const Divider(height: 24),

              // Folder selection & Action
              Row(
                children: [
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.surface,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Theme.of(context).colorScheme.outline),
                      ),
                      child: Text(
                        _selectedFolder ?? 'Select music library directory to scan...',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 12,
                          color: _selectedFolder != null ? null : Colors.grey,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Theme.of(context).colorScheme.surface,
                      foregroundColor: Theme.of(context).colorScheme.onSurface,
                      side: BorderSide(color: Theme.of(context).colorScheme.outline),
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
                    ),
                    icon: Icon(Icons.folder_open, color: Theme.of(context).colorScheme.primary),
                    label: const Text('Browse'),
                    onPressed: _isScanning ? null : _pickFolder,
                  ),
                  const SizedBox(width: 12),
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: SonanceTheme.emerald,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                    ),
                    icon: Icon(_isScanning ? Icons.hourglass_empty : Icons.medical_services_rounded),
                    label: Text(_isScanning ? 'Diagnosing...' : 'Start Diagnosis'),
                    onPressed: _isScanning ? null : _startDoctorScan,
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Diagnostic Log Output
              Expanded(
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: isDark ? const Color(0xFF07090E) : const Color(0xFF0F172A),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: Colors.white10),
                  ),
                  child: SingleChildScrollView(
                    controller: _scrollController,
                    child: Text(
                      _logs.isEmpty
                          ? 'Library Doctor ready. Select a folder and click "Start Diagnosis" to audit audio health.'
                          : _logs.toString(),
                      style: const TextStyle(
                        fontFamily: 'monospace',
                        fontSize: 11,
                        color: Color(0xFF10B981),
                        height: 1.4,
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
