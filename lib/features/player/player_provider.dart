import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:just_audio/just_audio.dart';
import '../../core/models/lyrics.dart';
import '../../core/models/track.dart';
import '../lyrics/lyrics_engine.dart';

class PlayerState {
  final SonanceTrack? currentTrack;
  final SyncedLyrics? lyrics;
  final bool isPlaying;
  final Duration position;
  final Duration duration;
  final int activeLyricIndex;

  const PlayerState({
    this.currentTrack,
    this.lyrics,
    this.isPlaying = false,
    this.position = Duration.zero,
    this.duration = Duration.zero,
    this.activeLyricIndex = -1,
  });

  PlayerState copyWith({
    SonanceTrack? currentTrack,
    SyncedLyrics? lyrics,
    bool? isPlaying,
    Duration? position,
    Duration? duration,
    int? activeLyricIndex,
  }) {
    return PlayerState(
      currentTrack: currentTrack ?? this.currentTrack,
      lyrics: lyrics ?? this.lyrics,
      isPlaying: isPlaying ?? this.isPlaying,
      position: position ?? this.position,
      duration: duration ?? this.duration,
      activeLyricIndex: activeLyricIndex ?? this.activeLyricIndex,
    );
  }
}

class PlayerNotifier extends StateNotifier<PlayerState> {
  PlayerNotifier() : super(const PlayerState()) {
    _initAudioListeners();
  }

  final _player = AudioPlayer();

  void _initAudioListeners() {
    _player.playerStateStream.listen((ps) {
      state = state.copyWith(isPlaying: ps.playing);
    });

    _player.positionStream.listen((pos) {
      final activeIdx = state.lyrics?.getActiveLineIndex(pos) ?? -1;
      state = state.copyWith(
        position: pos,
        activeLyricIndex: activeIdx,
      );
    });

    _player.durationStream.listen((dur) {
      if (dur != null) {
        state = state.copyWith(duration: dur);
      }
    });
  }

  Future<void> playTrack(SonanceTrack track) async {
    state = state.copyWith(
      currentTrack: track,
      lyrics: null,
      activeLyricIndex: -1,
    );

    // 1. Play audio
    try {
      if (track.localFilePath != null) {
        await _player.setFilePath(track.localFilePath!);
      } else if (track.streamUrl != null) {
        await _player.setUrl(track.streamUrl!);
      }
      _player.play();
    } catch (_) {}

    // 2. Fetch lyrics simultaneously
    final lyrics = await LyricsEngine.fetchLrclib(
      title: track.title,
      artist: track.artist,
      duration: track.duration,
    );
    state = state.copyWith(lyrics: lyrics);
  }

  void togglePlayPause() {
    if (_player.playing) {
      _player.pause();
    } else {
      _player.play();
    }
  }

  void seek(Duration position) {
    _player.seek(position);
  }

  @override
  void dispose() {
    _player.dispose();
    super.dispose();
  }
}

final playerProvider = StateNotifierProvider<PlayerNotifier, PlayerState>((ref) {
  return PlayerNotifier();
});
