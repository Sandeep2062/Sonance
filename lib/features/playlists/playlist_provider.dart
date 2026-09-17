import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/models/track.dart';

class PlaylistState {
  final List<SonanceTrack> favorites;
  final Map<String, List<SonanceTrack>> playlists;

  const PlaylistState({
    this.favorites = const [],
    this.playlists = const {},
  });

  PlaylistState copyWith({
    List<SonanceTrack>? favorites,
    Map<String, List<SonanceTrack>>? playlists,
  }) {
    return PlaylistState(
      favorites: favorites ?? this.favorites,
      playlists: playlists ?? this.playlists,
    );
  }
}

class PlaylistNotifier extends StateNotifier<PlaylistState> {
  PlaylistNotifier() : super(const PlaylistState()) {
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final favJson = prefs.getString('user_favorites');
    final plJson = prefs.getString('user_playlists');

    List<SonanceTrack> favs = [];
    if (favJson != null) {
      final list = jsonDecode(favJson) as List<dynamic>;
      favs = list.map((e) => SonanceTrack.fromJson(e as Map<String, dynamic>)).toList();
    }

    Map<String, List<SonanceTrack>> pls = {};
    if (plJson != null) {
      final map = jsonDecode(plJson) as Map<String, dynamic>;
      map.forEach((k, v) {
        pls[k] = (v as List<dynamic>).map((e) => SonanceTrack.fromJson(e as Map<String, dynamic>)).toList();
      });
    }

    state = PlaylistState(favorites: favs, playlists: pls);
  }

  Future<bool> toggleFavorite(SonanceTrack track) async {
    final isFav = state.favorites.any((t) => t.id == track.id);
    final updated = isFav
        ? state.favorites.where((t) => t.id != track.id).toList()
        : [...state.favorites, track];

    state = state.copyWith(favorites: updated);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('user_favorites', jsonEncode(updated.map((t) => t.toJson()).toList()));
    return !isFav;
  }

  Future<void> createPlaylist(String name) async {
    if (state.playlists.containsKey(name)) return;
    final updated = {...state.playlists, name: <SonanceTrack>[]};
    state = state.copyWith(playlists: updated);
    _persistPlaylists();
  }

  Future<void> addToPlaylist(String name, SonanceTrack track) async {
    final list = state.playlists[name] ?? [];
    if (list.any((t) => t.id == track.id)) return;
    final updated = {
      ...state.playlists,
      name: [...list, track],
    };
    state = state.copyWith(playlists: updated);
    _persistPlaylists();
  }

  Future<void> _persistPlaylists() async {
    final prefs = await SharedPreferences.getInstance();
    final encoded = state.playlists.map((k, v) => MapEntry(k, v.map((t) => t.toJson()).toList()));
    await prefs.setString('user_playlists', jsonEncode(encoded));
  }
}

final playlistProvider = StateNotifierProvider<PlaylistNotifier, PlaylistState>((ref) {
  return PlaylistNotifier();
});
