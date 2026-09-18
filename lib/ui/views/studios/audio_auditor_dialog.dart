import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import '../../../core/services/python_engine_service.dart';
import '../../../core/theme/app_theme.dart';

class AudioAuditorDialog extends StatefulWidget {
  const AudioAuditorDialog({super.key});

  @override
  State<AudioAuditorDialog> createState() => _AudioAuditorDialogState();
}

class _AudioAuditorDialogState extends State<AudioAuditorDialog> {
  String? _selectedFile;
  bool _isAuditing = false;
  String? _auditResult;

  Future<void> _pickAudioFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['flac', 'wav', 'mp3', 'm4a', 'ogg', 'aiff', 'dsf'],
    );
    if (result != null && result.files.single.path != null) {
      setState(() {
        _selectedFile = result.files.single.path;
        _auditResult = null;
      });
    }
  }

  Future<void> _runAudit() async {
    if (_selectedFile == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select an audio file to audit.')),
      );
      return;
    }

    setState(() {
      _isAuditing = true;
      _auditResult = 'Auditing audio spectrum & metadata tags...';
    });

    final res = await pythonEngineService.auditAudioFile(_selectedFile!);

    setState(() {
      _isAuditing = false;
      _auditResult = res.stdout.isNotEmpty
          ? res.stdout
          : res.stderr.isNotEmpty
              ? res.stderr
              : 'Audit finished. No anomalies detected.';
    });
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
        constraints: const BoxConstraints(maxWidth: 780, maxHeight: 620),
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
                        child: const Icon(Icons.verified_rounded, color: SonanceTheme.emerald),
                      ),
                      const SizedBox(width: 12),
                      const Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Audio Quality & Lossless Auditor',
                            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                          ),
                          Text(
                            'Detect fake upsampled FLACs, verify true sample rate and bit depth',
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

              // File Picker & Audit trigger
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
                        _selectedFile ?? 'Select audio track (.flac, .wav, .mp3)...',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 12,
                          color: _selectedFile != null ? null : Colors.grey,
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
                    icon: Icon(Icons.file_open_rounded, color: Theme.of(context).colorScheme.primary),
                    label: const Text('Browse'),
                    onPressed: _isAuditing ? null : _pickAudioFile,
                  ),
                  const SizedBox(width: 12),
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: SonanceTheme.emerald,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                    ),
                    icon: Icon(_isAuditing ? Icons.hourglass_top : Icons.analytics_rounded),
                    label: Text(_isAuditing ? 'Auditing...' : 'Audit File'),
                    onPressed: _isAuditing ? null : _runAudit,
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Audit Report
              Expanded(
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: isDark ? const Color(0xFF07090E) : const Color(0xFF0F172A),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: Colors.white10),
                  ),
                  child: SingleChildScrollView(
                    child: Text(
                      _auditResult ??
                          'Select an audio file and click "Audit File" to run deep bit-stream and spectral verification.',
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
