import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/services/equalizer_service.dart';

class EqualizerState {
  final bool isEnabled;
  final String currentPreset;
  final List<double> gains; // 10 bands: 32, 64, 125, 250, 500, 1k, 2k, 4k, 8k, 16k Hz
  final double preamp;

  const EqualizerState({
    this.isEnabled = true,
    this.currentPreset = 'Flat',
    this.gains = const [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    this.preamp = 0.0,
  });

  EqualizerState copyWith({
    bool? isEnabled,
    String? currentPreset,
    List<double>? gains,
    double? preamp,
  }) {
    return EqualizerState(
      isEnabled: isEnabled ?? this.isEnabled,
      currentPreset: currentPreset ?? this.currentPreset,
      gains: gains ?? this.gains,
      preamp: preamp ?? this.preamp,
    );
  }
}

class EqualizerNotifier extends StateNotifier<EqualizerState> {
  EqualizerNotifier() : super(const EqualizerState()) {
    _loadFromStorage();
  }

  static const _keyEnabled = 'sonance_eq_enabled';
  static const _keyPreset = 'sonance_eq_preset';
  static const _keyGains = 'sonance_eq_gains';
  static const _keyPreamp = 'sonance_eq_preamp';

  Future<void> _loadFromStorage() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final enabled = prefs.getBool(_keyEnabled) ?? true;
      final preset = prefs.getString(_keyPreset) ?? 'Flat';
      final preamp = prefs.getDouble(_keyPreamp) ?? 0.0;
      final gainsJson = prefs.getString(_keyGains);

      List<double> gains = const [0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
      if (gainsJson != null) {
        final decoded = (jsonDecode(gainsJson) as List<dynamic>)
            .map((e) => (e as num).toDouble())
            .toList();
        if (decoded.length == 10) {
          gains = decoded;
        }
      } else {
        gains = List<double>.from(EqualizerService.getPreset(preset).gains);
      }

      state = EqualizerState(
        isEnabled: enabled,
        currentPreset: preset,
        gains: gains,
        preamp: preamp,
      );
    } catch (_) {}
  }

  Future<void> setBandGain(int index, double gainDb) async {
    if (index < 0 || index >= state.gains.length) return;
    final clamped = gainDb.clamp(-12.0, 12.0);
    final updated = List<double>.from(state.gains);
    updated[index] = clamped;

    // Check if it still matches current preset
    String newPreset = state.currentPreset;
    final presetObj = EqualizerService.getPreset(state.currentPreset);
    bool matches = true;
    for (int i = 0; i < 10; i++) {
      if ((updated[i] - presetObj.gains[i]).abs() > 0.1) {
        matches = false;
        break;
      }
    }
    if (!matches) {
      newPreset = 'Custom';
    }

    state = state.copyWith(gains: updated, currentPreset: newPreset);
    _save();
  }

  Future<void> selectPreset(String presetName) async {
    final preset = EqualizerService.getPreset(presetName);
    state = state.copyWith(
      currentPreset: preset.name,
      gains: List<double>.from(preset.gains),
    );
    _save();
  }

  Future<void> toggleEnabled() async {
    state = state.copyWith(isEnabled: !state.isEnabled);
    _save();
  }

  Future<void> setPreamp(double val) async {
    state = state.copyWith(preamp: val.clamp(-12.0, 12.0));
    _save();
  }

  Future<void> resetToFlat() async {
    await selectPreset('Flat');
  }

  Future<void> _save() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(_keyEnabled, state.isEnabled);
      await prefs.setString(_keyPreset, state.currentPreset);
      await prefs.setDouble(_keyPreamp, state.preamp);
      await prefs.setString(_keyGains, jsonEncode(state.gains));
    } catch (_) {}
  }
}

final equalizerProvider =
    StateNotifierProvider<EqualizerNotifier, EqualizerState>((ref) {
  return EqualizerNotifier();
});
