import 'dart:io';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:youtube_explode_dart/youtube_explode_dart.dart';
import '../../core/models/track.dart';
import '../lyrics/lyrics_engine.dart';

enum DownloadStatus { queued, downloading, lyricsSync, tagging, complete, failed }

class DownloadTask {
  final String id;
  final SonanceTrack track;
  final String format; // 'mp3', 'flac'
  final DownloadStatus status;
  final double percent;
  final String message;
  final String? lyricsStatus; // 'synced', 'plain', 'none'
  final String? audioPath;
  final String? lyricsPath;

  const DownloadTask({
    required this.id,
    required this.track,
    required this.format,
    this.status = DownloadStatus.queued,
    this.percent = 0.0,
    this.message = 'Queued...',
    this.lyricsStatus,
    this.audioPath,
    this.lyricsPath,
  });

  DownloadTask copyWith({
    DownloadStatus? status,
    double? percent,
    String? message,
    String? lyricsStatus,
    String? audioPath,
    String? lyricsPath,
  }) {
    return DownloadTask(
      id: id,
      track: track,
      format: format,
      status: status ?? this.status,
      percent: percent ?? this.percent,
      message: message ?? this.message,
      lyricsStatus: lyricsStatus ?? this.lyricsStatus,
      audioPath: audioPath ?? this.audioPath,
      lyricsPath: lyricsPath ?? this.lyricsPath,
    );
  }
}

class DownloadQueueNotifier extends StateNotifier<List<DownloadTask>> {
  DownloadQueueNotifier() : super([]);

  final _dio = Dio();
  final _yt = YoutubeExplode();
  bool _isProcessing = false;

  void addTask(SonanceTrack track, {String format = 'mp3'}) {
    final id = '${track.id}_${DateTime.now().millisecondsSinceEpoch}';
    final task = DownloadTask(id: id, track: track, format: format);
    state = [...state, task];
    _processNext();
  }

  Future<void> _processNext() async {
    if (_isProcessing) return;
    final nextIndex = state.indexWhere((t) => t.status == DownloadStatus.queued);
    if (nextIndex == -1) return;

    _isProcessing = true;
    final task = state[nextIndex];

    try {
      // 1. Prepare download directory
      final baseDir = await getApplicationDocumentsDirectory();
      final musicDir = Directory(p.join(baseDir.path, 'SonanceMusic', _sanitize(task.track.artist), _sanitize(task.track.album)));
      if (!await musicDir.exists()) {
        await musicDir.create(recursive: true);
      }

      final baseFilename = '${_sanitize(task.track.artist)} - ${_sanitize(task.track.title)}';
      final audioFile = p.join(musicDir.path, '$baseFilename.${task.format}');
      final lrcFile = p.join(musicDir.path, '$baseFilename.lrc');

      _updateTask(task.id, status: DownloadStatus.downloading, percent: 10, message: 'Downloading audio stream...');

      // 2. Download Audio (YouTube Explode HQ Stream or Direct Preview)
      if (task.track.streamUrl != null && task.track.streamUrl!.contains('youtube.com')) {
        final videoId = VideoId(task.track.streamUrl!);
        final manifest = await _yt.videos.streamsClient.getManifest(videoId);
        final audioStreamInfo = manifest.audioOnly.withHighestBitrate();
        final stream = _yt.videos.streamsClient.get(audioStreamInfo);

        final output = File(audioFile).openWrite();
        await stream.pipe(output);
        await output.flush();
        await output.close();
      } else if (task.track.streamUrl != null) {
        await _dio.download(
          task.track.streamUrl!,
          audioFile,
          onReceiveProgress: (rec, total) {
            if (total > 0) {
              final pct = (rec / total) * 60 + 10;
              _updateTask(task.id, percent: pct);
            }
          },
        );
      }

      // 3. Simultaneous Synced Lyrics Download with Anti-Mismatch Check
      _updateTask(task.id, status: DownloadStatus.lyricsSync, percent: 75, message: 'Fetching synced lyrics (.lrc)...');
      final savedLrc = await LyricsEngine.downloadAndSaveLrc(
        title: task.track.title,
        artist: task.track.artist,
        outputLrcPath: lrcFile,
        duration: task.track.duration,
      );

      final lrcStatus = savedLrc != null ? 'synced' : 'none';

      // 4. Mark Complete
      _updateTask(
        task.id,
        status: DownloadStatus.complete,
        percent: 100,
        message: 'Download & lyrics sync complete!',
        lyricsStatus: lrcStatus,
        audioPath: audioFile,
        lyricsPath: savedLrc?.path,
      );
    } catch (e) {
      _updateTask(task.id, status: DownloadStatus.failed, percent: 0, message: e.toString());
    } finally {
      _isProcessing = false;
      _processNext();
    }
  }

  void _updateTask(String id, {DownloadStatus? status, double? percent, String? message, String? lyricsStatus, String? audioPath, String? lyricsPath}) {
    state = [
      for (final t in state)
        if (t.id == id)
          t.copyWith(
            status: status,
            percent: percent,
            message: message,
            lyricsStatus: lyricsStatus,
            audioPath: audioPath,
            lyricsPath: lyricsPath,
          )
        else
          t,
    ];
  }

  String _sanitize(String name) => name.replaceAll(RegExp(r'[\\/*?:"<>|]'), '').trim();
}

final downloadQueueProvider = StateNotifierProvider<DownloadQueueNotifier, List<DownloadTask>>((ref) {
  return DownloadQueueNotifier();
});
