import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:path/path.dart' as p;
import '../models/track.dart';

class LocalAudioMetadata {
  final String title;
  final String artist;
  final String album;
  final String? coverUrl;
  final Duration duration;
  final int? year;
  final int? trackNumber;

  const LocalAudioMetadata({
    required this.title,
    required this.artist,
    required this.album,
    this.coverUrl,
    this.duration = Duration.zero,
    this.year,
    this.trackNumber,
  });
}

class LocalAudioService {
  static final Map<String, String?> _folderCoverCache = {};

  /// Scans a directory and returns an enriched list of SonanceTrack objects.
  static Future<List<SonanceTrack>> scanDirectory(String rootFolderPath) async {
    final tracks = <SonanceTrack>[];
    final dir = Directory(rootFolderPath);
    if (!dir.existsSync()) return tracks;

    final validExts = {'.mp3', '.flac', '.m4a', '.ogg', '.wav'};

    try {
      await for (final entity in dir.list(recursive: true, followLinks: false)) {
        if (entity is File) {
          final ext = p.extension(entity.path).toLowerCase();
          if (validExts.contains(ext)) {
            final track = await parseTrack(entity.path, rootFolderPath);
            tracks.add(track);
          }
        }
      }
    } catch (_) {}

    return tracks;
  }

  /// Parses a single audio file, extracting embedded tags, companion cover, and folder metadata.
  static Future<SonanceTrack> parseTrack(String filePath, [String? rootFolderPath]) async {
    final file = File(filePath);
    final ext = p.extension(filePath).toLowerCase();
    final parentDir = file.parent.path;

    // 1. Companion Folder Art Discovery
    String? coverUrl = _findFolderCover(parentDir);

    // 2. Parse embedded metadata (ID3 / FLAC)
    LocalAudioMetadata? meta;
    try {
      if (ext == '.mp3') {
        meta = await _parseId3(file);
      } else if (ext == '.flac') {
        meta = await _parseFlac(file);
      }
    } catch (_) {}

    // 3. Companion LRC lyrics discovery
    final lrcCandidate = File('${p.withoutExtension(filePath)}.lrc');
    final hasLrc = await lrcCandidate.exists();

    // 4. Fallback inference from Filename & Folder Hierarchy
    final filename = p.basenameWithoutExtension(filePath);
    String title = meta?.title.trim() ?? '';
    String artist = meta?.artist.trim() ?? '';
    String album = meta?.album.trim() ?? '';

    // If album is empty or placeholder, infer from folder hierarchy
    if (album.isEmpty || album.toLowerCase() == 'local library' || album.toLowerCase() == 'unknown') {
      final parentName = p.basename(parentDir);
      final isRoot = rootFolderPath != null && p.canonicalize(parentDir) == p.canonicalize(rootFolderPath);
      if (!isRoot && parentName.isNotEmpty) {
        album = parentName;
      } else {
        album = 'Singles & Loose Tracks';
      }
    }

    // If artist is empty, infer from filename or parent folder
    if (artist.isEmpty || artist.toLowerCase() == 'unknown artist') {
      final parts = filename.split(' - ');
      if (parts.length > 1) {
        artist = parts[0].trim();
      } else {
        final grandParent = file.parent.parent.path;
        final isRoot = rootFolderPath != null && (p.canonicalize(parentDir) == p.canonicalize(rootFolderPath) || p.canonicalize(grandParent) == p.canonicalize(rootFolderPath));
        if (!isRoot) {
          artist = p.basename(grandParent);
        }
      }
    }
    if (artist.isEmpty) artist = 'Unknown Artist';

    // If title is empty, infer from filename
    if (title.isEmpty) {
      final parts = filename.split(' - ');
      if (parts.length > 1) {
        title = parts.sublist(1).join(' - ').trim();
      } else {
        title = filename;
      }
      // Strip leading track number if present (e.g. "01 ", "01. ", "01 - ")
      title = title.replaceFirst(RegExp(r'^\d+[\s\.\-_]+'), '').trim();
    }
    if (title.isEmpty) title = filename;

    // Use embedded cover if companion cover is not found
    if (coverUrl == null && meta?.coverUrl != null) {
      coverUrl = meta!.coverUrl;
    }

    return SonanceTrack(
      id: filePath,
      title: title,
      artist: artist,
      album: album,
      duration: meta?.duration ?? Duration.zero,
      coverUrl: coverUrl,
      localFilePath: filePath,
      lyricsFilePath: hasLrc ? lrcCandidate.path : null,
      source: 'Local',
      qualityBadge: ext.replaceAll('.', '').toUpperCase(),
      isLossless: ext == '.flac' || ext == '.wav',
      year: meta?.year,
      trackNumber: meta?.trackNumber,
    );
  }

  /// Locates companion cover images within the directory (cover.jpg, folder.png, etc.).
  static String? _findFolderCover(String dirPath) {
    if (_folderCoverCache.containsKey(dirPath)) {
      return _folderCoverCache[dirPath];
    }

    final candidateNames = [
      'cover.jpg', 'cover.png', 'cover.jpeg',
      'folder.jpg', 'folder.png', 'folder.jpeg',
      'front.jpg', 'front.png', 'front.jpeg',
      'albumart.jpg', 'albumartsmall.jpg', 'artwork.jpg',
    ];

    for (final name in candidateNames) {
      final img = File(p.join(dirPath, name));
      if (img.existsSync()) {
        _folderCoverCache[dirPath] = img.path;
        return img.path;
      }
    }

    // Check case-insensitive match for common image files in the directory
    try {
      final dir = Directory(dirPath);
      if (dir.existsSync()) {
        for (final entity in dir.listSync()) {
          if (entity is File) {
            final name = p.basename(entity.path).toLowerCase();
            final ext = p.extension(name);
            if (['.jpg', '.jpeg', '.png'].contains(ext)) {
              if (name.contains('cover') || name.contains('folder') || name.contains('front') || name.contains('album')) {
                _folderCoverCache[dirPath] = entity.path;
                return entity.path;
              }
            }
          }
        }
      }
    } catch (_) {}

    _folderCoverCache[dirPath] = null;
    return null;
  }

  /// Pure Dart lightweight ID3v2.3 / ID3v2.4 parser for Title, Artist, Album, and APIC Cover.
  static Future<LocalAudioMetadata?> _parseId3(File file) async {
    RandomAccessFile? raf;
    try {
      raf = await file.open(mode: FileMode.read);
      final header = await raf.read(10);
      if (header.length < 10) return null;

      // Check "ID3" identifier
      if (header[0] != 0x49 || header[1] != 0x44 || header[2] != 0x33) return null;

      final version = header[3];
      final tagSize = _synchsafeToInt(header.sublist(6, 10));
      if (tagSize <= 0) return null;

      final readLimit = tagSize.clamp(0, 1024 * 1024); // read up to 1MB
      final tagBytes = await raf.read(readLimit);

      String title = '';
      String artist = '';
      String album = '';
      String? coverDataUri;
      int? year;
      int? trackNumber;

      int offset = 0;
      while (offset + 10 <= tagBytes.length) {
        final frameId = String.fromCharCodes(tagBytes.sublist(offset, offset + 4));
        if (frameId.codeUnits.any((c) => c == 0 || c < 32 || c > 126)) break;

        int frameSize;
        if (version >= 4) {
          frameSize = _synchsafeToInt(tagBytes.sublist(offset + 4, offset + 8));
        } else {
          frameSize = (tagBytes[offset + 4] << 24) |
              (tagBytes[offset + 5] << 16) |
              (tagBytes[offset + 6] << 8) |
              tagBytes[offset + 7];
        }

        if (frameSize <= 0 || offset + 10 + frameSize > tagBytes.length) break;

        final frameData = tagBytes.sublist(offset + 10, offset + 10 + frameSize);
        offset += 10 + frameSize;

        if (frameData.isEmpty) continue;

        if (frameId == 'TIT2') {
          title = _decodeId3Text(frameData);
        } else if (frameId == 'TPE1') {
          artist = _decodeId3Text(frameData);
        } else if (frameId == 'TALB') {
          album = _decodeId3Text(frameData);
        } else if (frameId == 'TYER' || frameId == 'TDRC') {
          final yrStr = _decodeId3Text(frameData);
          year = int.tryParse(RegExp(r'\d{4}').firstMatch(yrStr)?.group(0) ?? '');
        } else if (frameId == 'TRCK') {
          final trkStr = _decodeId3Text(frameData);
          trackNumber = int.tryParse(RegExp(r'^\d+').firstMatch(trkStr)?.group(0) ?? '');
        } else if (frameId == 'APIC' && coverDataUri == null) {
          coverDataUri = _extractApicImage(frameData);
        }
      }

      return LocalAudioMetadata(
        title: title,
        artist: artist,
        album: album,
        coverUrl: coverDataUri,
        year: year,
        trackNumber: trackNumber,
      );
    } catch (_) {
      return null;
    } finally {
      await raf?.close();
    }
  }

  /// Pure Dart lightweight FLAC metadata parser for Vorbis comments and embedded pictures.
  static Future<LocalAudioMetadata?> _parseFlac(File file) async {
    RandomAccessFile? raf;
    try {
      raf = await file.open(mode: FileMode.read);
      final magic = await raf.read(4);
      if (magic.length < 4 || String.fromCharCodes(magic) != 'fLaC') return null;

      String title = '';
      String artist = '';
      String album = '';
      String? coverDataUri;
      int? year;
      int? trackNumber;

      bool isLast = false;
      while (!isLast) {
        final blockHeader = await raf.read(4);
        if (blockHeader.length < 4) break;

        isLast = (blockHeader[0] & 0x80) != 0;
        final blockType = blockHeader[0] & 0x7F;
        final blockSize = (blockHeader[1] << 16) | (blockHeader[2] << 8) | blockHeader[3];

        if (blockSize <= 0) break;

        // Block Type 4: VORBIS_COMMENT
        if (blockType == 4) {
          final blockData = await raf.read(blockSize.clamp(0, 128 * 1024));
          final bd = ByteData.sublistView(blockData);
          int offset = 0;

          if (offset + 4 <= blockData.length) {
            final vendorLen = bd.getUint32(offset, Endian.little);
            offset += 4 + vendorLen;
          }

          if (offset + 4 <= blockData.length) {
            final numComments = bd.getUint32(offset, Endian.little);
            offset += 4;

            for (int i = 0; i < numComments && offset + 4 <= blockData.length; i++) {
              final cLen = bd.getUint32(offset, Endian.little);
              offset += 4;
              if (offset + cLen > blockData.length) break;

              final comment = utf8.decode(blockData.sublist(offset, offset + cLen), allowMalformed: true);
              offset += cLen;

              final eqIdx = comment.indexOf('=');
              if (eqIdx != -1) {
                final key = comment.substring(0, eqIdx).toUpperCase();
                final val = comment.substring(eqIdx + 1).trim();

                if (key == 'TITLE') title = val;
                if (key == 'ARTIST') artist = val;
                if (key == 'ALBUM') album = val;
                if (key == 'DATE' || key == 'YEAR') {
                  year = int.tryParse(RegExp(r'\d{4}').firstMatch(val)?.group(0) ?? '');
                }
                if (key == 'TRACKNUMBER') {
                  trackNumber = int.tryParse(RegExp(r'^\d+').firstMatch(val)?.group(0) ?? '');
                }
              }
            }
          }
        }
        // Block Type 6: PICTURE
        else if (blockType == 6 && coverDataUri == null) {
          final blockData = await raf.read(blockSize.clamp(0, 4 * 1024 * 1024));
          coverDataUri = _extractFlacPicture(blockData);
        } else {
          // Skip other blocks
          await raf.setPosition(await raf.position() + blockSize);
        }
      }

      return LocalAudioMetadata(
        title: title,
        artist: artist,
        album: album,
        coverUrl: coverDataUri,
        year: year,
        trackNumber: trackNumber,
      );
    } catch (_) {
      return null;
    } finally {
      await raf?.close();
    }
  }

  static int _synchsafeToInt(List<int> bytes) {
    if (bytes.length < 4) return 0;
    return ((bytes[0] & 0x7F) << 21) |
        ((bytes[1] & 0x7F) << 14) |
        ((bytes[2] & 0x7F) << 7) |
        (bytes[3] & 0x7F);
  }

  static String _decodeId3Text(List<int> data) {
    if (data.isEmpty) return '';
    final enc = data[0];
    final bytes = data.sublist(1);

    try {
      if (enc == 0) {
        // ISO-8859-1 (Latin1)
        return latin1.decode(bytes).split('\x00').first.trim();
      } else if (enc == 1) {
        // UTF-16 with BOM
        if (bytes.length >= 2) {
          return _decodeUtf16(bytes).split('\x00').first.trim();
        }
      } else if (enc == 2) {
        // UTF-16BE
        return _decodeUtf16BE(bytes).split('\x00').first.trim();
      } else if (enc == 3) {
        // UTF-8
        return utf8.decode(bytes, allowMalformed: true).split('\x00').first.trim();
      }
    } catch (_) {}

    return utf8.decode(bytes, allowMalformed: true).split('\x00').first.trim();
  }

  static String _decodeUtf16(List<int> bytes) {
    if (bytes.length < 2) return '';
    final isLE = bytes[0] == 0xFF && bytes[1] == 0xFE;
    final payload = bytes.sublist(2);
    final buffer = StringBuffer();
    for (int i = 0; i + 1 < payload.length; i += 2) {
      final code = isLE ? (payload[i] | (payload[i + 1] << 8)) : ((payload[i] << 8) | payload[i + 1]);
      if (code == 0) break;
      buffer.writeCharCode(code);
    }
    return buffer.toString();
  }

  static String _decodeUtf16BE(List<int> bytes) {
    final buffer = StringBuffer();
    for (int i = 0; i + 1 < bytes.length; i += 2) {
      final code = (bytes[i] << 8) | bytes[i + 1];
      if (code == 0) break;
      buffer.writeCharCode(code);
    }
    return buffer.toString();
  }

  static String? _extractApicImage(List<int> data) {
    if (data.length < 10) return null;
    try {
      int offset = 1; // skip encoding byte

      // Read MIME type (null-terminated ASCII)
      final mimeStart = offset;
      while (offset < data.length && data[offset] != 0) {
        offset++;
      }
      final mime = String.fromCharCodes(data.sublist(mimeStart, offset)).toLowerCase();
      offset++; // skip null terminator

      if (offset >= data.length) return null;
      offset++; // skip picture type byte

      // Skip description string
      while (offset < data.length && data[offset] != 0) {
        offset++;
      }
      offset++; // skip null terminator
      if (offset < data.length && data[offset] == 0) offset++; // potential second null for UTF16

      if (offset < data.length) {
        final imgBytes = data.sublist(offset);
        if (imgBytes.length > 200) {
          final resolvedMime = mime.contains('png') ? 'image/png' : 'image/jpeg';
          return 'data:$resolvedMime;base64,${base64Encode(imgBytes)}';
        }
      }
    } catch (_) {}
    return null;
  }

  static String? _extractFlacPicture(Uint8List data) {
    try {
      final bd = ByteData.sublistView(data);
      int offset = 0;

      offset += 4; // skip picture type
      if (offset + 4 > data.length) return null;

      final mimeLen = bd.getUint32(offset, Endian.big);
      offset += 4;
      if (offset + mimeLen > data.length) return null;

      final mime = utf8.decode(data.sublist(offset, offset + mimeLen), allowMalformed: true);
      offset += mimeLen;

      if (offset + 4 > data.length) return null;
      final descLen = bd.getUint32(offset, Endian.big);
      offset += 4 + descLen;

      // Skip width (4), height (4), color depth (4), colors (4) = 16 bytes
      offset += 16;
      if (offset + 4 > data.length) return null;

      final dataLen = bd.getUint32(offset, Endian.big);
      offset += 4;

      if (offset + dataLen <= data.length) {
        final imgBytes = data.sublist(offset, offset + dataLen);
        final resolvedMime = mime.contains('png') ? 'image/png' : 'image/jpeg';
        return 'data:$resolvedMime;base64,${base64Encode(imgBytes)}';
      }
    } catch (_) {}
    return null;
  }
}
