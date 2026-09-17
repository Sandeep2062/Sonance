/// Track data model representing a playable, downloadable music item.
class SonanceTrack {
  final String id;
  final String title;
  final String artist;
  final String album;
  final Duration duration;
  final String? coverUrl;
  final String? streamUrl;
  final String? localFilePath;
  final String? lyricsFilePath;
  final String source; // 'Deezer', 'Qobuz', 'Spotify', 'YouTube', 'Local'
  final String qualityBadge; // 'FLAC 24-bit', 'FLAC 16-bit', '320 kbps', 'HQ'
  final bool isLossless;
  final int? year;
  final int? trackNumber;

  const SonanceTrack({
    required this.id,
    required this.title,
    required this.artist,
    required this.album,
    required this.duration,
    this.coverUrl,
    this.streamUrl,
    this.localFilePath,
    this.lyricsFilePath,
    this.source = 'Online',
    this.qualityBadge = 'HQ',
    this.isLossless = false,
    this.year,
    this.trackNumber,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'artist': artist,
        'album': album,
        'durationMs': duration.inMilliseconds,
        'coverUrl': coverUrl,
        'streamUrl': streamUrl,
        'localFilePath': localFilePath,
        'lyricsFilePath': lyricsFilePath,
        'source': source,
        'qualityBadge': qualityBadge,
        'isLossless': isLossless,
        'year': year,
        'trackNumber': trackNumber,
      };

  factory SonanceTrack.fromJson(Map<String, dynamic> json) => SonanceTrack(
        id: json['id'] as String,
        title: json['title'] as String,
        artist: json['artist'] as String,
        album: json['album'] as String? ?? 'Single',
        duration: Duration(milliseconds: json['durationMs'] as int? ?? 0),
        coverUrl: json['coverUrl'] as String?,
        streamUrl: json['streamUrl'] as String?,
        localFilePath: json['localFilePath'] as String?,
        lyricsFilePath: json['lyricsFilePath'] as String?,
        source: json['source'] as String? ?? 'Online',
        qualityBadge: json['qualityBadge'] as String? ?? 'HQ',
        isLossless: json['isLossless'] as bool? ?? false,
        year: json['year'] as int?,
        trackNumber: json['trackNumber'] as int?,
      );

  SonanceTrack copyWith({
    String? localFilePath,
    String? lyricsFilePath,
    String? streamUrl,
  }) {
    return SonanceTrack(
      id: id,
      title: title,
      artist: artist,
      album: album,
      duration: duration,
      coverUrl: coverUrl,
      streamUrl: streamUrl ?? this.streamUrl,
      localFilePath: localFilePath ?? this.localFilePath,
      lyricsFilePath: lyricsFilePath ?? this.lyricsFilePath,
      source: source,
      qualityBadge: qualityBadge,
      isLossless: isLossless,
      year: year,
      trackNumber: trackNumber,
    );
  }
}
