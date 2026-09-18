import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/theme_provider.dart';
import '../../core/services/update_service.dart';
import '../../core/services/discord_rpc_service.dart';
import '../../features/auth/auth_provider.dart';
import '../../features/player/equalizer_provider.dart';
import 'equalizer_view.dart';

class SettingsView extends ConsumerStatefulWidget {
  const SettingsView({super.key});

  @override
  ConsumerState<SettingsView> createState() => _SettingsViewState();
}

class _SettingsViewState extends ConsumerState<SettingsView> {
  late TextEditingController _deezerArlCtrl;
  late TextEditingController _qobuzIdCtrl;
  late TextEditingController _qobuzTokenCtrl;
  late TextEditingController _qobuzAppIdCtrl;
  late TextEditingController _qobuzAppSecretCtrl;
  late TextEditingController _spotifyClientCtrl;
  late TextEditingController _spotifySecretCtrl;
  bool _discordRpcEnabled = true;

  @override
  void initState() {
    super.initState();
    final auth = ref.read(authProvider);
    _deezerArlCtrl = TextEditingController(text: auth.deezerArl);
    _qobuzIdCtrl = TextEditingController(text: auth.qobuzId);
    _qobuzTokenCtrl = TextEditingController(text: auth.qobuzToken);
    _qobuzAppIdCtrl = TextEditingController(text: auth.qobuzAppId);
    _qobuzAppSecretCtrl = TextEditingController(text: auth.qobuzAppSecret);
    _spotifyClientCtrl = TextEditingController(text: auth.spotifyClientId);
    _spotifySecretCtrl = TextEditingController(text: auth.spotifyClientSecret);
    _discordRpcEnabled = discordRpcService.isEnabled;
  }

  @override
  void dispose() {
    _deezerArlCtrl.dispose();
    _qobuzIdCtrl.dispose();
    _qobuzTokenCtrl.dispose();
    _qobuzAppIdCtrl.dispose();
    _qobuzAppSecretCtrl.dispose();
    _spotifyClientCtrl.dispose();
    _spotifySecretCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);
    final themeMode = ref.watch(themeProvider);
    final eq = ref.watch(equalizerProvider);

    return Scaffold(
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 860),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Settings',
                  style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Appearance, DSP Audio Equalizer, and Multi-Source Streaming Credentials.',
                  style: TextStyle(fontSize: 13, color: Colors.grey),
                ),
                const SizedBox(height: 24),

                // Appearance Card
                _buildCard(
                  title: 'Appearance & Theme',
                  subtitle: 'Choose between Slate Dark, Crisp Light, or System default theme.',
                  status: themeMode == ThemeMode.dark
                      ? 'Dark'
                      : themeMode == ThemeMode.light
                          ? 'Light'
                          : 'System',
                  isLoggedIn: true,
                  children: [
                    Row(
                      children: [
                        _buildThemeOption(
                          context,
                          label: 'Slate Dark',
                          icon: Icons.dark_mode_rounded,
                          isSelected: themeMode == ThemeMode.dark,
                          onTap: () => ref
                              .read(themeProvider.notifier)
                              .setTheme(ThemeMode.dark),
                        ),
                        const SizedBox(width: 12),
                        _buildThemeOption(
                          context,
                          label: 'Crisp Light',
                          icon: Icons.light_mode_rounded,
                          isSelected: themeMode == ThemeMode.light,
                          onTap: () => ref
                              .read(themeProvider.notifier)
                              .setTheme(ThemeMode.light),
                        ),
                        const SizedBox(width: 12),
                        _buildThemeOption(
                          context,
                          label: 'System Sync',
                          icon: Icons.brightness_auto_rounded,
                          isSelected: themeMode == ThemeMode.system,
                          onTap: () => ref
                              .read(themeProvider.notifier)
                              .setTheme(ThemeMode.system),
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // Studio Equalizer Card
                _buildCard(
                  title: '10-Band Studio Hardware Equalizer',
                  subtitle: 'Audiophile grade biquad peaking filters (32 Hz - 16 kHz) and preamp stage.',
                  status: eq.isEnabled ? 'Active (${eq.currentPreset})' : 'Bypassed',
                  isLoggedIn: eq.isEnabled,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Preset: ${eq.currentPreset}',
                              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              'Master EQ is ${eq.isEnabled ? "ON" : "OFF"}. Preamp: ${eq.preamp >= 0 ? "+" : ""}${eq.preamp.toStringAsFixed(1)} dB',
                              style: TextStyle(
                                fontSize: 12,
                                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                              ),
                            ),
                          ],
                        ),
                        ElevatedButton.icon(
                          icon: const Icon(Icons.tune_rounded, size: 18),
                          label: const Text('Open Equalizer Rack'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: SonanceTheme.emerald,
                            foregroundColor: Colors.white,
                          ),
                          onPressed: () {
                            showDialog(
                              context: context,
                              builder: (_) => const EqualizerDialog(),
                            );
                          },
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // Native Engine & Low-RAM Architecture
                _buildCard(
                  title: 'Native Low-RAM Engine',
                  subtitle: 'Pure Flutter native AOT compilation with zero WebView2/Chromium runtime.',
                  status: 'Active (~40-80 MB)',
                  isLoggedIn: true,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: SonanceTheme.emerald.withOpacity(0.12),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: const Icon(Icons.speed_rounded, color: SonanceTheme.emerald, size: 24),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Text(
                            'Sonance runs as pure native code without browser runtimes, saving 80-90% of system memory compared to Electron/WebView2.',
                            style: TextStyle(
                              fontSize: 12,
                              color: Theme.of(context).colorScheme.onSurface.withOpacity(0.75),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // Discord Rich Presence Card
                _buildCard(
                  title: 'Discord Rich Presence',
                  subtitle: 'Show the currently playing track and album art on your Discord profile.',
                  status: _discordRpcEnabled ? 'Enabled' : 'Disabled',
                  isLoggedIn: _discordRpcEnabled,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Broadcast "Listening to Sonance" status to Discord'),
                        Switch(
                          value: _discordRpcEnabled,
                          activeColor: SonanceTheme.emerald,
                          onChanged: (val) {
                            setState(() => _discordRpcEnabled = val);
                            discordRpcService.isEnabled = val;
                          },
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // Deezer Card
                _buildCard(
                  title: 'Deezer',
                  subtitle: 'Sign into Deezer using your Deezer ARL cookie for direct FLAC & 320 kbps MP3.',
                  status: auth.isDeezerLoggedIn ? 'Logged In' : 'Not Logged In',
                  isLoggedIn: auth.isDeezerLoggedIn,
                  children: [
                    TextField(
                      controller: _deezerArlCtrl,
                      obscureText: true,
                      decoration: const InputDecoration(
                        labelText: 'Deezer ARL',
                        hintText: 'Enter your 192-character Deezer ARL token...',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Align(
                      alignment: Alignment.centerRight,
                      child: ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Theme.of(context).colorScheme.primary,
                          foregroundColor: Colors.white,
                        ),
                        onPressed: () {
                          ref.read(authProvider.notifier).updateDeezer(_deezerArlCtrl.text);
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Deezer ARL saved!')),
                          );
                        },
                        child: const Text('Save ARL', style: TextStyle(fontWeight: FontWeight.bold)),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // Qobuz Card
                _buildCard(
                  title: 'Qobuz Hi-Res (24-Bit / 192 kHz)',
                  subtitle: 'Connect your Qobuz account for Studio Master lossless streams and downloads.',
                  status: auth.isQobuzLoggedIn ? 'Logged In' : 'Not Logged In',
                  isLoggedIn: auth.isQobuzLoggedIn,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _qobuzIdCtrl,
                            decoration: const InputDecoration(labelText: 'User ID', border: OutlineInputBorder()),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextField(
                            controller: _qobuzTokenCtrl,
                            obscureText: true,
                            decoration: const InputDecoration(labelText: 'User Auth Token', border: OutlineInputBorder()),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Align(
                      alignment: Alignment.centerRight,
                      child: ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Theme.of(context).colorScheme.primary,
                          foregroundColor: Colors.white,
                        ),
                        onPressed: () {
                          ref.read(authProvider.notifier).updateQobuz(
                                id: _qobuzIdCtrl.text,
                                token: _qobuzTokenCtrl.text,
                                appId: _qobuzAppIdCtrl.text,
                                appSecret: _qobuzAppSecretCtrl.text,
                              );
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Qobuz credentials saved!')),
                          );
                        },
                        child: const Text('Save Credentials', style: TextStyle(fontWeight: FontWeight.bold)),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // Spotify Card
                _buildCard(
                  title: 'Spotify Integration',
                  subtitle: 'Spotify Developer API Client ID & Secret for high-volume playlist sync.',
                  status: auth.isSpotifyConfigured ? 'Configured' : 'Public Scraper Fallback',
                  isLoggedIn: auth.isSpotifyConfigured,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _spotifyClientCtrl,
                            decoration: const InputDecoration(labelText: 'Client ID', border: OutlineInputBorder()),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextField(
                            controller: _spotifySecretCtrl,
                            obscureText: true,
                            decoration: const InputDecoration(labelText: 'Client Secret', border: OutlineInputBorder()),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    const Text('Redirect URI: http://127.0.0.1:5543/callback', style: TextStyle(fontSize: 11, color: Colors.grey)),
                    const SizedBox(height: 12),
                    Align(
                      alignment: Alignment.centerRight,
                      child: ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Theme.of(context).colorScheme.primary,
                          foregroundColor: Colors.white,
                        ),
                        onPressed: () {
                          ref.read(authProvider.notifier).updateSpotify(
                                clientId: _spotifyClientCtrl.text,
                                clientSecret: _spotifySecretCtrl.text,
                              );
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Spotify credentials saved!')),
                          );
                        },
                        child: const Text('Save Changes', style: TextStyle(fontWeight: FontWeight.bold)),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // Updates & About Card
                _buildCard(
                  title: 'Sonance v4.0.0',
                  subtitle: 'The ultimate unified music suite — GPLv3 with Commons Clause by Sandeep Khadka.',
                  status: 'Latest',
                  isLoggedIn: true,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Check GitHub releases for updates and new features.'),
                        ElevatedButton.icon(
                          icon: const Icon(Icons.system_update_alt, size: 16),
                          label: const Text('Check for Updates'),
                          onPressed: () async {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('Checking for updates...')),
                            );
                            final info = await UpdateService.checkForUpdates();
                            if (!context.mounted) return;

                            if (info.updateAvailable) {
                              showDialog(
                                context: context,
                                builder: (ctx) => AlertDialog(
                                  title: Text('New Version Available: v${info.latestVersion}'),
                                  content: Column(
                                    mainAxisSize: MainAxisSize.min,
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text('Current version: v${info.currentVersion}'),
                                      const SizedBox(height: 10),
                                      const Text('Changelog:', style: TextStyle(fontWeight: FontWeight.bold)),
                                      Text(info.changelog, style: const TextStyle(fontSize: 12, color: Colors.grey)),
                                    ],
                                  ),
                                  actions: [
                                    TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Later')),
                                    ElevatedButton(
                                      style: ElevatedButton.styleFrom(
                                        backgroundColor: Theme.of(context).colorScheme.primary,
                                        foregroundColor: Colors.white,
                                      ),
                                      onPressed: () {
                                        Navigator.pop(ctx);
                                        if (info.downloadUrl != null) {
                                          UpdateService.downloadAndInstallUpdate(
                                            info.downloadUrl!,
                                            info.expectedSha256,
                                            (pct, msg) {
                                              ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
                                            },
                                          );
                                        }
                                      },
                                      child: const Text('Update Now', style: TextStyle(fontWeight: FontWeight.bold)),
                                    ),
                                  ],
                                ),
                              );
                            } else {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('You are on the latest version of Sonance!')),
                              );
                            }
                          },
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildThemeOption(
    BuildContext context, {
    required String label,
    required IconData icon,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 12),
          decoration: BoxDecoration(
            color: isSelected
                ? SonanceTheme.emerald.withOpacity(0.12)
                : Theme.of(context).colorScheme.surface,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: isSelected
                  ? SonanceTheme.emerald
                  : Theme.of(context).colorScheme.outline,
              width: isSelected ? 2 : 1,
            ),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                icon,
                size: 20,
                color: isSelected ? SonanceTheme.emerald : Colors.grey,
              ),
              const SizedBox(width: 8),
              Text(
                label,
                style: TextStyle(
                  fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                  color: isSelected ? SonanceTheme.emerald : null,
                  fontSize: 13,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCard({
    required String title,
    required String subtitle,
    required String status,
    required bool isLoggedIn,
    required List<Widget> children,
  }) {
    return Builder(
      builder: (context) {
        final theme = Theme.of(context);
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                        const SizedBox(height: 2),
                        Text(subtitle, style: TextStyle(fontSize: 11, color: theme.colorScheme.onSurface.withOpacity(0.6))),
                      ],
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: isLoggedIn ? theme.colorScheme.primary.withOpacity(0.12) : theme.colorScheme.outlineVariant.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: isLoggedIn ? theme.colorScheme.primary.withOpacity(0.4) : theme.colorScheme.outlineVariant),
                      ),
                      child: Text(
                        status,
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: isLoggedIn ? theme.colorScheme.primary : theme.colorScheme.onSurface.withOpacity(0.6),
                        ),
                      ),
                    ),
                  ],
                ),
                const Divider(height: 24),
                ...children,
              ],
            ),
          ),
        );
      },
    );
  }
}
