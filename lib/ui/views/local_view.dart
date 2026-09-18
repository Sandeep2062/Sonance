import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path/path.dart' as p;
import '../../core/models/track.dart';
import '../../core/theme/app_theme.dart';
import '../../features/player/player_provider.dart';
import 'artist_browser_view.dart';
import 'album_view.dart';

class LocalView extends ConsumerStatefulWidget {
  const LocalView({super.key});

  @override
  ConsumerState<LocalView> createState() => _LocalViewState();
}

class _LocalViewState extends ConsumerState<LocalView>
    with SingleTickerProviderStateMixin {
  String? _selectedFolder;
  List<SonanceTrack> _localTracks = [];
  bool _isScanning = false;
  String _trackFilter = '';
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _pickFolder() async {
    final folder = await FilePicker.platform.getDirectoryPath();
    if (folder != null) {
      setState(() {
        _selectedFolder = folder;
        _isScanning = true;
      });

      final tracks = <SonanceTrack>[];
      final dir = Directory(folder);

      try {
        await for (final entity
            in dir.list(recursive: true, followLinks: false)) {
          if (entity is File) {
            final ext = p.extension(entity.path).toLowerCase();
            if (['.mp3', '.flac', '.m4a', '.ogg', '.wav'].contains(ext)) {
              final filename = p.basenameWithoutExtension(entity.path);
              final parts = filename.split(' - ');
              final artist =
                  parts.length > 1 ? parts[0].trim() : 'Unknown Artist';
              final title = parts.length > 1
                  ? parts.sublist(1).join(' - ').trim()
                  : filename;

              final lrcFile = File('${p.withoutExtension(entity.path)}.lrc');
              final hasLrc = await lrcFile.exists();

              tracks.add(SonanceTrack(
                id: entity.path,
                title: title,
                artist: artist,
                album: 'Local Library',
                duration: Duration.zero,
                localFilePath: entity.path,
                lyricsFilePath: hasLrc ? lrcFile.path : null,
                source: 'Local',
                qualityBadge: ext.replaceAll('.', '').toUpperCase(),
                isLossless: ext == '.flac',
              ));
            }
          }
        }
      } catch (_) {}

      setState(() {
        _localTracks = tracks;
        _isScanning = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final filteredTracks = _trackFilter.isEmpty
        ? _localTracks
        : _localTracks.where((t) {
            final q = _trackFilter.toLowerCase();
            return t.title.toLowerCase().contains(q) ||
                t.artist.toLowerCase().contains(q) ||
                t.album.toLowerCase().contains(q);
          }).toList();

    return Scaffold(
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Top Bar
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Local Music Library',
                        style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 2),
                    Text(_selectedFolder ?? 'No folder selected',
                        style: const TextStyle(fontSize: 12, color: Colors.grey)),
                  ],
                ),
                Row(
                  children: [
                    if (_localTracks.isNotEmpty) ...[
                      ElevatedButton.icon(
                        icon: const Icon(Icons.play_arrow_rounded),
                        label: const Text('Play All'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: SonanceTheme.emerald,
                          foregroundColor: Colors.white,
                        ),
                        onPressed: () {
                          ref
                              .read(playerProvider.notifier)
                              .playQueue(_localTracks, startIndex: 0);
                        },
                      ),
                      const SizedBox(width: 8),
                      OutlinedButton.icon(
                        icon: const Icon(Icons.shuffle, size: 18),
                        label: const Text('Shuffle'),
                        onPressed: () {
                          final shuffled = List<SonanceTrack>.from(_localTracks)
                            ..shuffle();
                          ref
                              .read(playerProvider.notifier)
                              .playQueue(shuffled, startIndex: 0);
                        },
                      ),
                      const SizedBox(width: 12),
                    ],
                    ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Theme.of(context).colorScheme.surface,
                        foregroundColor: Theme.of(context).colorScheme.onSurface,
                        side: BorderSide(
                            color: Theme.of(context).colorScheme.outline),
                      ),
                      icon: Icon(Icons.folder_open,
                          color: Theme.of(context).colorScheme.primary),
                      label: const Text('Select Music Folder'),
                      onPressed: _pickFolder,
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 16),

            if (_isScanning)
              Expanded(
                child: Center(
                  child: CircularProgressIndicator(
                      color: Theme.of(context).colorScheme.primary),
                ),
              )
            else if (_localTracks.isEmpty)
              Expanded(
                child: Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.folder_copy_outlined,
                          size: 64,
                          color: Theme.of(context)
                              .colorScheme
                              .onSurface
                              .withOpacity(0.4)),
                      const SizedBox(height: 12),
                      Text(
                        'Click "Select Music Folder" to browse your local audio library.',
                        style: TextStyle(
                            color: Theme.of(context)
                                .colorScheme
                                .onSurface
                                .withOpacity(0.6)),
                      ),
                    ],
                  ),
                ),
              )
            else ...[
              // Tabs Bar (Tracks, Artists, Albums)
              TabBar(
                controller: _tabController,
                isScrollable: true,
                indicatorColor: SonanceTheme.emerald,
                labelColor: SonanceTheme.emerald,
                unselectedLabelColor: Colors.grey,
                tabs: [
                  Tab(text: 'Tracks (${_localTracks.length})'),
                  Tab(
                      text:
                          'Artists (${_localTracks.map((t) => t.artist).toSet().length})'),
                  Tab(
                      text:
                          'Albums (${_localTracks.map((t) => t.album).toSet().length})'),
                ],
              ),
              const SizedBox(height: 12),

              // Tab Views
              Expanded(
                child: TabBarView(
                  controller: _tabController,
                  children: [
                    // Tracks Tab
                    Column(
                      children: [
                        Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: TextField(
                            decoration: InputDecoration(
                              hintText: 'Search in ${_localTracks.length} tracks...',
                              prefixIcon: const Icon(Icons.search, size: 20),
                              isDense: true,
                              contentPadding: const EdgeInsets.symmetric(
                                  horizontal: 14, vertical: 10),
                              border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(10)),
                            ),
                            onChanged: (v) =>
                                setState(() => _trackFilter = v),
                          ),
                        ),
                        Expanded(
                          child: ListView.separated(
                            itemCount: filteredTracks.length,
                            separatorBuilder: (_, __) =>
                                const SizedBox(height: 6),
                            itemBuilder: (context, idx) {
                              final track = filteredTracks[idx];
                              final hasLrc = track.lyricsFilePath != null;

                              return Card(
                                child: ListTile(
                                  leading: Container(
                                    width: 44,
                                    height: 44,
                                    decoration: BoxDecoration(
                                      color: Theme.of(context)
                                          .colorScheme
                                          .outlineVariant
                                          .withOpacity(0.2),
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: Icon(Icons.music_note,
                                        color: Theme.of(context)
                                            .colorScheme
                                            .primary),
                                  ),
                                  title: Text(track.title,
                                      style: const TextStyle(
                                          fontWeight: FontWeight.bold,
                                          fontSize: 13)),
                                  subtitle: Text(track.artist,
                                      style: TextStyle(
                                          color: Theme.of(context)
                                              .colorScheme
                                              .onSurface
                                              .withOpacity(0.6),
                                          fontSize: 11)),
                                  trailing: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Container(
                                        padding: const EdgeInsets.symmetric(
                                            horizontal: 8, vertical: 3),
                                        decoration: BoxDecoration(
                                          color: hasLrc
                                              ? Theme.of(context)
                                                  .colorScheme
                                                  .primary
                                                  .withOpacity(0.12)
                                              : Theme.of(context)
                                                  .colorScheme
                                                  .outlineVariant
                                                  .withOpacity(0.2),
                                          borderRadius:
                                              BorderRadius.circular(6),
                                          border: Border.all(
                                            color: hasLrc
                                                ? Theme.of(context)
                                                    .colorScheme
                                                    .primary
                                                    .withOpacity(0.3)
                                                : Theme.of(context)
                                                    .colorScheme
                                                    .outlineVariant,
                                          ),
                                        ),
                                        child: Text(
                                          hasLrc ? 'Synced LRC' : 'No LRC',
                                          style: TextStyle(
                                            fontSize: 10,
                                            fontWeight: FontWeight.w600,
                                            color: hasLrc
                                                ? Theme.of(context)
                                                    .colorScheme
                                                    .primary
                                                : Theme.of(context)
                                                    .colorScheme
                                                    .onSurface
                                                    .withOpacity(0.6),
                                          ),
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      IconButton(
                                        icon: Icon(Icons.play_circle_fill,
                                            color: Theme.of(context)
                                                .colorScheme
                                                .primary),
                                        onPressed: () {
                                          ref
                                              .read(playerProvider.notifier)
                                              .playQueue(filteredTracks,
                                                  startIndex: idx);
                                        },
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

                    // Artists Tab
                    ArtistBrowserView(tracks: _localTracks),

                    // Albums Tab
                    AlbumBrowserView(tracks: _localTracks),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
