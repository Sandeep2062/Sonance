import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../equalizer_view.dart';
import 'transcoder_dialog.dart';
import 'library_doctor_dialog.dart';
import 'audio_auditor_dialog.dart';
import 'listening_stats_dialog.dart';

class StudiosView extends StatelessWidget {
  const StudiosView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Top Header
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Audiophile Studios & DSP Suite',
                      style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'High-performance native audio tools with zero-overhead on-demand workers',
                      style: TextStyle(
                        fontSize: 13,
                        color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                      ),
                    ),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: SonanceTheme.emerald.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: SonanceTheme.emerald.withOpacity(0.3)),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.bolt_rounded, color: SonanceTheme.emerald, size: 16),
                      SizedBox(width: 6),
                      Text(
                        'Engine: Native Flutter (~40-80 MB RAM)',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: SonanceTheme.emerald,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // Section 1: Mastering & DSP
            _buildSectionHeader(context, 'Mastering & Dynamics DSP', Icons.tune_rounded),
            const SizedBox(height: 12),
            _buildGrid(context, [
              _StudioCard(
                title: '10-Band Studio Hardware EQ',
                description: 'Audiophile peaking filters (32 Hz - 16 kHz) with preamp stage and 8 tuned presets.',
                icon: Icons.equalizer_rounded,
                badge: 'REALTIME',
                badgeColor: SonanceTheme.emerald,
                onTap: () => showDialog(context: context, builder: (_) => const EqualizerDialog()),
              ),
              _StudioCard(
                title: 'Audio Transcoder & Converter',
                description: 'Batch convert audio to Bit-Perfect FLAC, MP3 320k, WAV, AAC, and OGG Vorbis.',
                icon: Icons.transform_rounded,
                badge: 'BATCH',
                badgeColor: Colors.blueAccent,
                onTap: () => showDialog(context: context, builder: (_) => const TranscoderDialog()),
              ),
              _StudioCard(
                title: 'Zenith Mastering Orchestrator',
                description: '7-stage mastering chain: LA-2A vintage compressor, true-peak limiter, and tape sheen.',
                icon: Icons.auto_awesome,
                badge: 'MASTERING',
                badgeColor: Colors.amberAccent,
                onTap: () => _showZenithNotice(context),
              ),
            ]),

            const SizedBox(height: 28),

            // Section 2: Audio Forensics & Quality Inspection
            _buildSectionHeader(context, 'Audio Forensics & Lossless Verification', Icons.security_rounded),
            const SizedBox(height: 12),
            _buildGrid(context, [
              _StudioCard(
                title: 'Lossless Authenticity Auditor',
                description: 'Detect fake upsampled FLACs, cut-off MP3 transients, bit depth, and spectral range.',
                icon: Icons.verified_rounded,
                badge: 'AUDITOR',
                badgeColor: SonanceTheme.emerald,
                onTap: () => showDialog(context: context, builder: (_) => const AudioAuditorDialog()),
              ),
              _StudioCard(
                title: 'Library Doctor & Duplicates',
                description: 'Scan library health score, detect duplicate files, find dead links, and audit tags.',
                icon: Icons.medical_services_rounded,
                badge: 'HEALTH',
                badgeColor: Colors.tealAccent,
                onTap: () => showDialog(context: context, builder: (_) => const LibraryDoctorDialog()),
              ),
              _StudioCard(
                title: 'Sonance Wrapped & Habits',
                description: 'Detailed listening statistics, most played artists, total playtime, and formats.',
                icon: Icons.insights_rounded,
                badge: 'WRAPPED',
                badgeColor: Colors.purpleAccent,
                onTap: () => showDialog(context: context, builder: (_) => const ListeningStatsDialog()),
              ),
            ]),
          ],
        ),
      ),
    );
  }

  void _showZenithNotice(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Zenith Grand Mastering Suite'),
        content: const Text(
          'Zenith can be executed directly for any track or album folder via Sonance CLI:\n\n'
          '  python sonance.py --zenith <audio_file> --profile audiophile_pure_master\n\n'
          'Profiles: audiophile_pure_master, club_edm_banger, broadcast_radio_sheen, vinyl_cutting_prep.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Close')),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(BuildContext context, String title, IconData icon) {
    return Row(
      children: [
        Icon(icon, size: 18, color: SonanceTheme.emerald),
        const SizedBox(width: 8),
        Text(
          title,
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
      ],
    );
  }

  Widget _buildGrid(BuildContext context, List<Widget> children) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final crossAxisCount = constraints.maxWidth > 900 ? 3 : constraints.maxWidth > 600 ? 2 : 1;
        return GridView.count(
          crossAxisCount: crossAxisCount,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisSpacing: 16,
          mainAxisSpacing: 16,
          childAspectRatio: 1.6,
          children: children,
        );
      },
    );
  }
}

class _StudioCard extends StatelessWidget {
  final String title;
  final String description;
  final IconData icon;
  final String badge;
  final Color badgeColor;
  final VoidCallback onTap;

  const _StudioCard({
    required this.title,
    required this.description,
    required this.icon,
    required this.badge,
    required this.badgeColor,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: SonanceTheme.emerald.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Icon(icon, color: SonanceTheme.emerald, size: 22),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: badgeColor.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(color: badgeColor.withOpacity(0.4)),
                    ),
                    child: Text(
                      badge,
                      style: TextStyle(
                        fontSize: 9,
                        fontWeight: FontWeight.bold,
                        color: badgeColor,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    description,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 11,
                      color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                      height: 1.3,
                    ),
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
