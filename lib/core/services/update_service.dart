import 'dart:convert';
import 'dart:io';
import 'package:crypto/crypto.dart';
import 'package:http/http.dart' as http;
import 'package:package_info_plus/package_info_plus.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:url_launcher/url_launcher.dart';

class UpdateInfo {
  final bool updateAvailable;
  final String currentVersion;
  final String latestVersion;
  final String changelog;
  final String? downloadUrl;
  final String? expectedSha256;

  const UpdateInfo({
    required this.updateAvailable,
    required this.currentVersion,
    required this.latestVersion,
    this.changelog = '',
    this.downloadUrl,
    this.expectedSha256,
  });
}

class UpdateService {
  static const String _repo = 'Sandeep2062/Sonance';
  static const String _apiUrl = 'https://api.github.com/repos/$_repo/releases/latest';

  /// Checks GitHub Releases API for a newer version.
  static Future<UpdateInfo> checkForUpdates() async {
    try {
      final pkgInfo = await PackageInfo.fromPlatform();
      final currentVersion = pkgInfo.version.isNotEmpty ? pkgInfo.version : '3.6.2';

      final res = await http.get(
        Uri.parse(_apiUrl),
        headers: {
          'Accept': 'application/vnd.github.v3+json',
          'User-Agent': 'Sonance/$currentVersion',
        },
      ).timeout(const Duration(seconds: 8));

      if (res.statusCode != 200) {
        return UpdateInfo(updateAvailable: false, currentVersion: currentVersion, latestVersion: currentVersion);
      }

      final data = jsonDecode(res.body) as Map<String, dynamic>;
      final tag = (data['tag_name'] as String? ?? '').replaceAll('v', '').trim();
      final body = data['body'] as String? ?? 'Bug fixes and performance improvements.';
      final assets = data['assets'] as List<dynamic>? ?? [];

      if (tag.isNotEmpty && _isNewerVersion(tag, currentVersion)) {
        // Find matching binary asset for current operating system
        String? assetUrl;
        String? sha256AssetUrl;

        for (final asset in assets) {
          final name = (asset['name'] as String? ?? '').toLowerCase();
          final dlUrl = asset['browser_download_url'] as String?;

          if (name == 'release.sha256sum') {
            sha256AssetUrl = dlUrl;
          }

          if (Platform.isWindows && name.endsWith('.exe')) {
            assetUrl = dlUrl;
          } else if (Platform.isAndroid && name.endsWith('.apk')) {
            assetUrl = dlUrl;
          } else if (Platform.isMacOS && name.endsWith('.dmg')) {
            assetUrl = dlUrl;
          } else if (Platform.isLinux && (name.endsWith('.appimage') || name.endsWith('.deb') || name.endsWith('.tar.xz'))) {
            assetUrl = dlUrl;
          }
        }

        // Fetch SHA256 if available
        String? expectedHash;
        if (sha256AssetUrl != null && assetUrl != null) {
          try {
            final shaRes = await http.get(Uri.parse(sha256AssetUrl));
            if (shaRes.statusCode == 200) {
              final targetFilename = p.basename(Uri.parse(assetUrl).path);
              for (final line in shaRes.body.split('\n')) {
                if (line.contains(targetFilename)) {
                  expectedHash = line.split(RegExp(r'\s+')).first.trim();
                  break;
                }
              }
            }
          } catch (_) {}
        }

        return UpdateInfo(
          updateAvailable: true,
          currentVersion: currentVersion,
          latestVersion: tag,
          changelog: body,
          downloadUrl: assetUrl ?? data['html_url'] as String?,
          expectedSha256: expectedHash,
        );
      }

      return UpdateInfo(
        updateAvailable: false,
        currentVersion: currentVersion,
        latestVersion: tag.isNotEmpty ? tag : currentVersion,
      );
    } catch (_) {
      return const UpdateInfo(
        updateAvailable: false,
        currentVersion: '3.6.2',
        latestVersion: '3.6.2',
      );
    }
  }

  /// Downloads update binary, verifies SHA256, and opens installer.
  static Future<bool> downloadAndInstallUpdate(
    String downloadUrl,
    String? expectedSha256,
    void Function(double progress, String status) onProgress,
  ) async {
    try {
      final tempDir = await getTemporaryDirectory();
      final filename = p.basename(Uri.parse(downloadUrl).path);
      final targetFile = File(p.join(tempDir.path, filename));

      onProgress(0.1, 'Connecting to GitHub CDN...');

      final client = http.Client();
      final request = http.Request('GET', Uri.parse(downloadUrl));
      final response = await client.send(request);

      final total = response.contentLength ?? 0;
      int received = 0;

      final sink = targetFile.openWrite();

      await response.stream.listen((chunk) {
        sink.add(chunk);
        received += chunk.length;
        if (total > 0) {
          final pct = (received / total) * 0.8 + 0.1;
          onProgress(pct, 'Downloading: ${(received / (1024 * 1024)).toStringAsFixed(1)} MB / ${(total / (1024 * 1024)).toStringAsFixed(1)} MB');
        }
      }).asFuture();

      await sink.flush();
      await sink.close();

      // Verify SHA256 integrity
      if (expectedSha256 != null && expectedSha256.isNotEmpty) {
        onProgress(0.95, 'Verifying cryptographic checksum (SHA-256)...');
        final bytes = await targetFile.readAsBytes();
        final actualHash = sha256.convert(bytes).toString().toLowerCase();

        if (actualHash != expectedSha256.toLowerCase()) {
          onProgress(0.0, 'Checksum verification failed! Corrupted file.');
          return false;
        }
      }

      onProgress(1.0, 'Launching installer...');

      // Launch installer
      if (Platform.isWindows) {
        await Process.start(targetFile.path, [], mode: ProcessStartMode.detached);
        exit(0);
      } else {
        await launchUrl(Uri.file(targetFile.path));
      }

      return true;
    } catch (e) {
      onProgress(0.0, 'Update failed: $e');
      return false;
    }
  }

  static bool _isNewerVersion(String latest, String current) {
    try {
      final lParts = latest.split('.').map(int.parse).toList();
      final cParts = current.split('.').map(int.parse).toList();
      for (int i = 0; i < lParts.length && i < cParts.length; i++) {
        if (lParts[i] > cParts[i]) return true;
        if (lParts[i] < cParts[i]) return false;
      }
      return lParts.length > cParts.length;
    } catch (_) {
      return latest != current;
    }
  }
}
