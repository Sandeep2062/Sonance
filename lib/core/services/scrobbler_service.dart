import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ScrobblerConfig {
  final bool lastfmEnabled;
  final String lastfmApiKey;
  final String lastfmSecret;
  final String lastfmSessionKey;
  final String lastfmUsername;
  final bool listenbrainzEnabled;
  final String listenbrainzToken;
  final String listenbrainzUsername;

  const ScrobblerConfig({
    this.lastfmEnabled = false,
    this.lastfmApiKey = '4a9f2c8d234f51e1948087e5498fa670',
    this.lastfmSecret = '26440e5e32927d312e7cad35edd5fcd5',
    this.lastfmSessionKey = '',
    this.lastfmUsername = '',
    this.listenbrainzEnabled = false,
    this.listenbrainzToken = '',
    this.listenbrainzUsername = '',
  });

  ScrobblerConfig copyWith({
    bool? lastfmEnabled,
    String? lastfmApiKey,
    String? lastfmSecret,
    String? lastfmSessionKey,
    String? lastfmUsername,
    bool? listenbrainzEnabled,
    String? listenbrainzToken,
    String? listenbrainzUsername,
  }) {
    return ScrobblerConfig(
      lastfmEnabled: lastfmEnabled ?? this.lastfmEnabled,
      lastfmApiKey: lastfmApiKey ?? this.lastfmApiKey,
      lastfmSecret: lastfmSecret ?? this.lastfmSecret,
      lastfmSessionKey: lastfmSessionKey ?? this.lastfmSessionKey,
      lastfmUsername: lastfmUsername ?? this.lastfmUsername,
      listenbrainzEnabled: listenbrainzEnabled ?? this.listenbrainzEnabled,
      listenbrainzToken: listenbrainzToken ?? this.listenbrainzToken,
      listenbrainzUsername: listenbrainzUsername ?? this.listenbrainzUsername,
    );
  }
}

class ScrobblerService {
  static const String _lastfmUrl = 'https://ws.audioscrobbler.com/2.0/';
  static const String _listenbrainzUrl = 'https://api.listenbrainz.org/1/submit-listens';
  static const String _listenbrainzValidateUrl = 'https://api.listenbrainz.org/1/validate-token';

  static Future<ScrobblerConfig> loadConfig() async {
    final prefs = await SharedPreferences.getInstance();
    return ScrobblerConfig(
      lastfmEnabled: prefs.getBool('lastfm_enabled') ?? false,
      lastfmApiKey: prefs.getString('lastfm_api_key') ?? '4a9f2c8d234f51e1948087e5498fa670',
      lastfmSecret: prefs.getString('lastfm_secret') ?? '26440e5e32927d312e7cad35edd5fcd5',
      lastfmSessionKey: prefs.getString('lastfm_session_key') ?? '',
      lastfmUsername: prefs.getString('lastfm_username') ?? '',
      listenbrainzEnabled: prefs.getBool('listenbrainz_enabled') ?? false,
      listenbrainzToken: prefs.getString('listenbrainz_token') ?? '',
      listenbrainzUsername: prefs.getString('listenbrainz_username') ?? '',
    );
  }

  static Future<void> saveConfig(ScrobblerConfig cfg) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('lastfm_enabled', cfg.lastfmEnabled);
    await prefs.setString('lastfm_api_key', cfg.lastfmApiKey);
    await prefs.setString('lastfm_secret', cfg.lastfmSecret);
    await prefs.setString('lastfm_session_key', cfg.lastfmSessionKey);
    await prefs.setString('lastfm_username', cfg.lastfmUsername);
    await prefs.setBool('listenbrainz_enabled', cfg.listenbrainzEnabled);
    await prefs.setString('listenbrainz_token', cfg.listenbrainzToken);
    await prefs.setString('listenbrainz_username', cfg.listenbrainzUsername);
  }

  static String _generateLastFmSig(Map<String, String> params, String secret) {
    final sortedKeys = params.keys.toList()..sort();
    final buffer = StringBuffer();
    for (final k in sortedKeys) {
      if (k == 'format' || k == 'callback') continue;
      buffer.write('$k${params[k]}');
    }
    buffer.write(secret);
    return md5.convert(utf8.encode(buffer.toString())).toString();
  }

  // ------------------ Last.fm ------------------

  static Future<bool> updateLastFmNowPlaying({
    required String artist,
    required String track,
    String? album,
    int? duration,
  }) async {
    final cfg = await loadConfig();
    if (!cfg.lastfmEnabled || cfg.lastfmSessionKey.isEmpty) return false;

    final params = <String, String>{
      'method': 'track.updateNowPlaying',
      'artist': artist,
      'track': track,
      'api_key': cfg.lastfmApiKey,
      'sk': cfg.lastfmSessionKey,
    };
    if (album != null && album.isNotEmpty) params['album'] = album;
    if (duration != null && duration > 0) params['duration'] = duration.toString();

    params['api_sig'] = _generateLastFmSig(params, cfg.lastfmSecret);
    params['format'] = 'json';

    try {
      final res = await http.post(Uri.parse(_lastfmUrl), body: params).timeout(const Duration(seconds: 8));
      return res.statusCode == 200 && res.body.contains('nowplaying');
    } catch (_) {
      return false;
    }
  }

  static Future<bool> scrobbleLastFm({
    required String artist,
    required String track,
    required int timestamp,
    String? album,
    int? duration,
  }) async {
    final cfg = await loadConfig();
    if (!cfg.lastfmEnabled || cfg.lastfmSessionKey.isEmpty) return false;

    final params = <String, String>{
      'method': 'track.scrobble',
      'artist': artist,
      'track': track,
      'timestamp': timestamp.toString(),
      'api_key': cfg.lastfmApiKey,
      'sk': cfg.lastfmSessionKey,
    };
    if (album != null && album.isNotEmpty) params['album'] = album;
    if (duration != null && duration > 0) params['duration'] = duration.toString();

    params['api_sig'] = _generateLastFmSig(params, cfg.lastfmSecret);
    params['format'] = 'json';

    try {
      final res = await http.post(Uri.parse(_lastfmUrl), body: params).timeout(const Duration(seconds: 8));
      return res.statusCode == 200 && res.body.contains('scrobbles');
    } catch (_) {
      return false;
    }
  }

  // ------------------ ListenBrainz ------------------

  static Future<Map<String, dynamic>> validateListenBrainzToken(String token) async {
    try {
      final res = await http.get(
        Uri.parse(_listenbrainzValidateUrl),
        headers: {'Authorization': 'Token $token'},
      ).timeout(const Duration(seconds: 8));
      final data = jsonDecode(res.body) as Map<String, dynamic>;
      return {'valid': data['valid'] == true, 'username': data['user_name'] ?? ''};
    } catch (e) {
      return {'valid': false, 'error': e.toString()};
    }
  }

  static Future<bool> submitListenBrainz({
    required String artist,
    required String track,
    String? album,
    required String listenType, // 'playing_now' or 'single'
    int? timestamp,
  }) async {
    final cfg = await loadConfig();
    if (!cfg.listenbrainzEnabled || cfg.listenbrainzToken.isEmpty) return false;

    final trackMeta = <String, dynamic>{
      'artist_name': artist,
      'track_name': track,
    };
    if (album != null && album.isNotEmpty) trackMeta['release_name'] = album;

    final payloadItem = <String, dynamic>{'track_metadata': trackMeta};
    if (listenType == 'single') {
      payloadItem['listened_at'] = timestamp ?? DateTime.now().millisecondsSinceEpoch ~/ 1000;
    }

    final body = {
      'listen_type': listenType,
      'payload': [payloadItem],
    };

    try {
      final res = await http.post(
        Uri.parse(_listenbrainzUrl),
        headers: {
          'Authorization': 'Token ${cfg.listenbrainzToken}',
          'Content-Type': 'application/json',
        },
        body: jsonEncode(body),
      ).timeout(const Duration(seconds: 8));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ------------------ Authentication & Session Linking ------------------

  static Future<Map<String, dynamic>> authenticateLastFm({
    required String username,
    required String password,
  }) async {
    final cfg = await loadConfig();
    final params = <String, String>{
      'method': 'auth.getMobileSession',
      'username': username.trim(),
      'password': password.trim(),
      'api_key': cfg.lastfmApiKey,
    };
    params['api_sig'] = _generateLastFmSig(params, cfg.lastfmSecret);
    params['format'] = 'json';

    try {
      final res = await http.post(Uri.parse(_lastfmUrl), body: params).timeout(const Duration(seconds: 10));
      final data = jsonDecode(res.body) as Map<String, dynamic>;

      if (data.containsKey('session')) {
        final session = data['session'] as Map<String, dynamic>;
        final sk = session['key'] as String? ?? '';
        final name = session['name'] as String? ?? username;

        final updated = cfg.copyWith(
          lastfmEnabled: true,
          lastfmSessionKey: sk,
          lastfmUsername: name,
        );
        await saveConfig(updated);
        return {'success': true, 'username': name};
      } else {
        return {'success': false, 'error': data['message'] ?? 'Authentication failed'};
      }
    } catch (e) {
      return {'success': false, 'error': e.toString()};
    }
  }

  static Future<void> disconnectLastFm() async {
    final cfg = await loadConfig();
    final updated = cfg.copyWith(
      lastfmEnabled: false,
      lastfmSessionKey: '',
      lastfmUsername: '',
    );
    await saveConfig(updated);
  }

  static Future<void> saveListenBrainz({
    required String token,
    required String username,
    bool enabled = true,
  }) async {
    final cfg = await loadConfig();
    final updated = cfg.copyWith(
      listenbrainzEnabled: enabled,
      listenbrainzToken: token.trim(),
      listenbrainzUsername: username.trim(),
    );
    await saveConfig(updated);
  }

  static Future<void> disconnectListenBrainz() async {
    final cfg = await loadConfig();
    final updated = cfg.copyWith(
      listenbrainzEnabled: false,
      listenbrainzToken: '',
      listenbrainzUsername: '',
    );
    await saveConfig(updated);
  }

  // ------------------ Unified Dispatcher ------------------

  static void nowPlaying({
    required String artist,
    required String track,
    String? album,
    int? duration,
  }) {
    updateLastFmNowPlaying(artist: artist, track: track, album: album, duration: duration);
    submitListenBrainz(artist: artist, track: track, album: album, listenType: 'playing_now');
  }

  static void scrobble({
    required String artist,
    required String track,
    String? album,
    int? duration,
    int? timestamp,
  }) {
    final ts = timestamp ?? DateTime.now().millisecondsSinceEpoch ~/ 1000;
    scrobbleLastFm(artist: artist, track: track, timestamp: ts, album: album, duration: duration);
    submitListenBrainz(artist: artist, track: track, album: album, listenType: 'single', timestamp: ts);
  }
}
