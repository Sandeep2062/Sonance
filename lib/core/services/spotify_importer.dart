import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../core/models/track.dart';

class SpotifyImportResult {
  final String title;
  final String? coverUrl;
  final List<SonanceTrack> tracks;

  const SpotifyImportResult({
    required this.title,
    this.coverUrl,
    required this.tracks,
  });
}

/// Parses Spotify playlist, album, and track URLs.
class SpotifyImporter {
  static final RegExp _spotifyUrlRegex = RegExp(
    r'https?:\/\/open\.spotify\.com\/(playlist|album|track)\/([a-zA-Z0-9]+)',
  );

  static bool isSpotifyUrl(String url) => _spotifyUrlRegex.hasMatch(url);

  /// Resolves tracks from any public Spotify URL.
  static Future<SpotifyImportResult?> resolveSpotifyUrl(String url) async {
    final match = _spotifyUrlRegex.firstMatch(url);
    if (match == null) return null;

    final type = match.group(1)!;
    final id = match.group(2)!;

    try {
      // Fetch public embed page for instant metadata without requiring developer API key
      final embedUrl = 'https://open.spotify.com/embed/$type/$id';
      final res = await http.get(Uri.parse(embedUrl)).timeout(const Duration(seconds: 8));

      if (res.statusCode == 200) {
        // Extract embedded JSON data from next_data script
        final html = res.body;
        final jsonMatch = RegExp(r'<script id="__NEXT_DATA__" type="application\/json">(.*?)<\/script>').firstMatch(html);

        if (jsonMatch != null) {
          final jsonStr = jsonMatch.group(1)!;
          final data = jsonDecode(jsonStr) as Map<String, dynamic>;
          final entity = data['props']?['pageProps']?['state']?['data']?['entity'];

          if (entity != null) {
            final title = entity['title'] as String? ?? 'Spotify Collection';
            final cover = (entity['images'] as List<dynamic>?)?.firstOrNull?['url'] as String?;
            final trackList = <SonanceTrack>[];

            final rawTrackList = entity['trackList'] as List<dynamic>? ?? [];
            for (final t in rawTrackList) {
              final trackTitle = t['title'] as String? ?? 'Unknown';
              final subtitle = t['subtitle'] as String? ?? 'Unknown Artist';
              final durationMs = t['duration'] as int? ?? 0;

              trackList.add(SonanceTrack(
                id: 'spotify_${t['id'] ?? trackTitle.hashCode}',
                title: trackTitle,
                artist: subtitle,
                album: title,
                duration: Duration(milliseconds: durationMs),
                coverUrl: cover,
                source: 'Spotify',
                qualityBadge: 'Spotify Sync',
                isLossless: false,
              ));
            }

            return SpotifyImportResult(
              title: title,
              coverUrl: cover,
              tracks: trackList,
            );
          }
        }
      }
    } catch (_) {}

    return null;
  }
}
