import 'dart:io';
import 'dart:math';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:just_audio/just_audio.dart';
import 'package:youtube_explode_dart/youtube_explode_dart.dart';
import '../../core/models/lyrics.dart';
import '../../core/models/track.dart';
import '../../core/services/discord_rpc_service.dart';
import '../../core/services/scrobbler_service.dart';
import '../lyrics/lyrics_engine.dart';

class PlayerState {
  final SonanceTrack? currentTrack;
  final SyncedLyrics? lyrics;
  final bool isPlaying;
  final Duration position;
  final Duration duration;
  final int activeLyricIndex;
  final double volume; // 0.0 to 1.0
  final bool isMuted;
  final double previousVolume;
  final bool isShuffle;
  final LoopMode loopMode;
  final List<SonanceTrack> queue;
  final int queueIndex;
  final bool isLyricsLoading;
  final String? playbackError;

  const PlayerState({
    this.currentTrack,
    this.lyrics,
    this.isPlaying = false,
    this.position = Duration.zero,
    this.duration = Duration.zero,
    this.activeLyricIndex = -1,
    this.volume = 1.0,
    this.isMuted = false,
    this.previousVolume = 1.0,
    this.isShuffle = false,
    this.loopMode = LoopMode.off,
    this.queue = const [],
    this.queueIndex = 0,
    this.isLyricsLoading = false,
    this.playbackError,
  });

  PlayerState copyWith({
    SonanceTrack? currentTrack,
    SyncedLyrics? lyrics,
    bool? isPlaying,
    Duration? position,
    Duration? duration,
    int? activeLyricIndex,
    double? volume,
    bool? isMuted,
    double? previousVolume,
    bool? isShuffle,
    LoopMode? loopMode,
    List<SonanceTrack>? queue,
    int? queueIndex,
    bool? isLyricsLoading,
    String? playbackError,
  }) {
    return PlayerState(
      currentTrack: currentTrack ?? this.currentTrack,
      lyrics: lyrics ?? this.lyrics,
      isPlaying: isPlaying ?? this.isPlaying,
      position: position ?? this.position,
      duration: duration ?? this.duration,
      activeLyricIndex: activeLyricIndex ?? this.activeLyricIndex,
      volume: volume ?? this.volume,
      isMuted: isMuted ?? this.isMuted,
      previousVolume: previousVolume ?? this.previousVolume,
      isShuffle: isShuffle ?? this.isShuffle,
      loopMode: loopMode ?? this.loopMode,
      queue: queue ?? this.queue,
      queueIndex: queueIndex ?? this.queueIndex,
      isLyricsLoading: isLyricsLoading ?? this.isLyricsLoading,
      playbackError: playbackError,
    );
  }
}

class PlayerNotifier extends StateNotifier<PlayerState> {
  PlayerNotifier() : super(const PlayerState()) {
    _initAudioListeners();
  }

  final _player = AudioPlayer();
  final _random = Random();

  void _initAudioListeners() {
    _player.playerStateStream.listen((ps) {
      state = state.copyWith(isPlaying: ps.playing);

      // Handle auto-advancing to next track when song finishes
      if (ps.processingState == ProcessingState.completed) {
        if (state.currentTrack != null) {
          ScrobblerService.scrobble(
            artist: state.currentTrack!.artist,
            track: state.currentTrack!.title,
            album: state.currentTrack!.album,
            duration: state.duration.inSeconds,
          );
        }

        if (state.loopMode == LoopMode.one) {
          _player.seek(Duration.zero);
          _player.play();
        } else {
          next();
        }
      }
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

    _player.volumeStream.listen((vol) {
      state = state.copyWith(volume: vol);
    });
  }

  Future<void> playTrack(
    SonanceTrack track, {
    List<SonanceTrack>? queue,
    int? index,
  }) async {
    List<SonanceTrack> newQueue = queue ?? (state.queue.isEmpty ? [track] : state.queue);
    int newIndex = index ?? (queue != null ? (index ?? 0) : state.queue.indexWhere((t) => t.id == track.id));
    if (newIndex < 0) {
      newQueue = [...newQueue, track];
      newIndex = newQueue.length - 1;
    }

    state = state.copyWith(
      currentTrack: track,
      lyrics: null,
      activeLyricIndex: -1,
      queue: newQueue,
      queueIndex: newIndex,
      isLyricsLoading: true,
      playbackError: null,
    );

    // 1. Play audio
    try {
      if (track.localFilePath != null && File(track.localFilePath!).existsSync()) {
        await _player.setFilePath(track.localFilePath!);
        await _player.play();
      } else {
        String? streamUrl = track.streamUrl;

        // Extract direct audio stream for YouTube videos
        if (streamUrl != null &&
            (streamUrl.contains('youtube.com') || streamUrl.contains('youtu.be') || track.source == 'YouTube')) {
          final yt = YoutubeExplode();
          try {
            final rawId = track.id.startsWith('yt_') ? track.id.replaceFirst('yt_', '') : streamUrl;
            final videoId = VideoId(rawId);
            final manifest = await yt.videos.streamsClient.getManifest(videoId);
            final audioStreamInfo = manifest.audioOnly.withHighestBitrate();
            streamUrl = audioStreamInfo.url.toString();
          } catch (_) {
            // Keep original streamUrl if manifest extraction fails
          } finally {
            yt.close();
          }
        }

        if (streamUrl != null && streamUrl.isNotEmpty) {
          await _player.setUrl(streamUrl);
          await _player.play();
        } else {
          state = state.copyWith(playbackError: 'No playable audio stream available.');
        }
      }
    } catch (e) {
      state = state.copyWith(playbackError: 'Playback error: $e');
    }

    // Update Discord Presence
    discordRpcService.updatePresence(
      title: track.title,
      artist: track.artist,
      album: track.album,
      duration: track.duration,
      isPlaying: true,
    );

    // Update Last.fm / ListenBrainz Now Playing
    ScrobblerService.nowPlaying(
      artist: track.artist,
      track: track.title,
      album: track.album,
      duration: track.duration.inSeconds,
    );

    // 2. Resolve lyrics (check local companion .lrc first, fallback to LRCLIB)
    SyncedLyrics? resolvedLyrics;
    try {
      if (track.lyricsFilePath != null && File(track.lyricsFilePath!).existsSync()) {
        final lrcText = await File(track.lyricsFilePath!).readAsString();
        resolvedLyrics = SyncedLyrics.parse(lrcText, provider: 'Local LRC');
      } else if (track.localFilePath != null) {
        final extIndex = track.localFilePath!.lastIndexOf('.');
        if (extIndex != -1) {
          final candidateLrc = File('${track.localFilePath!.substring(0, extIndex)}.lrc');
          if (candidateLrc.existsSync()) {
            final lrcText = await candidateLrc.readAsString();
            resolvedLyrics = SyncedLyrics.parse(lrcText, provider: 'Local LRC');
          }
        }
      }
    } catch (_) {}

    if (resolvedLyrics == null || !resolvedLyrics.hasLyrics) {
      resolvedLyrics = await LyricsEngine.fetchLrclib(
        title: track.title,
        artist: track.artist,
        duration: track.duration,
      );
    }

    state = state.copyWith(
      lyrics: resolvedLyrics,
      isLyricsLoading: false,
    );
  }

  void playQueue(List<SonanceTrack> tracks, {int startIndex = 0}) {
    if (tracks.isEmpty) return;
    final idx = startIndex.clamp(0, tracks.length - 1);
    playTrack(tracks[idx], queue: tracks, index: idx);
  }

  void addToQueue(SonanceTrack track) {
    state = state.copyWith(queue: [...state.queue, track]);
  }

  void removeFromQueue(int index) {
    if (index < 0 || index >= state.queue.length) return;
    final updated = List<SonanceTrack>.from(state.queue)..removeAt(index);
    int newIndex = state.queueIndex;
    if (index < state.queueIndex) {
      newIndex = (newIndex - 1).clamp(0, updated.length - 1);
    } else if (newIndex >= updated.length) {
      newIndex = max(0, updated.length - 1);
    }
    state = state.copyWith(queue: updated, queueIndex: newIndex);
  }

  void clearQueue() {
    state = state.copyWith(queue: [], queueIndex: 0);
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

  void setVolume(double volume) {
    final v = volume.clamp(0.0, 1.0);
    _player.setVolume(v);
    state = state.copyWith(volume: v, isMuted: v == 0.0);
  }

  void toggleMute() {
    if (state.isMuted) {
      final restore = state.previousVolume > 0.05 ? state.previousVolume : 0.5;
      _player.setVolume(restore);
      state = state.copyWith(volume: restore, isMuted: false);
    } else {
      state = state.copyWith(previousVolume: state.volume, isMuted: true, volume: 0.0);
      _player.setVolume(0.0);
    }
  }

  void toggleShuffle() {
    state = state.copyWith(isShuffle: !state.isShuffle);
  }

  void cycleLoopMode() {
    LoopMode nextMode;
    switch (state.loopMode) {
      case LoopMode.off:
        nextMode = LoopMode.all;
        break;
      case LoopMode.all:
        nextMode = LoopMode.one;
        break;
      case LoopMode.one:
        nextMode = LoopMode.off;
        break;
    }
    _player.setLoopMode(nextMode);
    state = state.copyWith(loopMode: nextMode);
  }

  void next() {
    if (state.queue.isEmpty) return;

    if (state.isShuffle && state.queue.length > 1) {
      int nextIdx;
      do {
        nextIdx = _random.nextInt(state.queue.length);
      } while (nextIdx == state.queueIndex && state.queue.length > 1);
      playTrack(state.queue[nextIdx], queue: state.queue, index: nextIdx);
      return;
    }

    if (state.queueIndex + 1 < state.queue.length) {
      final nextIdx = state.queueIndex + 1;
      playTrack(state.queue[nextIdx], queue: state.queue, index: nextIdx);
    } else if (state.loopMode == LoopMode.all) {
      playTrack(state.queue.first, queue: state.queue, index: 0);
    }
  }

  void previous() {
    if (state.position.inSeconds > 3) {
      seek(Duration.zero);
      return;
    }

    if (state.queue.isEmpty) return;

    if (state.queueIndex > 0) {
      final prevIdx = state.queueIndex - 1;
      playTrack(state.queue[prevIdx], queue: state.queue, index: prevIdx);
    } else if (state.loopMode == LoopMode.all) {
      final lastIdx = state.queue.length - 1;
      playTrack(state.queue[lastIdx], queue: state.queue, index: lastIdx);
    } else {
      seek(Duration.zero);
    }
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
