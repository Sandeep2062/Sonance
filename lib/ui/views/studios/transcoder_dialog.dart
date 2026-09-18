import 'dart:async';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import '../../../core/services/python_engine_service.dart';
import '../../../core/theme/app_theme.dart';

class TranscoderDialog extends StatefulWidget {
  const TranscoderDialog({super.key});

  @override
  State<TranscoderDialog> createState() => _TranscoderDialogState();
}

class _TranscoderDialogState extends State<TranscoderDialog> {
  String? _sourcePath;
  String? _destPath;
  String _format = 'flac';
  String _bitrate = 'lossless';
  bool _isRunning = false;
  final StringBuffer _logs = StringBuffer();
  StreamSubscription<String>? _sub;
  final ScrollController _scrollController = ScrollController();

  @override
  void dispose() {
    _sub?.cancel();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _pickSource() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['mp3', 'flac', 'wav', 'm4a', 'ogg', 'aac', 'dsd', 'dsf'],
    );
    if (result != null && result.files.single.path != null) {
      setState(() {
        _sourcePath = result.files.single.path;
      });
    }
  }

  Future<void> _pickSourceFolder() async {
    final folder = await FilePicker.platform.getDirectoryPath();
    if (folder != null) {
      setState(() {
        _sourcePath = folder;
      });
    }
  }

  Future<void> _pickDestFolder() async {
    final folder = await FilePicker.platform.getDirectoryPath();
    if (folder != null) {
      setState(() {
        _destPath = folder;
      });
    }
  }

  void _startTranscode() {
    if (_sourcePath == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a source audio file or folder.')),
      );
      return;
    }

    setState(() {
      _isRunning = true;
      _logs.clear();
      _logs.writeln('=== Sonance Audio Transcoder Engine Started ===');
      _logs.writeln('Source: $_sourcePath');
      _logs.writeln('Output Format: ${_format.toUpperCase()} ($_bitrate)');
      if (_destPath != null) _logs.writeln('Destination: $_destPath');
      _logs.writeln('--------------------------------------------------\n');
    });

    final stream = pythonEngineService.runTranscoder(
      source: _sourcePath!,
      outputDir: _destPath,
      format: _format,
      bitrate: _bitrate == 'lossless' ? null : _bitrate,
    );

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
          _isRunning = false;
        });
      },
      onError: (e) {
        setState(() {
          _logs.writeln('\n[Error]: $e');
          _isRunning = false;
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
                        child: const Icon(Icons.transform_rounded, color: SonanceTheme.emerald),
                      ),
                      const SizedBox(width: 12),
                      const Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Audio Transcoder Studio',
                            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                          ),
                          Text(
                            'High-fidelity batch conversion for FLAC, MP3, WAV, AAC, and OGG',
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

              // Inputs & Format Grid
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Left: Source & Destination
                  Expanded(
                    flex: 3,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Source Item:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                        const SizedBox(height: 6),
                        Row(
                          children: [
                            Expanded(
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                                decoration: BoxDecoration(
                                  color: Theme.of(context).colorScheme.surface,
                                  borderRadius: BorderRadius.circular(8),
                                  border: Border.all(color: Theme.of(context).colorScheme.outline),
                                ),
                                child: Text(
                                  _sourcePath ?? 'Select file or folder to convert...',
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(
                                    fontSize: 11,
                                    color: _sourcePath != null ? null : Colors.grey,
                                  ),
                                ),
                              ),
                            ),
                            const SizedBox(width: 6),
                            IconButton(
                              icon: const Icon(Icons.audio_file, size: 20),
                              tooltip: 'Select File',
                              onPressed: _isRunning ? null : _pickSource,
                            ),
                            IconButton(
                              icon: const Icon(Icons.folder_open, size: 20),
                              tooltip: 'Select Batch Folder',
                              onPressed: _isRunning ? null : _pickSourceFolder,
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),

                        const Text('Output Folder (Optional):', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                        const SizedBox(height: 6),
                        Row(
                          children: [
                            Expanded(
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                                decoration: BoxDecoration(
                                  color: Theme.of(context).colorScheme.surface,
                                  borderRadius: BorderRadius.circular(8),
                                  border: Border.all(color: Theme.of(context).colorScheme.outline),
                                ),
                                child: Text(
                                  _destPath ?? 'Same directory as source...',
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(
                                    fontSize: 11,
                                    color: _destPath != null ? null : Colors.grey,
                                  ),
                                ),
                              ),
                            ),
                            const SizedBox(width: 6),
                            IconButton(
                              icon: const Icon(Icons.folder_open, size: 20),
                              tooltip: 'Choose Output Folder',
                              onPressed: _isRunning ? null : _pickDestFolder,
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(width: 20),

                  // Right: Format & Bitrate
                  Expanded(
                    flex: 2,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Target Format:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                        const SizedBox(height: 6),
                        DropdownButtonFormField<String>(
                          value: _format,
                          decoration: InputDecoration(
                            isDense: true,
                            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                          ),
                          items: const [
                            DropdownMenuItem(value: 'flac', child: Text('FLAC (Lossless)')),
                            DropdownMenuItem(value: 'mp3', child: Text('MP3 (LAME CBR/VBR)')),
                            DropdownMenuItem(value: 'wav', child: Text('WAV (Uncompressed PCM)')),
                            DropdownMenuItem(value: 'm4a', child: Text('M4A / AAC')),
                            DropdownMenuItem(value: 'ogg', child: Text('OGG Vorbis')),
                          ],
                          onChanged: _isRunning ? null : (v) => setState(() => _format = v ?? 'flac'),
                        ),
                        const SizedBox(height: 14),

                        const Text('Bitrate / Quality:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                        const SizedBox(height: 6),
                        DropdownButtonFormField<String>(
                          value: _bitrate,
                          decoration: InputDecoration(
                            isDense: true,
                            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                          ),
                          items: const [
                            DropdownMenuItem(value: 'lossless', child: Text('Lossless Bit-Perfect')),
                            DropdownMenuItem(value: '320k', child: Text('320 kbps (Maximum)')),
                            DropdownMenuItem(value: '256k', child: Text('256 kbps (High)')),
                            DropdownMenuItem(value: '192k', child: Text('192 kbps (Standard)')),
                          ],
                          onChanged: _isRunning ? null : (v) => setState(() => _bitrate = v ?? 'lossless'),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Action button
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  if (_isRunning)
                    const Padding(
                      padding: EdgeInsets.only(right: 16),
                      child: SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2, color: SonanceTheme.emerald),
                      ),
                    ),
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: SonanceTheme.emerald,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                    ),
                    icon: Icon(_isRunning ? Icons.hourglass_top_rounded : Icons.play_arrow_rounded),
                    label: Text(_isRunning ? 'Transcoding...' : 'Start Transcoding'),
                    onPressed: _isRunning ? null : _startTranscode,
                  ),
                ],
              ),
              const SizedBox(height: 14),

              // Live Terminal Box
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
                          ? 'Worker console ready. Select a file/folder and click "Start Transcoding".'
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
