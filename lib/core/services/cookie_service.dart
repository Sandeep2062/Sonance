import 'dart:io';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

class PlatformCookieStatus {
  final bool hasYouTubeCookies;
  final bool hasDeezerArl;
  final bool hasSpotifySession;

  const PlatformCookieStatus({
    this.hasYouTubeCookies = false,
    this.hasDeezerArl = false,
    this.hasSpotifySession = false,
  });
}

/// Manages platform cookies (YouTube, Deezer, Spotify) for desktop and mobile.
class CookieService {
  /// Gets path to Netscape youtube_cookies.txt file.
  static Future<File> getYouTubeCookieFile() async {
    final appDir = await getApplicationDocumentsDirectory();
    final cookieDir = Directory(p.join(appDir.path, 'Sonance', 'cookies'));
    if (!await cookieDir.exists()) {
      await cookieDir.create(recursive: true);
    }
    return File(p.join(cookieDir.path, 'youtube_cookies.txt'));
  }

  /// Checks active cookie status across platforms.
  static Future<PlatformCookieStatus> checkCookieStatus({
    String? deezerArl,
    String? spotifySpDc,
  }) async {
    final ytFile = await getYouTubeCookieFile();
    final hasYt = await ytFile.exists() && (await ytFile.length()) > 50;

    return PlatformCookieStatus(
      hasYouTubeCookies: hasYt,
      hasDeezerArl: deezerArl != null && deezerArl.trim().isNotEmpty,
      hasSpotifySession: spotifySpDc != null && spotifySpDc.trim().isNotEmpty,
    );
  }

  /// Saves raw Netscape formatted cookies into storage.
  static Future<void> saveNetscapeCookies(String rawContent) async {
    final file = await getYouTubeCookieFile();
    await file.writeAsString(rawContent);
  }
}
