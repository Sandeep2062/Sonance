import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'package:youtube_explode_dart/youtube_explode_dart.dart';
import '../../core/models/track.dart';

class SearchState {
  final List<SonanceTrack> results;
  final bool isLoading;
  final String? error;
  final String sourceFilter; // 'all', 'deezer', 'youtube'

  const SearchState({
    this.results = const [],
    this.isLoading = false,
    this.error,
    this.sourceFilter = 'all',
  });

  SearchState copyWith({
    List<SonanceTrack>? results,
    bool? isLoading,
    String? error,
    String? sourceFilter,
  }) {
    return SearchState(
      results: results ?? this.results,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      sourceFilter: sourceFilter ?? this.sourceFilter,
    );
  }
}

class SearchNotifier extends StateNotifier<SearchState> {
  SearchNotifier() : super(const SearchState());

  final _yt = YoutubeExplode();

  Future<void> search(String query, {String? source}) async {
    if (query.trim().isEmpty) return;
    state = state.copyWith(isLoading: true, error: null);

    final effectiveSource = source ?? state.sourceFilter;
    final results = <SonanceTrack>[];

    try {
      // 1. Search Deezer Catalog
      if (effectiveSource == 'all' || effectiveSource == 'deezer') {
        final deezerUri = Uri.https('api.deezer.com', '/search', {'q': query, 'limit': '20'});
        final res = await http.get(deezerUri).timeout(const Duration(seconds: 6));
        if (res.statusCode == 200) {
          final data = jsonDecode(res.body)['data'] as List<dynamic>? ?? [];
          for (final item in data) {
            results.add(SonanceTrack(
              id: 'deezer_${item['id']}',
              title: item['title_short'] ?? item['title'] ?? 'Unknown',
              artist: item['artist']?['name'] ?? 'Unknown Artist',
              album: item['album']?['title'] ?? 'Single',
              duration: Duration(seconds: item['duration'] as int? ?? 0),
              coverUrl: item['album']?['cover_medium'] ?? item['album']?['cover_big'],
              streamUrl: item['preview'],
              source: 'Deezer',
              qualityBadge: 'FLAC / 320k',
              isLossless: true,
            ));
          }
        }
      }

      // 2. Search YouTube Fallback via youtube_explode_dart
      if (effectiveSource == 'all' || effectiveSource == 'youtube' || results.length < 5) {
        final ytResults = await _yt.search.search(query);
        for (final video in ytResults.take(15)) {
          results.add(SonanceTrack(
            id: 'yt_${video.id.value}',
            title: video.title,
            artist: video.author,
            album: 'Single',
            duration: video.duration ?? Duration.zero,
            coverUrl: video.thumbnails.highResUrl,
            streamUrl: 'https://www.youtube.com/watch?v=${video.id.value}',
            source: 'YouTube',
            qualityBadge: 'HQ Audio',
            isLossless: false,
          ));
        }
      }

      state = state.copyWith(results: results, isLoading: false);
    } catch (e) {
      state = state.copyWith(error: e.toString(), isLoading: false);
    }
  }

  void setSourceFilter(String source) {
    state = state.copyWith(sourceFilter: source);
  }
}

final searchProvider = StateNotifierProvider<SearchNotifier, SearchState>((ref) {
  return SearchNotifier();
});
