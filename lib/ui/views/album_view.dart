import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/models/track.dart';
import '../../core/theme/app_theme.dart';
import '../../features/player/player_provider.dart';

class AlbumBrowserView extends ConsumerStatefulWidget {
  final List<SonanceTrack> tracks;

  const AlbumBrowserView({super.key, required this.tracks});

  @override
  ConsumerState<AlbumBrowserView> createState() => _AlbumBrowserViewState();
}

class _AlbumBrowserViewState extends ConsumerState<AlbumBrowserView> {
  String? _selectedAlbum;
  String _filterQuery = '';

  @override
  Widget build(BuildContext context) {
    final albumMap = <String, List<SonanceTrack>>{};
    for (final track in widget.tracks) {
      final a = track.album.trim().isEmpty ? 'Unknown Album' : track.album.trim();
      albumMap.putIfAbsent(a, () => []).add(track);
    }

    final albums = albumMap.keys.toList()..sort((a, b) => a.toLowerCase().compareTo(b.toLowerCase()));
    final filteredAlbums = _filterQuery.isEmpty
        ? albums
        : albums.where((a) => a.toLowerCase().contains(_filterQuery.toLowerCase())).toList();

    if (_selectedAlbum != null && albumMap.containsKey(_selectedAlbum)) {
      return _buildAlbumDetail(context, _selectedAlbum!, albumMap[_selectedAlbum!]!);
    }

    return Column(
      children: [
        // Filter input
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: TextField(
            decoration: InputDecoration(
              hintText: 'Filter ${albums.length} albums...',
              prefixIcon: const Icon(Icons.album_outlined, size: 20),
              isDense: true,
              contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
            ),
            onChanged: (v) => setState(() => _filterQuery = v),
          ),
        ),
        Expanded(
          child: filteredAlbums.isEmpty
              ? const Center(
                  child: Text('No albums found', style: TextStyle(color: Colors.grey)),
                )
              : GridView.builder(
                  padding: const EdgeInsets.all(16),
                  gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                    maxCrossAxisExtent: 200,
                    childAspectRatio: 0.8,
                    crossAxisSpacing: 16,
                    mainAxisSpacing: 16,
                  ),
                  itemCount: filteredAlbums.length,
                  itemBuilder: (context, idx) {
                    final albumName = filteredAlbums[idx];
                    final albumTracks = albumMap[albumName] ?? [];
                    final artist = albumTracks.isNotEmpty ? albumTracks.first.artist : 'Various Artists';
                    final hasFlac = albumTracks.any((t) => t.isLossless);

                    return Card(
                      clipBehavior: Clip.antiAlias,
                      child: InkWell(
                        onTap: () => setState(() => _selectedAlbum = albumName),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            AspectRatio(
                              aspectRatio: 1.0,
                              child: Container(
                                color: Theme.of(context).colorScheme.surface,
                                child: Stack(
                                  children: [
                                    Center(
                                      child: Icon(
                                        Icons.album_rounded,
                                        size: 64,
                                        color: SonanceTheme.emerald.withOpacity(0.5),
                                      ),
                                    ),
                                    if (hasFlac)
                                      Positioned(
                                        top: 8,
                                        right: 8,
                                        child: Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                          decoration: BoxDecoration(
                                            color: SonanceTheme.emerald,
                                            borderRadius: BorderRadius.circular(4),
                                          ),
                                          child: const Text(
                                            'FLAC',
                                            style: TextStyle(
                                              fontSize: 9,
                                              fontWeight: FontWeight.bold,
                                              color: Colors.white,
                                            ),
                                          ),
                                        ),
                                      ),
                                  ],
                                ),
                              ),
                            ),
                            Padding(
                              padding: const EdgeInsets.all(10),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    albumName,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    artist,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(
                                      fontSize: 11,
                                      color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    '${albumTracks.length} tracks',
                                    style: TextStyle(
                                      fontSize: 10,
                                      color: Theme.of(context).colorScheme.onSurface.withOpacity(0.4),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }

  Widget _buildAlbumDetail(BuildContext context, String albumName, List<SonanceTrack> tracks) {
    final artist = tracks.isNotEmpty ? tracks.first.artist : 'Various Artists';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Top Navigation
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            border: Border(bottom: BorderSide(color: Theme.of(context).colorScheme.outline)),
          ),
          child: Row(
            children: [
              IconButton(
                icon: const Icon(Icons.arrow_back),
                onPressed: () => setState(() => _selectedAlbum = null),
                tooltip: 'Back to Albums',
              ),
              const SizedBox(width: 8),
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surface,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: Theme.of(context).colorScheme.outline),
                ),
                child: const Icon(Icons.album, color: SonanceTheme.emerald),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(albumName, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    Text('$artist · ${tracks.length} tracks',
                        style: TextStyle(fontSize: 12, color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6))),
                  ],
                ),
              ),
              ElevatedButton.icon(
                icon: const Icon(Icons.play_arrow_rounded),
                label: const Text('Play Album'),
                style: ElevatedButton.styleFrom(backgroundColor: SonanceTheme.emerald, foregroundColor: Colors.white),
                onPressed: () {
                  ref.read(playerProvider.notifier).playQueue(tracks, startIndex: 0);
                },
              ),
              const SizedBox(width: 8),
              OutlinedButton.icon(
                icon: const Icon(Icons.shuffle, size: 18),
                label: const Text('Shuffle'),
                onPressed: () {
                  final shuffled = List<SonanceTrack>.from(tracks)..shuffle();
                  ref.read(playerProvider.notifier).playQueue(shuffled, startIndex: 0);
                },
              ),
            ],
          ),
        ),
        // Album Tracks
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: tracks.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, idx) {
              final track = tracks[idx];
              return ListTile(
                leading: Text(
                  '${idx + 1}',
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Colors.grey),
                ),
                title: Text(track.title, style: const TextStyle(fontWeight: FontWeight.w600)),
                subtitle: Text(track.artist),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: track.isLossless
                            ? SonanceTheme.emerald.withOpacity(0.2)
                            : Theme.of(context).colorScheme.surface,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        track.qualityBadge,
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                          color: track.isLossless ? SonanceTheme.emerald : null,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    IconButton(
                      icon: const Icon(Icons.play_circle_outline, size: 26),
                      color: SonanceTheme.emerald,
                      onPressed: () {
                        ref.read(playerProvider.notifier).playQueue(tracks, startIndex: idx);
                      },
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}
