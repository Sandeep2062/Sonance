import 'package:flutter/material.dart';
import '../../../core/services/python_engine_service.dart';
import '../../../core/theme/app_theme.dart';

class ListeningStatsDialog extends StatefulWidget {
  const ListeningStatsDialog({super.key});

  @override
  State<ListeningStatsDialog> createState() => _ListeningStatsDialogState();
}

class _ListeningStatsDialogState extends State<ListeningStatsDialog> {
  bool _isLoading = true;
  String _statsText = '';

  @override
  void initState() {
    super.initState();
    _loadStats();
  }

  Future<void> _loadStats() async {
    setState(() => _isLoading = true);
    final res = await pythonEngineService.getListeningStats();
    setState(() {
      _isLoading = false;
      _statsText = res.stdout.isNotEmpty
          ? res.stdout
          : res.stderr.isNotEmpty
              ? res.stderr
              : 'No listening activity recorded yet. Start playing music to build your local listening stats!';
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
        constraints: const BoxConstraints(maxWidth: 720, maxHeight: 600),
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
                        child: const Icon(Icons.insights_rounded, color: SonanceTheme.emerald),
                      ),
                      const SizedBox(width: 12),
                      const Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Sonance Wrapped & Listening Stats',
                            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                          ),
                          Text(
                            'Local listening habits, top tracks, most played artists, and audiophile stats',
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

              // Content
              Expanded(
                child: _isLoading
                    ? const Center(
                        child: CircularProgressIndicator(color: SonanceTheme.emerald),
                      )
                    : Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: isDark ? const Color(0xFF07090E) : const Color(0xFF0F172A),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: Colors.white10),
                        ),
                        child: SingleChildScrollView(
                          child: Text(
                            _statsText,
                            style: const TextStyle(
                              fontFamily: 'monospace',
                              fontSize: 12,
                              color: Color(0xFF10B981),
                              height: 1.5,
                            ),
                          ),
                        ),
                      ),
              ),
              const SizedBox(height: 16),

              // Footer
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton.icon(
                    icon: const Icon(Icons.refresh, size: 18),
                    label: const Text('Refresh'),
                    onPressed: _loadStats,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
