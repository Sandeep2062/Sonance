/// 10-Band Equalizer configuration and presets.
class EqualizerPreset {
  final String name;
  final List<double> gains; // Gains in dB for 32, 64, 125, 250, 500, 1k, 2k, 4k, 8k, 16k Hz

  const EqualizerPreset(this.name, this.gains);
}

class EqualizerService {
  static const List<int> frequencies = [32, 64, 125, 250, 500, 1000, 2000, 4000, 8000, 16000];

  static const List<EqualizerPreset> presets = [
    EqualizerPreset('Flat', [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
    EqualizerPreset('Bass Boost', [6, 5, 4, 2, 0, 0, 0, 0, 1, 2]),
    EqualizerPreset('Rock', [4, 3, 2, 0, -1, 1, 3, 4, 4, 3]),
    EqualizerPreset('Pop', [-1, 1, 3, 4, 3, 0, -1, -1, 2, 3]),
    EqualizerPreset('Jazz', [3, 2, 1, 2, -1, -1, 0, 1, 2, 3]),
    EqualizerPreset('Electronic', [4, 4, 2, 0, -2, 2, 1, 2, 4, 4]),
    EqualizerPreset('Classical', [4, 3, 2, 2, -1, -1, 0, 2, 3, 3]),
    EqualizerPreset('Vocal Booster', [-2, -2, -1, 1, 3, 4, 3, 1, 0, -1]),
  ];

  static EqualizerPreset getPreset(String name) {
    return presets.firstWhere(
      (p) => p.name.toLowerCase() == name.toLowerCase(),
      orElse: () => presets.first,
    );
  }
}
