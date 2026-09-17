import 'package:flutter/material.dart';

class SonanceTheme {
  static const Color emerald = Color(0xFF10B981);
  static const Color darkBg = Color(0xFF0C0E14);
  static const Color surfaceColor = Color(0xFF141722);
  static const Color cardColor = Color(0xFF1A1E2D);
  static const Color borderColor = Color(0x14FFFFFF);

  static ThemeData darkTheme = ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    scaffoldBackgroundColor: darkBg,
    colorScheme: const ColorScheme.dark(
      primary: emerald,
      secondary: Color(0xFF0D9488),
      surface: surfaceColor,
      onSurface: Color(0xFFF8FAFC),
      background: darkBg,
      onBackground: Color(0xFFF8FAFC),
      error: Color(0xFFF43F5E),
    ),
    cardTheme: CardTheme(
      color: cardColor,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: borderColor),
      ),
    ),
    navigationRailTheme: const NavigationRailThemeData(
      backgroundColor: Color(0xFF10131C),
      selectedIconTheme: IconThemeData(color: emerald),
      unselectedIconTheme: IconThemeData(color: Color(0xFF64748B)),
      indicatorColor: Color(0x1F10B981),
    ),
  );
}
