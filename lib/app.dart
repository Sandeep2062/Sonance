import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/theme/app_theme.dart';
import 'core/theme/theme_provider.dart';
import 'ui/home_screen.dart';

class SonanceApp extends ConsumerWidget {
  const SonanceApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final themeMode = ref.watch(themeProvider);

    return MaterialApp(
      title: 'Sonance',
      debugShowCheckedModeBanner: false,
      theme: SonanceTheme.lightTheme,
      darkTheme: SonanceTheme.darkTheme,
      themeMode: themeMode,
      home: const HomeScreen(),
    );
  }
}

