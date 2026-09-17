import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../core/services/spotify_importer.dart';
import '../../features/downloader/download_queue_provider.dart';
import '../../features/player/player_provider.dart';
import '../../features/search/search_provider.dart';

class SearchView extends ConsumerStatefulWidget {
  const SearchView({super.key});

  @override
  ConsumerState<SearchView> createState() => _SearchViewState();
}

class _SearchViewState extends ConsumerState<SearchView> {
  final _searchCtrl = TextEditingController();

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  void _showSpotifyImportDialog() {
    final urlCtrl = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Import Spotify Playlist or Album'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Paste any public Spotify link (playlist, album, track) to resolve all tracks and download with synced lyrics:',
              style: TextStyle(fontSize: 12, color: Colors.grey),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: urlCtrl,
              decoration: const InputDecoration(
                hintText: 'https://open.spotify.com/playlist/...',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: SonanceTheme.emerald),
            onPressed: () async {
              final url = urlCtrl.text.trim();
              Navigator.pop(ctx);
              if (url.isEmpty) return;

              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Resolving Spotify collection...')),
              );

              final result = await SpotifyImporter.resolveSpotifyUrl(url);
              if (!mounted) return;

              if (result != null && result.tracks.isNotEmpty) {
                for (final track in result.tracks) {
                  ref.read(downloadQueueProvider.notifier).addTask(track);
                }
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('Enqueued ${result.tracks.length} tracks from "${result.title}" with synced lyrics!')),
                );
              } else {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Could not resolve tracks from that Spotify link.')),
                );
              }
            },
            child: const Text('Import & Download All', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final search = ref.watch(searchProvider);

    return Scaffold(
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _searchCtrl,
                    decoration: InputDecoration(
                      hintText: 'Search songs, artists, albums (Deezer, YouTube)...',
                      prefixIcon: const Icon(Icons.search),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      filled: true,
                      fillColor: SonanceTheme.surfaceColor,
                    ),
                    onSubmitted: (q) => ref.read(searchProvider.notifier).search(q),
                  ),
                ),
                const SizedBox(width: 12),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: SonanceTheme.emerald,
                    padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 18),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  onPressed: () => ref.read(searchProvider.notifier).search(_searchCtrl.text),
                  child: const Text('Search', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                TextButton.icon(
                  icon: const Icon(Icons.link, size: 16, color: SonanceTheme.emerald),
                  label: const Text('Paste Spotify Playlist / Album Link', style: TextStyle(color: SonanceTheme.emerald, fontSize: 12)),
                  onPressed: _showSpotifyImportDialog,
                ),
              ],
            ),
            const SizedBox(height: 8),

            if (search.isLoading)
              const Expanded(child: Center(child: CircularProgressIndicator(color: SonanceTheme.emerald)))
            else if (search.results.isEmpty)
              const Expanded(
                child: Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.library_music_outlined, size: 64, color: Colors.grey),
                      SizedBox(height: 12),
                      Text('Search millions of tracks with instant playback & lyrics sync.', style: TextStyle(color: Colors.grey)),
                    ],
                  ),
                ),
              )
            else
              Expanded(
                child: GridView.builder(
                  gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                    maxCrossAxisExtent: 340,
                    mainAxisExtent: 100,
                    crossAxisSpacing: 12,
                    mainAxisSpacing: 12,
                  ),
                  itemCount: search.results.length,
                  itemBuilder: (context, idx) {
                    final track = search.results[idx];
                    return Card(
                      child: Padding(
                        padding: const EdgeInsets.all(10),
                        child: Row(
                          children: [
                            ClipRRect(
                              borderRadius: BorderRadius.circular(8),
                              child: track.coverUrl != null
                                  ? Image.network(track.coverUrl!, width: 64, height: 64, fit: BoxFit.cover, errorBuilder: (_, __, ___) => Container(width: 64, height: 64, color: Colors.black))
                                  : Container(width: 64, height: 64, color: Colors.black, child: const Icon(Icons.music_note)),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Text(track.title, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                                  Text('${track.artist} · ${track.album}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Colors.grey, fontSize: 11)),
                                  const SizedBox(height: 4),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                    decoration: BoxDecoration(color: Colors.white10, borderRadius: BorderRadius.circular(4)),
                                    child: Text(track.source, style: const TextStyle(fontSize: 9, fontWeight: FontWeight.bold)),
                                  ),
                                ],
                              ),
                            ),
                            Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                IconButton(
                                  icon: const Icon(Icons.play_arrow, color: SonanceTheme.emerald),
                                  onPressed: () => ref.read(playerProvider.notifier).playTrack(track),
                                  tooltip: 'Play Stream',
                                ),
                                IconButton(
                                  icon: const Icon(Icons.download_rounded, size: 18),
                                  onPressed: () {
                                    ref.read(downloadQueueProvider.notifier).addTask(track);
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(content: Text('Added "${track.title}" to download queue with lyrics sync!')),
                                    );
                                  },
                                  tooltip: 'Download + Synced Lyrics',
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
          ],
        ),
      ),
    );
  }
}
