import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../features/player/player_provider.dart';

class LyricsView extends ConsumerStatefulWidget {
  const LyricsView({super.key});

  @override
  ConsumerState<LyricsView> createState() => _LyricsViewState();
}

class _LyricsViewState extends ConsumerState<LyricsView> {
  final _scrollController = ScrollController();
  int _lastActiveIndex = -1;

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToActive(int index) {
    if (index != _lastActiveIndex && _scrollController.hasClients) {
      _lastActiveIndex = index;
      final target = index * 48.0;
      _scrollController.animateTo(
        target,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final player = ref.watch(playerProvider);
    final lyrics = player.lyrics;

    if (player.activeLyricIndex >= 0) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _scrollToActive(player.activeLyricIndex);
      });
    }

    if (player.currentTrack == null) {
      return const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.music_note, size: 64, color: Colors.grey),
            SizedBox(height: 12),
            Text('No track playing. Play a track to view live synced lyrics.', style: TextStyle(color: Colors.grey)),
          ],
        ),
      );
    }

    if (lyrics == null || !lyrics.hasLyrics) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(color: Theme.of(context).colorScheme.primary),
            const SizedBox(height: 16),
            Text('Fetching verified synced lyrics for "${player.currentTrack!.title}"...', style: TextStyle(color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6))),
          ],
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(player.currentTrack!.title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            Text('${player.currentTrack!.artist} · ${lyrics.provider ?? "LRCLIB"}', style: TextStyle(fontSize: 11, color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6))),
          ],
        ),
        backgroundColor: Colors.transparent,
      ),
      body: ListView.builder(
        controller: _scrollController,
        padding: const EdgeInsets.symmetric(vertical: 200, horizontal: 32),
        itemCount: lyrics.lines.length,
        itemBuilder: (context, idx) {
          final line = lyrics.lines[idx];
          final isActive = idx == player.activeLyricIndex;

          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 10),
            child: AnimatedDefaultTextStyle(
              duration: const Duration(milliseconds: 200),
              style: TextStyle(
                fontSize: isActive ? 24 : 18,
                fontWeight: isActive ? FontWeight.w800 : FontWeight.normal,
                color: isActive ? Theme.of(context).colorScheme.primary : Theme.of(context).colorScheme.onSurface.withOpacity(0.35),
                height: 1.4,
              ),
              child: Text(
                line.text,
                textAlign: TextAlign.center,
              ),
            ),
          );
        },
      ),
    );
  }
}
