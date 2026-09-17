import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:http/http.dart' as http;
import '../../core/models/track.dart';

/// Qobuz Studio Master 24-bit Hi-Res API Service
class QobuzService {
  static const String _apiBase = 'https://www.qobuz.com/api.json/0.2';

  /// Resolves track information by Qobuz track ID.
  static Future<SonanceTrack?> getTrack({
    required String trackId,
    required String appId,
  }) async {
    try {
      final uri = Uri.parse('$_apiBase/track/get?track_id=$trackId&app_id=$appId');
      final res = await http.get(uri).timeout(const Duration(seconds: 6));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        final hires = (data['hires'] as bool? ?? false) || (data['maximum_bit_depth'] as int? ?? 16) > 16;
        final bitDepth = data['maximum_bit_depth'] ?? 16;
        final samplingRate = data['maximum_sampling_rate'] ?? 44.1;

        return SonanceTrack(
          id: 'qobuz_${data['id']}',
          title: data['title'] ?? 'Unknown',
          artist: data['performer']?['name'] ?? 'Unknown Artist',
          album: data['album']?['title'] ?? 'Unknown Album',
          duration: Duration(seconds: data['duration'] as int? ?? 0),
          coverUrl: data['album']?['image']?['large'] ?? data['album']?['image']?['small'],
          source: 'Qobuz',
          qualityBadge: hires ? 'FLAC $bitDepth-bit / ${samplingRate}kHz' : 'FLAC 16-bit',
          isLossless: true,
          year: data['album']?['released_at'] != null ? DateTime.fromMillisecondsSinceEpoch((data['album']['released_at'] as int) * 1000).year : null,
          trackNumber: data['track_number'] as int?,
        );
      }
    } catch (_) {}
    return null;
  }

  /// Generates the signed request URL for streaming / downloading high-resolution FLAC.
  static String generateSignedFileUrl({
    required String trackId,
    required String userToken,
    required String appId,
    required String appSecret,
    int formatId = 27, // 27 = FLAC 24-bit/192kHz, 7 = 24-bit/96kHz, 6 = 16-bit/44.1kHz
  }) {
    final timestamp = (DateTime.now().millisecondsSinceEpoch ~/ 1000).toString();
    final rawSignature = 'trackgetFileUrlformat_id${formatId}intentstreamtrack_id${trackId}$timestamp$appSecret';
    final requestSig = md5.convert(utf8.encode(rawSignature)).toString();

    return '$_apiBase/track/getFileUrl?format_id=$formatId&intent=stream&track_id=$trackId&request_ts=$timestamp&request_sig=$requestSig&user_auth_token=$userToken&app_id=$appId';
  }
}
