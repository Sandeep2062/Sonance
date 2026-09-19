import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';

/// Resilient artwork widget supporting network URLs, local files, data URIs, and styled fallbacks.
class SonanceArtwork extends StatelessWidget {
  final String? coverUrl;
  final double? width;
  final double? height;
  final double borderRadius;
  final IconData fallbackIcon;
  final BoxFit fit;

  const SonanceArtwork({
    super.key,
    required this.coverUrl,
    this.width,
    this.height,
    this.borderRadius = 8.0,
    this.fallbackIcon = Icons.music_note,
    this.fit = BoxFit.cover,
  });

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(borderRadius),
      child: SizedBox(
        width: width,
        height: height,
        child: _buildImage(context),
      ),
    );
  }

  Widget _buildImage(BuildContext context) {
    final url = coverUrl?.trim();
    if (url == null || url.isEmpty) {
      return _buildFallback(context);
    }

    // 1. Data URI (Base64 embedded album art)
    if (url.startsWith('data:image/')) {
      try {
        final commaIdx = url.indexOf(',');
        if (commaIdx != -1) {
          final b64Str = url.substring(commaIdx + 1);
          final bytes = base64Decode(b64Str);
          return Image.memory(
            bytes,
            width: width,
            height: height,
            fit: fit,
            errorBuilder: (_, __, ___) => _buildFallback(context),
          );
        }
      } catch (_) {
        return _buildFallback(context);
      }
    }

    // 2. HTTP / HTTPS Network Images
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return Image.network(
        url,
        width: width,
        height: height,
        fit: fit,
        errorBuilder: (_, __, ___) => _buildFallback(context),
      );
    }

    // 3. Local Filesystem Images (e.g. C:\... or file://...)
    try {
      String cleanPath = url;
      if (cleanPath.startsWith('file:///')) {
        cleanPath = Uri.parse(cleanPath).toFilePath();
      } else if (cleanPath.startsWith('file://')) {
        cleanPath = cleanPath.substring(7);
      }

      final file = File(cleanPath);
      if (file.existsSync()) {
        return Image.file(
          file,
          width: width,
          height: height,
          fit: fit,
          errorBuilder: (_, __, ___) => _buildFallback(context),
        );
      }
    } catch (_) {}

    return _buildFallback(context);
  }

  Widget _buildFallback(BuildContext context) {
    return Container(
      width: width,
      height: height,
      color: Theme.of(context).colorScheme.outlineVariant.withOpacity(0.18),
      child: Center(
        child: Icon(
          fallbackIcon,
          size: (width != null && height != null) ? (width! * 0.45).clamp(16.0, 48.0) : 24,
          color: SonanceTheme.emerald.withOpacity(0.65),
        ),
      ),
    );
  }
}
