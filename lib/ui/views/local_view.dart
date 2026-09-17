import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path/path.dart' as p;
import '../../core/models/track.dart';
import '../../core/theme/app_theme.dart';
import '../../features/player/player_provider.dart';

class LocalView extends ConsumerStatefulWidget {
  const LocalView({super.key});

  @override
  ConsumerState<LocalView> createState() => _LocalViewState();
}

class _LocalViewState extends ConsumerState<LocalView> {
  String? _selectedFolder;
  List<SonanceTrack> _localTracks = [];
  bool _isScanning = false;

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
        await for (final entity in dir.list(recursive: true, followLinks: false)) {
          if (entity is File) {
            final ext = p.extension(entity.path).toLowerCase();
            if (['.mp3', '.flac', '.m4a', '.ogg', '.wav'].contains(ext)) {
              final filename = p.basenameWithoutExtension(entity.path);
              final parts = filename.split(' - ');
              final artist = parts.length > 1 ? parts[0].trim() : 'Unknown Artist';
              final title = parts.length > 1 ? parts.sublist(1).join(' - ').trim() : filename;

              final lrcFile = File('${p.withoutExtension(entity.path)}.lrc');
              final hasLrc = await lrcFile.exists();

              tracks.add(SonanceTrack(
                id: entity.path,
                title: title,
                artist: artist,
                album: 'Local',
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
    return Scaffold(
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Local Music Library', style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 2),
                    Text(_selectedFolder ?? 'No folder selected', style: const TextStyle(fontSize: 12, color: Colors.grey)),
                  ],
                ),
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(backgroundColor: SonanceTheme.surfaceColor),
                  icon: const Icon(Icons.folder_open, color: SonanceTheme.emerald),
                  label: const Text('Select Music Folder'),
                  onPressed: _pickFolder,
                ),
              ],
            ),
            const SizedBox(height: 16),

            if (_isScanning)
              const Expanded(child: Center(child: CircularProgressIndicator(color: SonanceTheme.emerald)))
            else if (_localTracks.isEmpty)
              Expanded(
                child: Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.folder_copy_outlined, size: 64, color: Colors.grey),
                      const SizedBox(height: 12),
                      const Text('Click "Select Music Folder" to browse your local audio library.', style: TextStyle(color: Colors.grey)),
                    ],
                  ),
                ),
              )
            else
              Expanded(
                child: ListView.separated(
                  itemCount: _localTracks.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 6),
                  itemBuilder: (context, idx) {
                    final track = _localTracks[idx];
                    final hasLrc = track.lyricsFilePath != null;

                    return Card(
                      child: ListTile(
                        leading: Container(
                          width: 44,
                          height: 44,
                          decoration: BoxDecoration(color: Colors.black45, borderRadius: BorderRadius.circular(8)),
                          child: const Icon(Icons.music_note, color: SonanceTheme.emerald),
                        ),
                        title: Text(track.title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                        subtitle: Text(track.artist, style: const TextStyle(color: Colors.grey, fontSize: 11)),
                        trailing: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: hasLrc ? SonanceTheme.emerald.withOpacity(0.15) : Colors.white10,
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Text(
                                hasLrc ? '✅ Synced' : '❌ No LRC',
                                style: TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.bold,
                                  color: hasLrc ? SonanceTheme.emerald : Colors.grey,
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            IconButton(
                              icon: const Icon(Icons.play_circle_fill, color: SonanceTheme.emerald),
                              onPressed: () => ref.read(playerProvider.notifier).playTrack(track),
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
