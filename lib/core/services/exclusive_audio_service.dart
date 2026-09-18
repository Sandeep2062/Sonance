import 'dart:io';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

enum AudioOutputMode {
  standard,
  aaudioExclusive,
  usbDirect,
  wasapiExclusive,
  asio,
}

class UsbDacDevice {
  final String deviceName;
  final int deviceId;
  final int vendorId;
  final int productId;
  final bool hasPermission;

  const UsbDacDevice({
    required this.deviceName,
    required this.deviceId,
    required this.vendorId,
    required this.productId,
    required this.hasPermission,
  });

  factory UsbDacDevice.fromMap(Map<dynamic, dynamic> map) {
    return UsbDacDevice(
      deviceName: map['deviceName'] as String? ?? 'USB Audio DAC',
      deviceId: map['deviceId'] as int? ?? 0,
      vendorId: map['vendorId'] as int? ?? 0,
      productId: map['productId'] as int? ?? 0,
      hasPermission: map['hasPermission'] as bool? ?? false,
    );
  }
}

class ExclusiveAudioService {
  static const MethodChannel _channel = MethodChannel('sonance/exclusive_audio');

  /// Fetches available platform audio output modes
  Future<List<Map<String, dynamic>>> getAudioOutputModes() async {
    if (!Platform.isAndroid) return [];
    try {
      final List<dynamic>? res = await _channel.invokeMethod('getAudioOutputModes');
      if (res != null) {
        return res.map((e) => Map<String, dynamic>.from(e as Map)).toList();
      }
    } catch (_) {}
    return [];
  }

  /// Scans for connected USB Audio Class (UAC 1.0/2.0) DACs on Android
  Future<List<UsbDacDevice>> getConnectedUsbDacs() async {
    if (!Platform.isAndroid) return [];
    try {
      final List<dynamic>? res = await _channel.invokeMethod('getConnectedUsbDacs');
      if (res != null) {
        return res.map((e) => UsbDacDevice.fromMap(e as Map)).toList();
      }
    } catch (_) {}
    return [];
  }

  /// Requests USB Host permission for bit-perfect direct DAC access
  Future<bool> requestUsbDacPermission(int deviceId) async {
    if (!Platform.isAndroid) return false;
    try {
      final bool? res = await _channel.invokeMethod('requestUsbDacPermission', {
        'deviceId': deviceId,
      });
      return res ?? false;
    } catch (_) {
      return false;
    }
  }

  /// Sets active output driver mode
  Future<void> setAudioOutputMode(AudioOutputMode mode) async {
    if (!Platform.isAndroid) return;
    String modeString;
    switch (mode) {
      case AudioOutputMode.aaudioExclusive:
        modeString = 'aaudio_exclusive';
        break;
      case AudioOutputMode.usbDirect:
        modeString = 'usb_direct';
        break;
      case AudioOutputMode.wasapiExclusive:
        modeString = 'wasapi_exclusive';
        break;
      case AudioOutputMode.asio:
        modeString = 'asio';
        break;
      case AudioOutputMode.standard:
      default:
        modeString = 'standard';
        break;
    }
    try {
      await _channel.invokeMethod('setAudioOutputMode', {'mode': modeString});
    } catch (_) {}
  }

  /// Queries real-time exclusive status
  Future<Map<String, dynamic>> getExclusiveStatus() async {
    if (!Platform.isAndroid) return {'isBitPerfect': false, 'platform': 'other'};
    try {
      final Map<dynamic, dynamic>? res = await _channel.invokeMethod('getExclusiveStatus');
      if (res != null) {
        return Map<String, dynamic>.from(res);
      }
    } catch (_) {}
    return {'isBitPerfect': false};
  }
}

final exclusiveAudioServiceProvider = Provider<ExclusiveAudioService>((ref) {
  return ExclusiveAudioService();
});

final exclusiveAudioStatusProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final service = ref.watch(exclusiveAudioServiceProvider);
  return service.getExclusiveStatus();
});
