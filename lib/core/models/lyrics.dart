/// Single timestamped line in a synced LRC file.
class LyricLine {
  final Duration? timestamp;
  final String text;

  const LyricLine({
    this.timestamp,
    required this.text,
  });

  bool get isSynced => timestamp != null;
}

/// Full parsed lyrics document with sync state.
class SyncedLyrics {
  final List<LyricLine> lines;
  final String state; // 'synced', 'plain', 'none'
  final String? provider; // 'LRCLIB', 'Genius', 'Musixmatch'

  const SyncedLyrics({
    required this.lines,
    this.state = 'none',
    this.provider,
  });

  bool get hasLyrics => lines.isNotEmpty;
  bool get isSynced => state == 'synced';

  /// Finds the active line index given current playback position.
  int getActiveLineIndex(Duration currentPosition) {
    if (lines.isEmpty) return -1;

    int activeIdx = -1;
    for (int i = 0; i < lines.length; i++) {
      final ts = lines[i].timestamp;
      if (ts != null) {
        if (ts <= currentPosition + const Duration(milliseconds: 200)) {
          activeIdx = i;
        } else {
          break;
        }
      }
    }
    return activeIdx;
  }

  /// Parses raw LRC text into a SyncedLyrics object.
  static SyncedLyrics parse(String rawContent, {String? provider}) {
    if (rawContent.trim().isEmpty) {
      return const SyncedLyrics(lines: [], state: 'none');
    }

    final tsRegex = RegExp(r'\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]');
    final lines = <LyricLine>[];
    int syncedCount = 0;

    for (final rawLine in rawContent.split('\n')) {
      final line = rawLine.trim();
      if (line.isEmpty) continue;

      // Skip metadata headers
      if (line.startsWith('[ar:') ||
          line.startsWith('[ti:') ||
          line.startsWith('[al:') ||
          line.startsWith('[by:')) {
        continue;
      }

      final match = tsRegex.firstMatch(line);
      if (match != null) {
        final mins = int.parse(match.group(1)!);
        final secs = int.parse(match.group(2)!);
        final ms = match.group(3) != null
            ? (double.parse('0.${match.group(3)!}') * 1000).toInt()
            : 0;

        final duration = Duration(minutes: mins, seconds: secs, milliseconds: ms);
        final text = line.replaceAll(match.group(0)!, '').trim();

        lines.add(LyricLine(timestamp: duration, text: text));
        syncedCount++;
      } else {
        lines.add(LyricLine(text: line));
      }
    }

    final state = syncedCount >= 3 ? 'synced' : (lines.isNotEmpty ? 'plain' : 'none');
    return SyncedLyrics(lines: lines, state: state, provider: provider);
  }
}
