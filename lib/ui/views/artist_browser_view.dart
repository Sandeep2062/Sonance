import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/models/track.dart';
import '../../core/theme/app_theme.dart';
import '../../features/player/player_provider.dart';

class ArtistBrowserView extends ConsumerStatefulWidget {
  final List<SonanceTrack> tracks;

  const ArtistBrowserView({super.key, required this.tracks});

  @override
  ConsumerState<ArtistBrowserView> createState() => _ArtistBrowserViewState();
}

class _ArtistBrowserViewState extends ConsumerState<ArtistBrowserView> {
  String? _selectedArtist;
  String _filterQuery = '';

  @override
  Widget build(BuildContext context) {
    // Group tracks by artist
    final artistMap = <String, List<SonanceTrack>>{};
    for (final track in widget.tracks) {
      final a = track.artist.trim().isEmpty ? 'Unknown Artist' : track.artist.trim();
      artistMap.putIfAbsent(a, () => []).add(track);
    }

    final artists = artistMap.keys.toList()..sort((a, b) => a.toLowerCase().compareTo(b.toLowerCase()));
    final filteredArtists = _filterQuery.isEmpty
        ? artists
        : artists.where((a) => a.toLowerCase().contains(_filterQuery.toLowerCase())).toList();

    if (_selectedArtist != null && artistMap.containsKey(_selectedArtist)) {
      return _buildArtistDetail(context, _selectedArtist!, artistMap[_selectedArtist!]!);
    }

    return Column(
      children: [
        // Search & Filter
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: TextField(
            decoration: InputDecoration(
              hintText: 'Filter ${artists.length} artists...',
              prefixIcon: const Icon(Icons.search, size: 20),
              isDense: true,
              contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
            ),
            onChanged: (v) => setState(() => _filterQuery = v),
          ),
        ),
        Expanded(
          child: filteredArtists.isEmpty
              ? const Center(
                  child: Text('No artists found', style: TextStyle(color: Colors.grey)),
                )
              : GridView.builder(
                  padding: const EdgeInsets.all(16),
                  gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                    maxCrossAxisExtent: 220,
                    childAspectRatio: 0.85,
                    crossAxisSpacing: 16,
                    mainAxisSpacing: 16,
                  ),
                  itemCount: filteredArtists.length,
                  itemBuilder: (context, idx) {
                    final artistName = filteredArtists[idx];
                    final artistTracks = artistMap[artistName] ?? [];
                    final albums = artistTracks.map((t) => t.album).toSet().length;

                    return Card(
                      clipBehavior: Clip.antiAlias,
                      child: InkWell(
                        onTap: () => setState(() => _selectedArtist = artistName),
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              CircleAvatar(
                                radius: 44,
                                backgroundColor: SonanceTheme.emerald.withOpacity(0.15),
                                child: Text(
                                  artistName.isNotEmpty ? artistName[0].toUpperCase() : '?',
                                  style: const TextStyle(
                                    fontSize: 32,
                                    fontWeight: FontWeight.bold,
                                    color: SonanceTheme.emerald,
                                  ),
                                ),
                              ),
                              const SizedBox(height: 12),
                              Text(
                                artistName,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                textAlign: TextAlign.center,
                                style: const TextStyle(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 14,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                '${artistTracks.length} tracks · $albums album${albums > 1 ? 's' : ''}',
                                style: TextStyle(
                                  fontSize: 11,
                                  color: Theme.of(context)
                                      .colorScheme
                                      .onSurface
                                      .withOpacity(0.55),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }

  Widget _buildArtistDetail(BuildContext context, String artistName, List<SonanceTrack> tracks) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Top Navigation Bar
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            border: Border(bottom: BorderSide(color: Theme.of(context).colorScheme.outline)),
          ),
          child: Row(
            children: [
              IconButton(
                icon: const Icon(Icons.arrow_back),
                onPressed: () => setState(() => _selectedArtist = null),
                tooltip: 'Back to Artists',
              ),
              const SizedBox(width: 8),
              CircleAvatar(
                radius: 20,
                backgroundColor: SonanceTheme.emerald.withOpacity(0.15),
                child: Text(
                  artistName.isNotEmpty ? artistName[0].toUpperCase() : '?',
                  style: const TextStyle(color: SonanceTheme.emerald, fontWeight: FontWeight.bold),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      artistName,
                      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                    Text(
                      '${tracks.length} tracks in local library',
                      style: TextStyle(
                        fontSize: 12,
                        color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                      ),
                    ),
                  ],
                ),
              ),
              ElevatedButton.icon(
                icon: const Icon(Icons.play_arrow_rounded),
                label: const Text('Play All'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: SonanceTheme.emerald,
                  foregroundColor: Colors.white,
                ),
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
        // Tracks List
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: tracks.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, idx) {
              final track = tracks[idx];
              return ListTile(
                leading: CircleAvatar(
                  radius: 16,
                  backgroundColor: Theme.of(context).colorScheme.surface,
                  child: Text(
                    '${idx + 1}',
                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                  ),
                ),
                title: Text(track.title, style: const TextStyle(fontWeight: FontWeight.w600)),
                subtitle: Text('${track.album} · ${track.qualityBadge}'),
                trailing: IconButton(
                  icon: const Icon(Icons.play_circle_outline, size: 28),
                  color: SonanceTheme.emerald,
                  onPressed: () {
                    ref.read(playerProvider.notifier).playQueue(tracks, startIndex: idx);
                  },
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}
