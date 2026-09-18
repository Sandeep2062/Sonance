import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/services/equalizer_service.dart';
import '../../core/theme/app_theme.dart';
import '../../features/player/equalizer_provider.dart';

class EqualizerDialog extends ConsumerWidget {
  const EqualizerDialog({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final eq = ref.watch(equalizerProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Dialog(
      backgroundColor: isDark ? SonanceTheme.darkSurface : SonanceTheme.lightSurface,
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(
          color: Theme.of(context).colorScheme.outline,
          width: 1,
        ),
      ),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 820, maxHeight: 600),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Row(
                children: [
                  Container(
                    width: 38,
                    height: 38,
                    decoration: BoxDecoration(
                      color: eq.isEnabled
                          ? SonanceTheme.emerald.withOpacity(0.15)
                          : Colors.grey.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Center(
                      child: Icon(
                        Icons.tune_rounded,
                        color: eq.isEnabled ? SonanceTheme.emerald : Colors.grey,
                        size: 20,
                      ),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          '10-Band Studio Hardware Equalizer',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        Text(
                          'Audiophile DSP with 32 Hz - 16 kHz peaking filters',
                          style: TextStyle(
                            fontSize: 12,
                            color: Theme.of(context)
                                .colorScheme
                                .onSurface
                                .withOpacity(0.6),
                          ),
                        ),
                      ],
                    ),
                  ),
                  // Master Bypass Switch
                  Row(
                    children: [
                      Text(
                        eq.isEnabled ? 'ACTIVE' : 'BYPASS',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: eq.isEnabled ? SonanceTheme.emerald : Colors.grey,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Switch(
                        value: eq.isEnabled,
                        activeColor: SonanceTheme.emerald,
                        onChanged: (_) =>
                            ref.read(equalizerProvider.notifier).toggleEnabled(),
                      ),
                    ],
                  ),
                  const SizedBox(width: 12),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
              const Divider(height: 24),

              // Presets & Preamp bar
              Row(
                children: [
                  const Text('Preset:', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                  const SizedBox(width: 10),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10),
                    decoration: BoxDecoration(
                      border: Border.write(
                        top: BorderSide(color: Theme.of(context).colorScheme.outline),
                        bottom: BorderSide(color: Theme.of(context).colorScheme.outline),
                        left: BorderSide(color: Theme.of(context).colorScheme.outline),
                        right: BorderSide(color: Theme.of(context).colorScheme.outline),
                      ),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<String>(
                        value: EqualizerService.presets.any((p) => p.name == eq.currentPreset)
                            ? eq.currentPreset
                            : 'Custom',
                        items: [
                          ...EqualizerService.presets.map(
                            (p) => DropdownMenuItem(
                              value: p.name,
                              child: Text(p.name, style: const TextStyle(fontSize: 13)),
                            ),
                          ),
                          if (!EqualizerService.presets.any((p) => p.name == eq.currentPreset))
                            const DropdownMenuItem(
                              value: 'Custom',
                              child: Text('Custom', style: TextStyle(fontSize: 13)),
                            ),
                        ],
                        onChanged: (name) {
                          if (name != null && name != 'Custom') {
                            ref.read(equalizerProvider.notifier).selectPreset(name);
                          }
                        },
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),
                  TextButton.icon(
                    icon: const Icon(Icons.refresh, size: 16),
                    label: const Text('Flat (0 dB)', style: TextStyle(fontSize: 12)),
                    onPressed: () =>
                        ref.read(equalizerProvider.notifier).resetToFlat(),
                  ),
                  const Spacer(),
                  // Preamp
                  Row(
                    children: [
                      const Text('Preamp:', style: TextStyle(fontSize: 12)),
                      SizedBox(
                        width: 110,
                        child: Slider(
                          value: eq.preamp,
                          min: -12.0,
                          max: 12.0,
                          activeColor: SonanceTheme.emerald,
                          onChanged: eq.isEnabled
                              ? (v) => ref
                                  .read(equalizerProvider.notifier)
                                  .setPreamp(v)
                              : null,
                        ),
                      ),
                      Text(
                        '${eq.preamp >= 0 ? '+' : ''}${eq.preamp.toStringAsFixed(1)} dB',
                        style: const TextStyle(fontSize: 11, fontFamily: 'monospace'),
                      ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // 10-Band Sliders Grid
              Expanded(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  decoration: BoxDecoration(
                    color: isDark ? SonanceTheme.darkBg : const Color(0xFFF1F5F9),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Theme.of(context).colorScheme.outline),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: List.generate(10, (idx) {
                      final freq = EqualizerService.frequencies[idx];
                      final gain = eq.gains[idx];
                      final freqLabel = freq >= 1000 ? '${(freq / 1000).toInt()}k' : '$freq';

                      return _EqualizerBandSlider(
                        index: idx,
                        freqLabel: freqLabel,
                        gain: gain,
                        isEnabled: eq.isEnabled,
                        onChanged: (v) {
                          ref
                              .read(equalizerProvider.notifier)
                              .setBandGain(idx, v);
                        },
                        onDoubleTap: () {
                          ref
                              .read(equalizerProvider.notifier)
                              .setBandGain(idx, 0.0);
                        },
                      );
                    }),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _EqualizerBandSlider extends StatelessWidget {
  final int index;
  final String freqLabel;
  final double gain;
  final bool isEnabled;
  final ValueChanged<double> onChanged;
  final VoidCallback onDoubleTap;

  const _EqualizerBandSlider({
    required this.index,
    required this.freqLabel,
    required this.gain,
    required this.isEnabled,
    required this.onChanged,
    required this.onDoubleTap,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Gain display
        GestureDetector(
          onDoubleTap: onDoubleTap,
          child: Text(
            '${gain >= 0 ? '+' : ''}${gain.toStringAsFixed(1)}',
            style: TextStyle(
              fontSize: 10,
              fontFamily: 'monospace',
              fontWeight: FontWeight.bold,
              color: isEnabled
                  ? (gain > 0.1
                      ? SonanceTheme.emerald
                      : gain < -0.1
                          ? Colors.orangeAccent
                          : Theme.of(context).colorScheme.onSurface.withOpacity(0.6))
                  : Colors.grey,
            ),
          ),
        ),
        const SizedBox(height: 6),
        // Vertical Slider
        Expanded(
          child: RotatedBox(
            quarterTurns: 3,
            child: SliderTheme(
              data: SliderTheme.of(context).copyWith(
                trackHeight: 4,
                thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 7),
                activeTrackColor: isEnabled ? SonanceTheme.emerald : Colors.grey,
                inactiveTrackColor: isEnabled
                    ? SonanceTheme.emerald.withOpacity(0.2)
                    : Colors.grey.withOpacity(0.2),
                thumbColor: isEnabled ? SonanceTheme.emerald : Colors.grey,
              ),
              child: Slider(
                value: gain,
                min: -12.0,
                max: 12.0,
                onChanged: isEnabled ? onChanged : null,
              ),
            ),
          ),
        ),
        const SizedBox(height: 6),
        // Frequency Label
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            borderRadius: BorderRadius.circular(4),
            border: Border.all(
              color: Theme.of(context).colorScheme.outline.withOpacity(0.5),
            ),
          ),
          child: Text(
            freqLabel,
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ],
    );
  }
}
