import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../features/player/player_provider.dart';
import '../widgets/track_artwork.dart';

class MiniPlayerDialog extends ConsumerWidget {
  const MiniPlayerDialog({super.key});

  String _formatDuration(Duration d) {
    final minutes = d.inMinutes;
    final seconds = (d.inSeconds % 60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final player = ref.watch(playerProvider);
    final track = player.currentTrack;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    if (track == null) {
      return Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: const Padding(
          padding: EdgeInsets.all(24),
          child: Text('No track currently playing'),
        ),
      );
    }

    return Dialog(
      backgroundColor: isDark ? SonanceTheme.darkCard : SonanceTheme.lightCard,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: Theme.of(context).colorScheme.outline),
      ),
      insetPadding: const EdgeInsets.all(16),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 380),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Top Bar
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 8,
                        height: 8,
                        decoration: const BoxDecoration(
                          color: SonanceTheme.emerald,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 8),
                      const Text(
                        'SONANCE MINI',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 1.2,
                          color: SonanceTheme.emerald,
                        ),
                      ),
                    ],
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, size: 18),
                    onPressed: () => Navigator.of(context).pop(),
                    tooltip: 'Close Mini Player',
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // Album Art
              SonanceArtwork(
                coverUrl: track.coverUrl,
                width: 180,
                height: 180,
                borderRadius: 12,
                fallbackIcon: Icons.album_rounded,
              ),
              const SizedBox(height: 16),

              // Track details
              Text(
                track.title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.center,
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
              const SizedBox(height: 4),
              Text(
                track.artist,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 12,
                  color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                ),
              ),
              const SizedBox(height: 12),

              // Scrubber
              Column(
                children: [
                  SliderTheme(
                    data: SliderTheme.of(context).copyWith(
                      trackHeight: 3,
                      thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 6),
                      activeTrackColor: SonanceTheme.emerald,
                      inactiveTrackColor: SonanceTheme.emerald.withOpacity(0.2),
                      thumbColor: SonanceTheme.emerald,
                    ),
                    child: Slider(
                      value: player.duration.inMilliseconds > 0
                          ? player.position.inMilliseconds
                              .clamp(0, player.duration.inMilliseconds)
                              .toDouble()
                          : 0.0,
                      min: 0.0,
                      max: player.duration.inMilliseconds > 0
                          ? player.duration.inMilliseconds.toDouble()
                          : 1.0,
                      onChanged: (val) {
                        ref
                            .read(playerProvider.notifier)
                            .seek(Duration(milliseconds: val.toInt()));
                      },
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          _formatDuration(player.position),
                          style: const TextStyle(fontSize: 10, fontFamily: 'monospace'),
                        ),
                        Text(
                          _formatDuration(player.duration),
                          style: const TextStyle(fontSize: 10, fontFamily: 'monospace'),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),

              // Playback controls
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  IconButton(
                    icon: Icon(
                      player.isShuffle ? Icons.shuffle_on_outlined : Icons.shuffle,
                      size: 20,
                      color: player.isShuffle ? SonanceTheme.emerald : Colors.grey,
                    ),
                    onPressed: () =>
                        ref.read(playerProvider.notifier).toggleShuffle(),
                  ),
                  IconButton(
                    icon: const Icon(Icons.skip_previous_rounded, size: 28),
                    onPressed: () =>
                        ref.read(playerProvider.notifier).previous(),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    width: 48,
                    height: 48,
                    decoration: const BoxDecoration(
                      color: SonanceTheme.emerald,
                      shape: BoxShape.circle,
                    ),
                    child: IconButton(
                      icon: Icon(
                        player.isPlaying ? Icons.pause_rounded : Icons.play_arrow_rounded,
                        color: Colors.white,
                        size: 28,
                      ),
                      onPressed: () =>
                          ref.read(playerProvider.notifier).togglePlayPause(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    icon: const Icon(Icons.skip_next_rounded, size: 28),
                    onPressed: () => ref.read(playerProvider.notifier).next(),
                  ),
                  IconButton(
                    icon: Icon(
                      player.loopMode.name == 'one'
                          ? Icons.repeat_one_rounded
                          : player.loopMode.name == 'all'
                              ? Icons.repeat_on_rounded
                              : Icons.repeat_rounded,
                      size: 20,
                      color: player.loopMode.name != 'off'
                          ? SonanceTheme.emerald
                          : Colors.grey,
                    ),
                    onPressed: () =>
                        ref.read(playerProvider.notifier).cycleLoopMode(),
                  ),
                ],
              ),
              const SizedBox(height: 8),

              // Volume Slider
              Row(
                children: [
                  IconButton(
                    icon: Icon(
                      player.isMuted || player.volume == 0
                          ? Icons.volume_off_rounded
                          : player.volume < 0.5
                              ? Icons.volume_down_rounded
                              : Icons.volume_up_rounded,
                      size: 18,
                      color: Colors.grey,
                    ),
                    onPressed: () =>
                        ref.read(playerProvider.notifier).toggleMute(),
                  ),
                  Expanded(
                    child: SliderTheme(
                      data: SliderTheme.of(context).copyWith(
                        trackHeight: 2,
                        thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 4),
                        activeTrackColor: SonanceTheme.emerald,
                        inactiveTrackColor: Colors.grey.withOpacity(0.3),
                        thumbColor: SonanceTheme.emerald,
                      ),
                      child: Slider(
                        value: player.volume,
                        min: 0.0,
                        max: 1.0,
                        onChanged: (v) =>
                            ref.read(playerProvider.notifier).setVolume(v),
                      ),
                    ),
                  ),
                  Text(
                    '${(player.volume * 100).toInt()}%',
                    style: const TextStyle(fontSize: 10, fontFamily: 'monospace'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPlaceholder(BuildContext context) {
    return Container(
      width: 180,
      height: 180,
      color: Theme.of(context).colorScheme.surface,
      child: Icon(
        Icons.music_note_rounded,
        size: 64,
        color: SonanceTheme.emerald.withOpacity(0.5),
      ),
    );
  }
}
