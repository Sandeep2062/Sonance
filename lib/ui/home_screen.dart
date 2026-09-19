import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/theme/app_theme.dart';
import '../features/player/player_provider.dart';
import '../features/playlists/playlist_provider.dart';
import 'views/local_view.dart';
import 'views/lyrics_view.dart';
import 'views/queue_view.dart';
import 'views/search_view.dart';
import 'views/settings_view.dart';
import 'views/equalizer_view.dart';
import 'views/mini_player_view.dart';
import 'views/studios/studios_view.dart';
import 'widgets/track_artwork.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  int _selectedIndex = 1; // Default to Search & Stream
  double? _draggedPositionMs;

  final _views = const [
    LocalView(),
    SearchView(),
    QueueView(),
    LyricsView(),
    StudiosView(),
    SettingsView(),
  ];

  String _formatDuration(Duration d) {
    final minutes = d.inMinutes;
    final seconds = (d.inSeconds % 60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }

  @override
  Widget build(BuildContext context) {
    final player = ref.watch(playerProvider);
    final playlist = ref.watch(playlistProvider);
    final track = player.currentTrack;
    final isFav = track != null && playlist.favorites.any((t) => t.id == track.id);

    return Scaffold(
      body: Row(
        children: [
          // Navigation Rail
          NavigationRail(
            selectedIndex: _selectedIndex,
            onDestinationSelected: (idx) => setState(() => _selectedIndex = idx),
            leading: Padding(
              padding: const EdgeInsets.symmetric(vertical: 16),
              child: Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.primary,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Center(
                  child: Icon(Icons.graphic_eq_rounded, color: Colors.white, size: 22),
                ),
              ),
            ),
            labelType: NavigationRailLabelType.all,
            destinations: const [
              NavigationRailDestination(
                icon: Icon(Icons.folder_outlined),
                selectedIcon: Icon(Icons.folder),
                label: Text('Local'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.search_outlined),
                selectedIcon: Icon(Icons.search),
                label: Text('Search'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.downloading_outlined),
                selectedIcon: Icon(Icons.downloading),
                label: Text('Queue'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.lyrics_outlined),
                selectedIcon: Icon(Icons.lyrics),
                label: Text('Lyrics'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.auto_awesome_outlined),
                selectedIcon: Icon(Icons.auto_awesome),
                label: Text('Studios'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.settings_outlined),
                selectedIcon: Icon(Icons.settings),
                label: Text('Settings'),
              ),
            ],
          ),
          VerticalDivider(
            thickness: 1,
            width: 1,
            color: Theme.of(context).dividerTheme.color ?? Theme.of(context).dividerColor,
          ),

          // Main View
          Expanded(
            child: Column(
              children: [
                Expanded(child: _views[_selectedIndex]),

                // Upgraded Persistent Bottom Player Bar
                if (track != null)
                  Container(
                    height: 88,
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.surface,
                      border: Border(
                        top: BorderSide(
                          color: Theme.of(context).dividerTheme.color ?? Theme.of(context).dividerColor,
                        ),
                      ),
                    ),
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    child: Row(
                      children: [
                        // Left: Track Info & Artwork
                        SizedBox(
                          width: 240,
                          child: Row(
                            children: [
                              SonanceArtwork(
                                coverUrl: track.coverUrl,
                                width: 52,
                                height: 52,
                                borderRadius: 8,
                                fallbackIcon: Icons.music_note,
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      track.title,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(
                                        fontWeight: FontWeight.bold,
                                        fontSize: 13,
                                        color: Theme.of(context).colorScheme.onSurface,
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Row(
                                      children: [
                                        Flexible(
                                          child: Text(
                                            track.artist,
                                            maxLines: 1,
                                            overflow: TextOverflow.ellipsis,
                                            style: TextStyle(
                                              color: Theme.of(context)
                                                  .colorScheme
                                                  .onSurface
                                                  .withOpacity(0.6),
                                              fontSize: 11,
                                            ),
                                          ),
                                        ),
                                        const SizedBox(width: 6),
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                                          decoration: BoxDecoration(
                                            color: track.isLossless
                                                ? SonanceTheme.emerald.withOpacity(0.2)
                                                : Theme.of(context).colorScheme.outlineVariant.withOpacity(0.3),
                                            borderRadius: BorderRadius.circular(3),
                                          ),
                                          child: Text(
                                            track.qualityBadge,
                                            style: TextStyle(
                                              fontSize: 9,
                                              fontWeight: FontWeight.bold,
                                              color: track.isLossless ? SonanceTheme.emerald : null,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                              IconButton(
                                icon: Icon(
                                  isFav ? Icons.favorite : Icons.favorite_border,
                                  size: 20,
                                  color: isFav ? Colors.redAccent : Colors.grey,
                                ),
                                onPressed: () {
                                  ref.read(playlistProvider.notifier).toggleFavorite(track);
                                },
                                tooltip: isFav ? 'Remove from Favorites' : 'Add to Favorites',
                              ),
                            ],
                          ),
                        ),

                        const SizedBox(width: 16),

                        // Center: Controls & Seek Bar
                        Expanded(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              // Controls
                              Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  IconButton(
                                    icon: Icon(
                                      player.isShuffle ? Icons.shuffle_on_outlined : Icons.shuffle,
                                      size: 18,
                                      color: player.isShuffle ? SonanceTheme.emerald : Colors.grey,
                                    ),
                                    onPressed: () => ref.read(playerProvider.notifier).toggleShuffle(),
                                    tooltip: 'Shuffle',
                                  ),
                                  IconButton(
                                    icon: const Icon(Icons.skip_previous_rounded, size: 24),
                                    onPressed: () => ref.read(playerProvider.notifier).previous(),
                                    tooltip: 'Previous',
                                  ),
                                  const SizedBox(width: 6),
                                  Container(
                                    width: 36,
                                    height: 36,
                                    decoration: BoxDecoration(
                                      color: SonanceTheme.emerald,
                                      shape: BoxShape.circle,
                                    ),
                                    child: IconButton(
                                      padding: EdgeInsets.zero,
                                      icon: Icon(
                                        player.isPlaying ? Icons.pause_rounded : Icons.play_arrow_rounded,
                                        color: Colors.white,
                                        size: 24,
                                      ),
                                      onPressed: () => ref.read(playerProvider.notifier).togglePlayPause(),
                                      tooltip: player.isPlaying ? 'Pause' : 'Play',
                                    ),
                                  ),
                                  const SizedBox(width: 6),
                                  IconButton(
                                    icon: const Icon(Icons.skip_next_rounded, size: 24),
                                    onPressed: () => ref.read(playerProvider.notifier).next(),
                                    tooltip: 'Next',
                                  ),
                                  IconButton(
                                    icon: Icon(
                                      player.loopMode.name == 'one'
                                          ? Icons.repeat_one_rounded
                                          : player.loopMode.name == 'all'
                                              ? Icons.repeat_on_rounded
                                              : Icons.repeat_rounded,
                                      size: 18,
                                      color: player.loopMode.name != 'off' ? SonanceTheme.emerald : Colors.grey,
                                    ),
                                    onPressed: () => ref.read(playerProvider.notifier).cycleLoopMode(),
                                    tooltip: 'Repeat: ${player.loopMode.name.toUpperCase()}',
                                  ),
                                ],
                              ),

                              // Scrubber Row
                              Row(
                                children: [
                                  Text(
                                    _formatDuration(
                                      _draggedPositionMs != null
                                          ? Duration(milliseconds: _draggedPositionMs!.toInt())
                                          : player.position,
                                    ),
                                    style: const TextStyle(fontSize: 10, fontFamily: 'monospace'),
                                  ),
                                  Expanded(
                                    child: SliderTheme(
                                      data: SliderTheme.of(context).copyWith(
                                        trackHeight: 3,
                                        thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 5),
                                        activeTrackColor: SonanceTheme.emerald,
                                        inactiveTrackColor: Theme.of(context).colorScheme.outlineVariant.withOpacity(0.4),
                                        thumbColor: SonanceTheme.emerald,
                                        overlayShape: const RoundSliderOverlayShape(overlayRadius: 10),
                                      ),
                                      child: Slider(
                                        value: _draggedPositionMs ??
                                            (player.duration.inMilliseconds > 0
                                                ? player.position.inMilliseconds
                                                    .clamp(0, player.duration.inMilliseconds)
                                                    .toDouble()
                                                : 0.0),
                                        min: 0.0,
                                        max: player.duration.inMilliseconds > 0
                                            ? player.duration.inMilliseconds.toDouble()
                                            : 1.0,
                                        onChanged: (val) {
                                          setState(() => _draggedPositionMs = val);
                                        },
                                        onChangeEnd: (val) {
                                          ref
                                              .read(playerProvider.notifier)
                                              .seek(Duration(milliseconds: val.toInt()));
                                          setState(() => _draggedPositionMs = null);
                                        },
                                      ),
                                    ),
                                  ),
                                  Text(
                                    _formatDuration(player.duration),
                                    style: const TextStyle(fontSize: 10, fontFamily: 'monospace'),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),

                        const SizedBox(width: 16),

                        // Right: Volume & Utilities
                        SizedBox(
                          width: 260,
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.end,
                            children: [
                              // Volume Slider
                              IconButton(
                                icon: Icon(
                                  player.isMuted || player.volume == 0
                                      ? Icons.volume_off_rounded
                                      : player.volume < 0.5
                                          ? Icons.volume_down_rounded
                                          : Icons.volume_up_rounded,
                                  size: 20,
                                  color: Colors.grey,
                                ),
                                onPressed: () => ref.read(playerProvider.notifier).toggleMute(),
                                tooltip: player.isMuted ? 'Unmute' : 'Mute',
                              ),
                              SizedBox(
                                width: 80,
                                child: SliderTheme(
                                  data: SliderTheme.of(context).copyWith(
                                    trackHeight: 2,
                                    thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 4),
                                    activeTrackColor: SonanceTheme.emerald,
                                    inactiveTrackColor: Theme.of(context).colorScheme.outlineVariant.withOpacity(0.4),
                                    thumbColor: SonanceTheme.emerald,
                                  ),
                                  child: Slider(
                                    value: player.volume,
                                    min: 0.0,
                                    max: 1.0,
                                    onChanged: (v) => ref.read(playerProvider.notifier).setVolume(v),
                                  ),
                                ),
                              ),

                              const SizedBox(width: 4),

                              // Equalizer Dialog Button
                              IconButton(
                                icon: const Icon(Icons.tune_rounded, size: 20),
                                color: SonanceTheme.emerald,
                                onPressed: () {
                                  showDialog(
                                    context: context,
                                    builder: (_) => const EqualizerDialog(),
                                  );
                                },
                                tooltip: '10-Band Equalizer DSP',
                              ),

                              // Karaoke Lyrics View Button
                              IconButton(
                                icon: const Icon(Icons.lyrics_outlined, size: 20),
                                color: SonanceTheme.emerald,
                                onPressed: () => setState(() => _selectedIndex = 3),
                                tooltip: 'Open Karaoke Lyrics',
                              ),

                              // Mini-Player Button
                              IconButton(
                                icon: const Icon(Icons.picture_in_picture_alt_rounded, size: 20),
                                color: Colors.grey,
                                onPressed: () {
                                  showDialog(
                                    context: context,
                                    builder: (_) => const MiniPlayerDialog(),
                                  );
                                },
                                tooltip: 'Floating Mini Player',
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPlaceholder() {
    return Container(
      width: 52,
      height: 52,
      color: Theme.of(context).colorScheme.outlineVariant.withOpacity(0.3),
      child: Icon(
        Icons.music_note,
        color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
      ),
    );
  }
}
