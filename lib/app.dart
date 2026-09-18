import 'package:flutter/material.dart';
import 'core/theme/app_theme.dart';
import 'ui/home_screen.dart';

class SonanceApp extends StatelessWidget {
  const SonanceApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Sonance',
      debugShowCheckedModeBanner: false,
      theme: SonanceTheme.lightTheme,
      darkTheme: SonanceTheme.darkTheme,
      themeMode: ThemeMode.system,
      home: const HomeScreen(),
    );
  }
}
