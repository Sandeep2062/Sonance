import 'dart:async';
import 'dart:convert';
import 'dart:io';

class ProcessOutput {
  final int exitCode;
  final String stdout;
  final String stderr;
  final bool success;

  const ProcessOutput({
    required this.exitCode,
    required this.stdout,
    required this.stderr,
    required this.success,
  });
}

/// Lightweight service that bridges Flutter to on-demand Python DSP modules.
/// Spawns worker processes that exit immediately after work is done,
/// consuming 0 MB RAM while idle.
class PythonEngineService {
  static final PythonEngineService _instance = PythonEngineService._internal();
  factory PythonEngineService() => _instance;
  PythonEngineService._internal();

  String _cachedPythonPath = '';

  Future<String> getPythonExecutable() async {
    if (_cachedPythonPath.isNotEmpty) return _cachedPythonPath;

    // Check standard locations
    final candidates = [
      'python',
      'python3',
      'py',
      'C:\\Python311\\python.exe',
      'C:\\Python310\\python.exe',
      'C:\\Users\\Sandeep Khadka\\AppData\\Local\\Programs\\Python\\Python311\\python.exe',
      'C:\\Users\\Sandeep Khadka\\AppData\\Local\\Programs\\Python\\Python310\\python.exe',
    ];

    for (final c in candidates) {
      try {
        final res = await Process.run(c, ['--version']);
        if (res.exitCode == 0) {
          _cachedPythonPath = c;
          return c;
        }
      } catch (_) {}
    }

    _cachedPythonPath = 'python';
    return 'python';
  }

  /// Run a sonance.py command asynchronously with live output streaming.
  Stream<String> runStreamingCommand({
    required List<String> args,
    String? workingDirectory,
  }) async* {
    final py = await getPythonExecutable();
    final scriptPath = Platform.isWindows ? 'sonance.py' : './sonance.py';

    Process? process;
    try {
      process = await Process.start(
        py,
        [scriptPath, ...args],
        workingDirectory: workingDirectory,
      );

      final controller = StreamController<String>();

      process.stdout
          .transform(utf8.decoder)
          .listen((data) => controller.add(data));
      process.stderr
          .transform(utf8.decoder)
          .listen((data) => controller.add(data));

      process.exitCode.then((code) {
        controller.add('\n[Process completed with exit code $code]');
        controller.close();
      });

      yield* controller.stream;
    } catch (e) {
      yield 'Error starting Python worker: $e\n';
    }
  }

  /// Run a command and return full output when done.
  Future<ProcessOutput> runCommand({
    required List<String> args,
    String? workingDirectory,
  }) async {
    final py = await getPythonExecutable();
    final scriptPath = Platform.isWindows ? 'sonance.py' : './sonance.py';

    try {
      final res = await Process.run(
        py,
        [scriptPath, ...args],
        workingDirectory: workingDirectory,
      );

      return ProcessOutput(
        exitCode: res.exitCode,
        stdout: res.stdout.toString(),
        stderr: res.stderr.toString(),
        success: res.exitCode == 0,
      );
    } catch (e) {
      return ProcessOutput(
        exitCode: -1,
        stdout: '',
        stderr: e.toString(),
        success: false,
      );
    }
  }

  // --- Specific High-Level DSP Studio Calls ---

  Stream<String> runLibraryDoctor(String folderPath) {
    return runStreamingCommand(args: ['--doctor', folderPath]);
  }

  Stream<String> runTranscoder({
    required String source,
    String? outputDir,
    String format = 'flac',
    String? bitrate,
  }) {
    final args = ['--transcode', source];
    if (outputDir != null) args.add(outputDir);
    args.add(format);
    if (bitrate != null) args.add(bitrate);
    return runStreamingCommand(args: args);
  }

  Future<ProcessOutput> auditAudioFile(String audioFilePath) {
    return runCommand(args: ['--identify', audioFilePath]);
  }

  Future<ProcessOutput> getListeningStats() {
    return runCommand(args: ['--stats']);
  }

  Stream<String> runZenithMaster({
    required String audioFile,
    String? output,
    String profile = 'audiophile_pure_master',
  }) {
    final args = ['--zenith', audioFile];
    if (output != null) {
      args.addAll([output, '--profile', profile]);
    } else {
      args.addAll(['--profile', profile]);
    }
    return runStreamingCommand(args: args);
  }
}

final pythonEngineService = PythonEngineService();
