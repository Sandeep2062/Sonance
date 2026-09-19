import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

/// Lightweight, zero-dependency Discord Rich Presence client using native named pipes.
/// Compatible with Windows, macOS, and Linux without heavy native dependencies.
class DiscordRpcService {
  static final DiscordRpcService _instance = DiscordRpcService._internal();
  factory DiscordRpcService() => _instance;
  DiscordRpcService._internal();

  static const String clientId = '1280000000000000000'; // Sonance Discord App ID
  bool _isConnected = false;
  bool isEnabled = true;
  RandomAccessFile? _pipeFile;

  bool get isConnected => _isConnected;

  Future<void> initialize() async {
    if (!isEnabled) return;
    _connect();
  }

  bool _connect() {
    if (_isConnected && _pipeFile != null) return true;

    for (int i = 0; i < 10; i++) {
      try {
        final pipePath = Platform.isWindows
            ? r'\\.\pipe\discord-ipc-' + i.toString()
            : (Platform.environment['XDG_RUNTIME_DIR'] ?? '/tmp') + '/discord-ipc-$i';

        final file = File(pipePath);
        _pipeFile = file.openSync(mode: FileMode.write);
        _isConnected = true;
        _send(0, {'v': 1, 'client_id': clientId});
        return true;
      } catch (_) {
        continue;
      }
    }

    _isConnected = false;
    return false;
  }

  void _send(int op, Map<String, dynamic> payload) {
    if (!_isConnected || _pipeFile == null) return;
    try {
      final jsonBytes = utf8.encode(jsonEncode(payload));
      final header = ByteData(8);
      header.setUint32(0, op, Endian.little);
      header.setUint32(4, jsonBytes.length, Endian.little);

      _pipeFile!.writeFromSync(header.buffer.asUint8List());
      _pipeFile!.writeFromSync(jsonBytes);
      _pipeFile!.flushSync();
    } catch (_) {
      _isConnected = false;
      try {
        _pipeFile?.closeSync();
      } catch (_) {}
      _pipeFile = null;
    }
  }

  void updatePresence({
    required String title,
    required String artist,
    String? album,
    Duration? position,
    Duration? duration,
    bool isPlaying = true,
  }) {
    if (!isEnabled) return;
    if (!_isConnected) {
      if (!_connect()) return;
    }

    try {
      final now = DateTime.now().millisecondsSinceEpoch ~/ 1000;
      final posSec = position?.inSeconds ?? 0;
      final durSec = duration?.inSeconds ?? 0;

      final activity = <String, dynamic>{
        'details': title,
        'state': 'by $artist',
        'assets': {
          'large_image': 'https://raw.githubusercontent.com/Sandeep2062/Sonance/main/ui/logo.png',
          'large_text': (album != null && album.isNotEmpty) ? album : 'Sonance Music',
          'small_image': isPlaying ? 'play' : 'pause',
          'small_text': isPlaying ? 'Playing' : 'Paused',
        },
        'buttons': [
          {'label': 'Listen on Sonance', 'url': 'https://github.com/Sandeep2062/Sonance'},
          {'label': 'Get Sonance', 'url': 'https://github.com/Sandeep2062/Sonance/releases'},
        ],
      };

      if (isPlaying && durSec > 0) {
        activity['timestamps'] = {
          'start': now - posSec,
          'end': now - posSec + durSec,
        };
      }

      final payload = {
        'cmd': 'SET_ACTIVITY',
        'args': {'pid': pid, 'activity': activity},
        'nonce': DateTime.now().millisecondsSinceEpoch.toString(),
      };

      _send(1, payload);
    } catch (_) {}
  }

  void clearPresence() {
    if (!_isConnected) return;
    try {
      final payload = {
        'cmd': 'SET_ACTIVITY',
        'args': {'pid': pid, 'activity': null},
        'nonce': DateTime.now().millisecondsSinceEpoch.toString(),
      };
      _send(1, payload);
    } catch (_) {}
  }

  void dispose() {
    clearPresence();
    _isConnected = false;
    try {
      _pipeFile?.closeSync();
    } catch (_) {}
    _pipeFile = null;
  }
}

final discordRpcService = DiscordRpcService();
