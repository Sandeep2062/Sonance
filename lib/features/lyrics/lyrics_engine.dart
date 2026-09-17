import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import '../../core/models/lyrics.dart';

/// Multi-provider lyrics engine with anti-mismatch duration verification.
class LyricsEngine {
  static const Map<String, String> _headers = {
    'User-Agent': 'Sonance/2.1 (https://github.com/Sandeep2062/Sonance)',
    'Accept': 'application/json',
  };

  static final RegExp _tsRegex = RegExp(r'\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]');
  static final RegExp _cjkRegex = RegExp(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]');

  /// Queries LRCLIB official API directly for instant synced/plain lyrics.
  static Future<SyncedLyrics?> fetchLrclib({
    required String title,
    String? artist,
    Duration? duration,
  }) async {
    try {
      // 1. Try exact match on /api/get
      final uri = Uri.https('lrclib.net', '/api/get', {
        'track_name': title,
        if (artist != null && artist.isNotEmpty) 'artist_name': artist,
        if (duration != null && duration.inSeconds > 10) 'duration': duration.inSeconds.toString(),
      });

      final res = await http.get(uri, headers: _headers).timeout(const Duration(seconds: 6));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        final synced = data['syncedLyrics'] as String?;
        final plain = data['plainLyrics'] as String?;

        if (synced != null && synced.isNotEmpty) {
          return SyncedLyrics.parse(synced, provider: 'LRCLIB (Synced)');
        } else if (plain != null && plain.isNotEmpty) {
          return SyncedLyrics.parse(plain, provider: 'LRCLIB (Plain)');
        }
      }

      // 2. Fallback to /api/search
      final searchUri = Uri.https('lrclib.net', '/api/search', {
        'q': artist != null ? '$artist $title' : title,
      });

      final searchRes = await http.get(searchUri, headers: _headers).timeout(const Duration(seconds: 6));
      if (searchRes.statusCode == 200) {
        final list = jsonDecode(searchRes.body) as List<dynamic>;
        for (final item in list) {
          final synced = item['syncedLyrics'] as String?;
          if (synced != null && synced.isNotEmpty) {
            return SyncedLyrics.parse(synced, provider: 'LRCLIB (Synced)');
          }
        }
        for (final item in list) {
          final plain = item['plainLyrics'] as String?;
          if (plain != null && plain.isNotEmpty) {
            return SyncedLyrics.parse(plain, provider: 'LRCLIB (Plain)');
          }
        }
      }
    } catch (_) {}

    return null;
  }

  /// Verifies that lyrics timestamp does not exceed or drastically fall short of audio duration.
  static bool verifyLyricsMatch(String lrcContent, Duration audioDuration) {
    if (lrcContent.length < 40) return false;

    if (audioDuration.inSeconds > 15) {
      final matches = _tsRegex.allMatches(lrcContent);
      if (matches.isNotEmpty) {
        final last = matches.last;
        final mins = int.parse(last.group(1)!);
        final secs = int.parse(last.group(2)!);
        final lastSec = mins * 60 + secs;

        // If lyrics extend more than 6s past the audio end -> Mismatch!
        if (lastSec > audioDuration.inSeconds + 6) return false;

        // If lyrics finish more than 45s early -> Suspicious mismatch!
        if ((audioDuration.inSeconds - lastSec) > 45) return false;
      }
    }

    return true;
  }

  /// NetEase Cloud Music lyrics provider for Asian and global tracks.
  static Future<SyncedLyrics?> fetchNetEase({
    required String title,
    String? artist,
  }) async {
    try {
      final q = artist != null ? '$artist $title' : title;
      final searchUri = Uri.http('music.163.com', '/api/search/get/web', {
        's': q,
        'type': '1',
        'limit': '1',
      });

      final searchRes = await http.get(searchUri).timeout(const Duration(seconds: 6));
      if (searchRes.statusCode == 200) {
        final data = jsonDecode(searchRes.body) as Map<String, dynamic>;
        final songs = data['result']?['songs'] as List<dynamic>?;
        if (songs != null && songs.isNotEmpty) {
          final songId = songs.first['id'];
          final lyricUri = Uri.http('music.163.com', '/api/song/lyric', {
            'id': songId.toString(),
            'lv': '1',
            'kv': '1',
            'tv': '-1',
          });

          final lyricRes = await http.get(lyricUri).timeout(const Duration(seconds: 6));
          if (lyricRes.statusCode == 200) {
            final lrcData = jsonDecode(lyricRes.body) as Map<String, dynamic>;
            final lrcContent = lrcData['lrc']?['lyric'] as String?;
            if (lrcContent != null && lrcContent.isNotEmpty) {
              return SyncedLyrics.parse(lrcContent, provider: 'NetEase');
            }
          }
        }
      }
    } catch (_) {}
    return null;
  }

  /// Cleans track title noise like (Official Music Video), [Remastered], feat.
  static String sanitizeTitle(String title) {
    return title
        .replaceAll(RegExp(r'\s*[\(\[](?:official\s*(?:video|audio|music\s*video)|remastered|remaster|\d{4}\s*remaster|deluxe|explicit|hd|hq|audio|visualizer)[\)\]]', caseSensitive: false), '')
        .replaceAll(RegExp(r'\s*[\(\[]\s*(?:feat|ft)\.?\s+[^)\]]+[\)\]]', caseSensitive: false), '')
        .replaceAll(RegExp(r'\s+(?:feat|ft)\.?\s+.*$', caseSensitive: false), '')
        .trim();
  }

  /// Removes Asian / CJK script lines to filter out bad transliterations.
  static String stripCjkLines(String content) {
    return content.split('\n').where((l) => !_cjkRegex.hasMatch(l)).join('\n');
  }

  /// Complete pipeline: fetches, verifies, and saves timestamped .lrc to disk.
  static Future<File?> downloadAndSaveLrc({
    required String title,
    required String artist,
    required String outputLrcPath,
    Duration? duration,
  }) async {
    final cleanTitle = sanitizeTitle(title);

    // 1. Try LRCLIB (Primary)
    SyncedLyrics? lyrics = await fetchLrclib(title: cleanTitle, artist: artist, duration: duration);

    // 2. Try NetEase (Fallback)
    lyrics ??= await fetchNetEase(title: cleanTitle, artist: artist);

    if (lyrics != null && lyrics.hasLyrics) {
      final raw = lyrics.lines.map((l) {
        if (l.timestamp != null) {
          final m = l.timestamp!.inMinutes.remainder(60).toString().padLeft(2, '0');
          final s = l.timestamp!.inSeconds.remainder(60).toString().padLeft(2, '0');
          final ms = (l.timestamp!.inMilliseconds.remainder(1000) ~/ 10).toString().padLeft(2, '0');
          return '[$m:$s.$ms] ${l.text}';
        }
        return l.text;
      }).join('\n');

      if (duration != null && !verifyLyricsMatch(raw, duration)) {
        return null; // Reject mismatched lyrics
      }

      final file = File(outputLrcPath);
      await file.writeAsString(raw);
      return file;
    }
    return null;
  }
}
