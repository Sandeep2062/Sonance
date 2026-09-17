import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/theme/app_theme.dart';
import '../features/player/player_provider.dart';
import 'views/local_view.dart';
import 'views/lyrics_view.dart';
import 'views/queue_view.dart';
import 'views/search_view.dart';
import 'views/settings_view.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  int _selectedIndex = 1; // Default to Search & Stream

  final _views = const [
    LocalView(),
    SearchView(),
    QueueView(),
    LyricsView(),
    SettingsView(),
  ];

  @override
  Widget build(BuildContext context) {
    final player = ref.watch(playerProvider);

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
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(colors: [SonanceTheme.emerald, Color(0xFF0D9488)]),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Center(child: Text('🎵', style: TextStyle(fontSize: 20))),
              ),
            ),
            labelType: NavigationRailLabelType.all,
            destinations: const [
              NavigationRailDestination(icon: Icon(Icons.folder_outlined), selectedIcon: Icon(Icons.folder), label: Text('Local')),
              NavigationRailDestination(icon: Icon(Icons.search_outlined), selectedIcon: Icon(Icons.search), label: Text('Search')),
              NavigationRailDestination(icon: Icon(Icons.downloading_outlined), selectedIcon: Icon(Icons.downloading), label: Text('Queue')),
              NavigationRailDestination(icon: Icon(Icons.lyrics_outlined), selectedIcon: Icon(Icons.lyrics), label: Text('Lyrics')),
              NavigationRailDestination(icon: Icon(Icons.settings_outlined), selectedIcon: Icon(Icons.settings), label: Text('Settings')),
            ],
          ),
          const VerticalDivider(thickness: 1, width: 1, color: SonanceTheme.borderColor),

          // Main View
          Expanded(
            child: Column(
              children: [
                Expanded(child: _views[_selectedIndex]),

                // Persistent Bottom Player
                if (player.currentTrack != null)
                  Container(
                    height: 72,
                    decoration: const BoxDecoration(
                      color: SonanceTheme.surfaceColor,
                      border: Border(top: BorderSide(color: SonanceTheme.borderColor)),
                    ),
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    child: Row(
                      children: [
                        ClipRRect(
                          borderRadius: BorderRadius.circular(6),
                          child: player.currentTrack!.coverUrl != null
                              ? Image.network(player.currentTrack!.coverUrl!, width: 48, height: 48, fit: BoxFit.cover, errorBuilder: (_, __, ___) => Container(width: 48, height: 48, color: Colors.black))
                              : Container(width: 48, height: 48, color: Colors.black, child: const Icon(Icons.music_note)),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(player.currentTrack!.title, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                              Text(player.currentTrack!.artist, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Colors.grey, fontSize: 11)),
                            ],
                          ),
                        ),
                        IconButton(
                          icon: Icon(player.isPlaying ? Icons.pause_circle_filled : Icons.play_circle_fill, size: 38, color: SonanceTheme.emerald),
                          onPressed: () => ref.read(playerProvider.notifier).togglePlayPause(),
                        ),
                        const SizedBox(width: 12),
                        IconButton(
                          icon: const Icon(Icons.lyrics, color: SonanceTheme.emerald),
                          onPressed: () => setState(() => _selectedIndex = 3),
                          tooltip: 'Open Live Karaoke Lyrics',
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
}
