import 'dart:convert';
import 'dart:typed_data';
import 'package:crypto/crypto.dart';
import 'package:http/http.dart' as http;
import '../../core/models/track.dart';

/// Deezer API & Decryption Service
class DeezerService {
  static const String _apiBase = 'https://api.deezer.com';

  /// Resolves track information by Deezer track ID.
  static Future<SonanceTrack?> getTrack(String trackId) async {
    try {
      final res = await http.get(Uri.parse('$_apiBase/track/$trackId')).timeout(const Duration(seconds: 6));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        if (data.containsKey('error')) return null;

        return SonanceTrack(
          id: 'deezer_${data['id']}',
          title: data['title_short'] ?? data['title'] ?? 'Unknown',
          artist: data['artist']?['name'] ?? 'Unknown Artist',
          album: data['album']?['title'] ?? 'Unknown Album',
          duration: Duration(seconds: data['duration'] as int? ?? 0),
          coverUrl: data['album']?['cover_xl'] ?? data['album']?['cover_medium'],
          streamUrl: data['preview'],
          source: 'Deezer',
          qualityBadge: (data['disk_number'] != null) ? 'FLAC / 320k' : '320 kbps',
          isLossless: true,
          year: data['release_date'] != null ? DateTime.tryParse(data['release_date'])?.year : null,
          trackNumber: data['track_position'] as int?,
        );
      }
    } catch (_) {}
    return null;
  }

  /// Derives the Blowfish decryption key for a Deezer track.
  static Uint8List getBlowfishKey(String trackId) {
    const salt = 'g4el58wc0zvf9na1';
    final idMd5 = md5.convert(utf8.encode(trackId)).toString();
    final bfKey = Uint8List(16);

    for (int i = 0; i < 16; i++) {
      final a = idMd5.codeUnitAt(i);
      final b = idMd5.codeUnitAt(i + 16);
      final c = salt.codeUnitAt(i);
      bfKey[i] = a ^ b ^ c;
    }

    return bfKey;
  }

  /// Checks if a Deezer ARL cookie is valid.
  static Future<bool> validateArl(String arl) async {
    if (arl.trim().length < 50) return false;
    try {
      final res = await http.get(
        Uri.parse('https://www.deezer.com/ajax/gw-light.php?method=deezer.getUserData&input=3&api_version=1.0&api_token='),
        headers: {'Cookie': 'arl=$arl'},
      ).timeout(const Duration(seconds: 6));

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        final user = data['results']?['USER'];
        return user != null && user['USER_ID'] != 0;
      }
    } catch (_) {}
    return false;
  }
}
