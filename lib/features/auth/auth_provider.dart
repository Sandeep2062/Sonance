import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AuthState {
  final String deezerArl;
  final String qobuzId;
  final String qobuzToken;
  final String qobuzAppId;
  final String qobuzAppSecret;
  final String spotifyClientId;
  final String spotifyClientSecret;
  final String downloadDirectory;

  const AuthState({
    this.deezerArl = '',
    this.qobuzId = '',
    this.qobuzToken = '',
    this.qobuzAppId = '950096963',
    this.qobuzAppSecret = '979549437fcc4a3fead4867b5cd25dcb',
    this.spotifyClientId = '',
    this.spotifyClientSecret = '',
    this.downloadDirectory = '',
  });

  bool get isDeezerLoggedIn => deezerArl.trim().isNotEmpty;
  bool get isQobuzLoggedIn => qobuzToken.trim().isNotEmpty;
  bool get isSpotifyConfigured => spotifyClientId.trim().isNotEmpty;

  AuthState copyWith({
    String? deezerArl,
    String? qobuzId,
    String? qobuzToken,
    String? qobuzAppId,
    String? qobuzAppSecret,
    String? spotifyClientId,
    String? spotifyClientSecret,
    String? downloadDirectory,
  }) {
    return AuthState(
      deezerArl: deezerArl ?? this.deezerArl,
      qobuzId: qobuzId ?? this.qobuzId,
      qobuzToken: qobuzToken ?? this.qobuzToken,
      qobuzAppId: qobuzAppId ?? this.qobuzAppId,
      qobuzAppSecret: qobuzAppSecret ?? this.qobuzAppSecret,
      spotifyClientId: spotifyClientId ?? this.spotifyClientId,
      spotifyClientSecret: spotifyClientSecret ?? this.spotifyClientSecret,
      downloadDirectory: downloadDirectory ?? this.downloadDirectory,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier() : super(const AuthState()) {
    _loadFromStorage();
  }

  Future<void> _loadFromStorage() async {
    final prefs = await SharedPreferences.getInstance();
    state = AuthState(
      deezerArl: prefs.getString('deezer_arl') ?? '',
      qobuzId: prefs.getString('qobuz_id') ?? '',
      qobuzToken: prefs.getString('qobuz_token') ?? '',
      qobuzAppId: prefs.getString('qobuz_app_id') ?? '950096963',
      qobuzAppSecret: prefs.getString('qobuz_app_secret') ?? '979549437fcc4a3fead4867b5cd25dcb',
      spotifyClientId: prefs.getString('spotify_client_id') ?? '',
      spotifyClientSecret: prefs.getString('spotify_client_secret') ?? '',
      downloadDirectory: prefs.getString('download_directory') ?? '',
    );
  }

  Future<void> updateDeezer(String arl) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('deezer_arl', arl.trim());
    state = state.copyWith(deezerArl: arl.trim());
  }

  Future<void> updateQobuz({
    required String id,
    required String token,
    String? appId,
    String? appSecret,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('qobuz_id', id.trim());
    await prefs.setString('qobuz_token', token.trim());
    if (appId != null) await prefs.setString('qobuz_app_id', appId.trim());
    if (appSecret != null) await prefs.setString('qobuz_app_secret', appSecret.trim());

    state = state.copyWith(
      qobuzId: id.trim(),
      qobuzToken: token.trim(),
      qobuzAppId: appId?.trim(),
      qobuzAppSecret: appSecret?.trim(),
    );
  }

  Future<void> updateSpotify({required String clientId, required String clientSecret}) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('spotify_client_id', clientId.trim());
    await prefs.setString('spotify_client_secret', clientSecret.trim());
    state = state.copyWith(
      spotifyClientId: clientId.trim(),
      spotifyClientSecret: clientSecret.trim(),
    );
  }

  Future<void> updateDownloadDirectory(String path) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('download_directory', path.trim());
    state = state.copyWith(downloadDirectory: path.trim());
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier();
});
