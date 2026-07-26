# Video Audio Transcriber

A local Python desktop application that separates a video into video-only and
audio-only files, then transcribes the speech into a clean UTF-8 text file using
FFmpeg and faster-whisper.

The media and transcription are processed locally. The application does not
upload the selected video, extracted audio, or transcript to a transcription
service.

## Features

- Select a video through a desktop interface.
- Create a video-only file without re-encoding the video stream.
- Export the first audio stream as a high-quality MP3.
- Transcribe speech locally with faster-whisper.
- Detect the spoken language automatically or use a selected language code.
- Run on CPU or a compatible NVIDIA CUDA GPU.
- Generate a clean paragraph-based transcript.
- Optionally generate a timestamped transcript.
- Display progress and processing logs.
- Cancel an active job.
- Support Windows, Linux, and macOS launch scripts.

## Output files

For an input named `meeting.mp4`, the application creates:

```text
meeting_video_only.mp4
meeting_audio_only.mp3
meeting_transcript.txt
meeting_transcript_timestamps.txt
```

The timestamped file is created only when the option is enabled.

## How it works

1. `ffprobe` checks that the selected file contains video and audio streams.
2. `ffmpeg` copies the video stream into a video-only file.
3. `ffmpeg` converts the first audio stream into an MP3 file.
4. faster-whisper analyzes the extracted audio and generates speech segments.
5. The application normalizes whitespace and punctuation.
6. The cleaned transcript is saved as UTF-8 text.

## Requirements

- 64-bit Python 3.10, 3.11, 3.12, or 3.13
- Tkinter
- FFmpeg and ffprobe available in `PATH`
- Internet access the first time each Whisper model is downloaded
- A compatible NVIDIA CUDA environment only when GPU mode is used

CPU mode does not require an NVIDIA GPU.

Verify the required commands:

```bash
python --version
ffmpeg -version
ffprobe -version
```

Verify Tkinter:

```bash
python -m tkinter
```

A small Tkinter test window should open.

## Windows installation

1. Install 64-bit Python 3.10 through 3.13.
2. During Python installation, enable:
   - **Add Python to PATH**
   - **Tcl/Tk and IDLE**
3. Install FFmpeg and ensure `ffmpeg` and `ffprobe` work in a new terminal.
4. Download or clone this repository.
5. Run `install_windows.bat`.
6. Run `run_windows.bat`.

If the installer cannot see Python or FFmpeg when double-clicked, open the
terminal where the commands work and run:

```bat
cd /d "C:\path\to\video-audio-transcriber"
install_windows.bat
```

To inspect the Windows environment, run:

```bat
diagnose_windows.bat
```

### Manual Windows installation

```bat
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip setuptools wheel
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python app.py
```

## Linux and macOS installation

Make the scripts executable:

```bash
chmod +x install_linux_mac.sh run_linux_mac.sh
```

Install and run:

```bash
./install_linux_mac.sh
./run_linux_mac.sh
```

### Manual Linux and macOS installation

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

Some Linux distributions provide Tkinter in a separate package such as
`python3-tk`.

## Usage

1. Open the application.
2. Click **Browse** beside **Input video**.
3. Confirm or change the output folder.
4. Choose a transcription model.
5. Leave Language as `auto`, or enter a language code.
6. Leave Device as `auto`, unless you specifically want CPU or CUDA.
7. Optionally enable the timestamped transcript.
8. Click **Start processing**.

Common language codes:

| Language | Code |
|---|---|
| English | `en` |
| Persian | `fa` |
| German | `de` |
| Arabic | `ar` |
| Turkish | `tr` |
| French | `fr` |
| Spanish | `es` |

## Model selection

| Model | Speed | Accuracy | Resource use |
|---|---|---|---|
| `tiny` | Fastest | Lowest | Lowest |
| `base` | Very fast | Basic | Low |
| `small` | Moderate | Good default | Moderate |
| `medium` | Slower | Better | Higher |
| `large-v3` | Slowest | Usually highest | Highest |
| `turbo` | Fast | High | High |

The first use of a model downloads its files. Larger models require more disk
space, RAM, and processing time.

## CPU and GPU modes

- **CPU:** uses INT8 computation for lower memory use.
- **CUDA:** uses a compatible NVIDIA GPU and FP16 when available.
- **Auto:** uses CUDA when a supported environment is detected; otherwise it
  falls back to CPU.

When CUDA initialization fails in automatic mode, the application retries on
CPU.

## Supported video formats

The file picker includes:

```text
MP4, MKV, MOV, AVI, WebM, M4V, WMV, FLV, MPEG, MPG, and TS
```

Actual decoding support depends on the installed FFmpeg build.

## Project structure

```text
video-audio-transcriber/
├── app.py
├── media_processor.py
├── requirements.txt
├── install_windows.bat
├── diagnose_windows.bat
├── run_windows.bat
├── install_linux_mac.sh
├── run_linux_mac.sh
├── test_text_cleanup.py
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
├── LICENSE
└── .gitignore
```

## Tests

Run the included tests:

```bash
python -m unittest test_text_cleanup.py
```

The tests currently cover transcript cleanup, paragraph splitting, and
timestamp formatting.

## Troubleshooting

### FFmpeg is not found

Confirm that both commands work:

```bash
ffmpeg -version
ffprobe -version
```

Add FFmpeg's `bin` directory to `PATH`, then reopen the terminal.

### Python is not detected on Windows

Run the installer from the same terminal where this command works:

```bat
python --version
```

You can also run:

```bat
diagnose_windows.bat
```

### CUDA errors

Select `cpu` in the Device field. CUDA mode requires compatible NVIDIA drivers
and runtime libraries.

### The transcript is inaccurate

- Select a larger model.
- Set the correct language explicitly.
- Reduce background noise.
- Use a clearer recording.
- Keep the microphone closer to the speakers.
- Avoid overlapping speech when possible.

## Privacy

The application processes selected media locally. No source media or transcript
is intentionally uploaded by the application.

The first use of a model may connect to the model host to download model files.
Package installation also connects to Python package repositories.

## Known limitations

- Only the first video stream is exported.
- Only the first audio stream is exported and transcribed.
- Speaker identification is not included.
- Word-level timestamps are not included.
- Subtitle formats such as SRT and VTT are not currently generated.
- Transcription quality depends on the source audio and selected model.

## Roadmap

Possible future improvements:

- Speaker diarization
- SRT and VTT subtitle export
- Word-level timestamps
- Batch processing
- Multiple audio-stream selection
- Noise reduction and audio normalization
- Transcript editor
- Packaged Windows executable

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before
submitting a pull request.

For security-related reports, follow [SECURITY.md](SECURITY.md).

## License

This project is available under the MIT License. See [LICENSE](LICENSE).

Third-party projects and downloaded model files remain subject to their own
licenses.

## Acknowledgements

This project uses:

- FFmpeg and ffprobe for media processing
- faster-whisper for speech transcription
- CTranslate2 for optimized model inference
- Tkinter for the desktop interface
