import 'dart:convert';
import 'package:http/http.dart' as http;

class AudioTags {
  final String title;
  final String artist;
  final String album;
  final String albumArtist;
  final String year;
  final String genre;
  final String trackNumber;
  final String totalTracks;
  final String discNumber;
  final String comment;
  final String? coverDataUri;

  const AudioTags({
    this.title = '',
    this.artist = '',
    this.album = '',
    this.albumArtist = '',
    this.year = '',
    this.genre = '',
    this.trackNumber = '',
    this.totalTracks = '',
    this.discNumber = '',
    this.comment = '',
    this.coverDataUri,
  });

  factory AudioTags.fromJson(Map<String, dynamic> json) {
    return AudioTags(
      title: json['title'] as String? ?? '',
      artist: json['artist'] as String? ?? '',
      album: json['album'] as String? ?? '',
      albumArtist: json['album_artist'] as String? ?? '',
      year: json['year'] as String? ?? '',
      genre: json['genre'] as String? ?? '',
      trackNumber: json['track_number'] as String? ?? '',
      totalTracks: json['total_tracks'] as String? ?? '',
      discNumber: json['disc_number'] as String? ?? '',
      comment: json['comment'] as String? ?? '',
      coverDataUri: json['cover_data_uri'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'title': title,
      'artist': artist,
      'album': album,
      'album_artist': albumArtist,
      'year': year,
      'genre': genre,
      'track_number': trackNumber,
      'total_tracks': totalTracks,
      'disc_number': discNumber,
      'comment': comment,
      if (coverDataUri != null) 'cover_data_uri': coverDataUri,
    };
  }
}

class TagService {
  /// Queries MusicBrainz API to auto-fill metadata for a given track title and artist.
  static Future<AudioTags?> autoFetchMetadata(String title, String artist) async {
    try {
      final query = Uri.encodeComponent('recording:"$title" AND artist:"$artist"');
      final url = 'https://musicbrainz.org/ws/2/recording/?query=$query&fmt=json';
      final res = await http.get(
        Uri.parse(url),
        headers: {'User-Agent': 'Sonance/3.6.2 (https://github.com/Sandeep2062/Sonance)'},
      ).timeout(const Duration(seconds: 6));

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        final recordings = data['recordings'] as List<dynamic>? ?? [];
        if (recordings.isNotEmpty) {
          final rec = recordings[0] as Map<String, dynamic>;
          final releases = rec['releases'] as List<dynamic>? ?? [];
          String album = '';
          String year = '';
          String? coverUrl;

          if (releases.isNotEmpty) {
            final rel = releases[0] as Map<String, dynamic>;
            album = rel['title'] as String? ?? '';
            year = (rel['date'] as String? ?? '').split('-').first;
            final relId = rel['id'] as String?;
            if (relId != null) {
              coverUrl = 'https://coverartarchive.org/release/$relId/front-500';
            }
          }

          final tags = rec['tags'] as List<dynamic>? ?? [];
          String genre = '';
          if (tags.isNotEmpty) {
            genre = (tags[0]['name'] as String? ?? '').toUpperCase();
          }

          return AudioTags(
            title: title,
            artist: artist,
            album: album,
            year: year,
            genre: genre,
            coverDataUri: coverUrl,
          );
        }
      }
    } catch (_) {}
    return null;
  }
}
