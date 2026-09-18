import 'package:flutter/material.dart';

class SonanceTheme {
  // Brand Accents
  static const Color emerald = Color(0xFF10B981);
  static const Color emeraldDark = Color(0xFF059669);

  // Slate Dark Palette (Solid neutrals, no tacky purple glows)
  static const Color darkBg = Color(0xFF0B0E14);
  static const Color darkSurface = Color(0xFF111520);
  static const Color darkCard = Color(0xFF161B26);
  static const Color darkBorder = Color(0xFF1E293B);
  static const Color darkTextMain = Color(0xFFF1F5F9);
  static const Color darkTextMuted = Color(0xFF94A3B8);

  // Slate Light Palette (Clean, crisp, high-contrast)
  static const Color lightBg = Color(0xFFF8FAFC);
  static const Color lightSurface = Color(0xFFFFFFFF);
  static const Color lightCard = Color(0xFFFFFFFF);
  static const Color lightBorder = Color(0xFFE2E8F0);
  static const Color lightTextMain = Color(0xFF0F172A);
  static const Color lightTextMuted = Color(0xFF64748B);

  // Backward-compatible aliases
  static const Color surfaceColor = darkSurface;
  static const Color cardColor = darkCard;
  static const Color borderColor = darkBorder;

  static ThemeData darkTheme = ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    scaffoldBackgroundColor: darkBg,
    colorScheme: const ColorScheme.dark(
      primary: emerald,
      secondary: Color(0xFF0D9488),
      surface: darkSurface,
      onSurface: darkTextMain,
      outline: darkBorder,
      outlineVariant: Color(0xFF2D3748),
      error: Color(0xFFF43F5E),
    ),
    dividerTheme: const DividerThemeData(
      color: darkBorder,
      thickness: 1,
      space: 1,
    ),
    cardTheme: CardThemeData(
      color: darkCard,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: const BorderSide(color: darkBorder, width: 1),
      ),
    ),
    navigationRailTheme: const NavigationRailThemeData(
      backgroundColor: darkBg,
      selectedIconTheme: IconThemeData(color: emerald),
      unselectedIconTheme: IconThemeData(color: darkTextMuted),
      indicatorColor: Color(0x1F10B981),
      selectedLabelTextStyle: TextStyle(color: emerald, fontWeight: FontWeight.w600, fontSize: 11),
      unselectedLabelTextStyle: TextStyle(color: darkTextMuted, fontSize: 11),
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: darkBg,
      foregroundColor: darkTextMain,
      elevation: 0,
      scrolledUnderElevation: 0,
    ),
  );

  static ThemeData lightTheme = ThemeData(
    useMaterial3: true,
    brightness: Brightness.light,
    scaffoldBackgroundColor: lightBg,
    colorScheme: const ColorScheme.light(
      primary: emeraldDark,
      secondary: Color(0xFF0D9488),
      surface: lightSurface,
      onSurface: lightTextMain,
      outline: lightBorder,
      outlineVariant: Color(0xFFCBD5E1),
      error: Color(0xFFE11D48),
    ),
    dividerTheme: const DividerThemeData(
      color: lightBorder,
      thickness: 1,
      space: 1,
    ),
    cardTheme: CardThemeData(
      color: lightCard,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: const BorderSide(color: lightBorder, width: 1),
      ),
    ),
    navigationRailTheme: const NavigationRailThemeData(
      backgroundColor: lightSurface,
      selectedIconTheme: IconThemeData(color: emeraldDark),
      unselectedIconTheme: IconThemeData(color: lightTextMuted),
      indicatorColor: Color(0x14059669),
      selectedLabelTextStyle: TextStyle(color: emeraldDark, fontWeight: FontWeight.w600, fontSize: 11),
      unselectedLabelTextStyle: TextStyle(color: lightTextMuted, fontSize: 11),
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: lightBg,
      foregroundColor: lightTextMain,
      elevation: 0,
      scrolledUnderElevation: 0,
    ),
  );
}

