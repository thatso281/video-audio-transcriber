from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


class ProcessingError(RuntimeError):
    """Raised when media processing or transcription fails."""


class ProcessingCancelled(RuntimeError):
    """Raised when the user cancels the active job."""


@dataclass(frozen=True)
class ProcessingOptions:
    input_file: Path
    output_directory: Path
    model_size: str = "small"
    language: str | None = None
    device: str = "auto"
    save_timestamps: bool = False


@dataclass(frozen=True)
class ProcessingResult:
    video_file: Path
    audio_file: Path
    transcript_file: Path
    timestamped_transcript_file: Path | None
    detected_language: str | None
    language_probability: float | None


StatusCallback = Callable[[str], None]
LogCallback = Callable[[str], None]
ProgressCallback = Callable[[float | None], None]


class MediaProcessor:
    """
    Separates a video's streams and transcribes its audio locally.

    Required external application:
        ffmpeg and ffprobe available on PATH.

    Required Python package:
        faster-whisper
    """

    def __init__(
        self,
        status_callback: StatusCallback | None = None,
        log_callback: LogCallback | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self._status_callback = status_callback or (lambda _message: None)
        self._log_callback = log_callback or (lambda _message: None)
        self._progress_callback = progress_callback or (lambda _value: None)

        self._cancel_event = threading.Event()
        self._process_lock = threading.Lock()
        self._active_process: subprocess.Popen[str] | None = None

    def cancel(self) -> None:
        self._cancel_event.set()

        with self._process_lock:
            process = self._active_process

        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass

    def process(self, options: ProcessingOptions) -> ProcessingResult:
        self._cancel_event.clear()
        self._validate_options(options)
        self._check_dependencies()

        input_file = options.input_file.resolve()
        output_directory = options.output_directory.resolve()
        output_directory.mkdir(parents=True, exist_ok=True)

        self._status("Inspecting media streams...")
        media_info = self._probe_media(input_file)

        if not media_info["has_video"]:
            raise ProcessingError("The selected file does not contain a video stream.")

        if not media_info["has_audio"]:
            raise ProcessingError("The selected file does not contain an audio stream.")

        safe_stem = self._safe_filename(input_file.stem)
        video_extension = input_file.suffix.lower() or ".mkv"

        video_file = output_directory / f"{safe_stem}_video_only{video_extension}"
        audio_file = output_directory / f"{safe_stem}_audio_only.mp3"
        transcript_file = output_directory / f"{safe_stem}_transcript.txt"
        timestamped_file = (
            output_directory / f"{safe_stem}_transcript_timestamps.txt"
            if options.save_timestamps
            else None
        )

        self._raise_if_cancelled()

        self._status("Creating video-only file...")
        self._progress(None)
        self._extract_video(input_file, video_file)
        self._log(f"Video-only file created: {video_file}")

        self._raise_if_cancelled()

        self._status("Creating audio-only MP3...")
        self._extract_audio(input_file, audio_file)
        self._log(f"Audio-only file created: {audio_file}")

        self._raise_if_cancelled()

        self._status(
            "Loading speech model. The first run may download the selected model..."
        )
        transcript_data = self._transcribe(
            audio_file=audio_file,
            model_size=options.model_size,
            language=options.language,
            requested_device=options.device,
        )

        clean_text = self._build_clean_transcript(transcript_data["segments"])
        if not clean_text:
            raise ProcessingError(
                "Transcription completed, but no speech was detected in the audio."
            )

        self._write_utf8_text(transcript_file, clean_text + "\n")
        self._log(f"Clean transcript created: {transcript_file}")

        if timestamped_file is not None:
            timestamped_text = self._build_timestamped_transcript(
                transcript_data["segments"]
            )
            self._write_utf8_text(timestamped_file, timestamped_text + "\n")
            self._log(f"Timestamped transcript created: {timestamped_file}")

        self._progress(1.0)
        self._status("Completed successfully.")

        return ProcessingResult(
            video_file=video_file,
            audio_file=audio_file,
            transcript_file=transcript_file,
            timestamped_transcript_file=timestamped_file,
            detected_language=transcript_data["language"],
            language_probability=transcript_data["language_probability"],
        )

    def _validate_options(self, options: ProcessingOptions) -> None:
        if not options.input_file:
            raise ProcessingError("No input file was selected.")

        if not options.input_file.exists():
            raise ProcessingError(f"Input file not found: {options.input_file}")

        if not options.input_file.is_file():
            raise ProcessingError("The selected input is not a file.")

        if not options.output_directory:
            raise ProcessingError("No output directory was selected.")

        if options.model_size not in {
            "tiny",
            "base",
            "small",
            "medium",
            "large-v3",
            "turbo",
        }:
            raise ProcessingError(f"Unsupported model: {options.model_size}")

        if options.device not in {"auto", "cpu", "cuda"}:
            raise ProcessingError(f"Unsupported device: {options.device}")

    def _check_dependencies(self) -> None:
        missing = [
            program
            for program in ("ffmpeg", "ffprobe")
            if shutil.which(program) is None
        ]

        if missing:
            raise ProcessingError(
                "Missing required application(s): "
                + ", ".join(missing)
                + ". Install FFmpeg and ensure both ffmpeg and ffprobe are available "
                  "in your system PATH."
            )

        try:
            import faster_whisper  # noqa: F401
        except ImportError as exc:
            raise ProcessingError(
                "The Python package 'faster-whisper' is not installed. "
                "Activate the project's virtual environment and run: "
                "pip install -r requirements.txt"
            ) from exc

    def _probe_media(self, input_file: Path) -> dict[str, bool]:
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "json",
            str(input_file),
        ]

        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=self._creation_flags(),
            check=False,
        )

        if completed.returncode != 0:
            details = completed.stderr.strip() or "Unknown ffprobe error."
            raise ProcessingError(f"Could not inspect the selected media file:\n{details}")

        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise ProcessingError("ffprobe returned invalid media information.") from exc

        stream_types = {
            stream.get("codec_type")
            for stream in payload.get("streams", [])
            if isinstance(stream, dict)
        }

        return {
            "has_video": "video" in stream_types,
            "has_audio": "audio" in stream_types,
        }

    def _extract_video(self, input_file: Path, output_file: Path) -> None:
        command = [
            "ffmpeg",
            "-hide_banner",
            "-nostdin",
            "-y",
            "-i",
            str(input_file),
            "-map",
            "0:V:0",
            "-c:v",
            "copy",
            "-an",
            str(output_file),
        ]
        self._run_command(command, "video extraction")

    def _extract_audio(self, input_file: Path, output_file: Path) -> None:
        command = [
            "ffmpeg",
            "-hide_banner",
            "-nostdin",
            "-y",
            "-i",
            str(input_file),
            "-map",
            "0:a:0",
            "-vn",
            "-c:a",
            "libmp3lame",
            "-q:a",
            "2",
            str(output_file),
        ]
        self._run_command(command, "audio extraction")

    def _run_command(self, command: list[str], operation_name: str) -> None:
        self._raise_if_cancelled()
        self._log("Running: " + subprocess.list2cmdline(command))

        with tempfile.NamedTemporaryFile(
            mode="w+",
            encoding="utf-8",
            errors="replace",
            delete=False,
            suffix=".log",
        ) as log_file:
            log_path = Path(log_file.name)

        try:
            with log_path.open(
                "w",
                encoding="utf-8",
                errors="replace",
            ) as output_stream:
                process = subprocess.Popen(
                    command,
                    stdout=output_stream,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=self._creation_flags(),
                )

                with self._process_lock:
                    self._active_process = process

                while process.poll() is None:
                    if self._cancel_event.is_set():
                        self._terminate_process(process)
                        raise ProcessingCancelled("Processing was cancelled.")
                    time.sleep(0.1)

                return_code = process.returncode

            details = log_path.read_text(
                encoding="utf-8",
                errors="replace",
            ).strip()

            if return_code != 0:
                tail = "\n".join(details.splitlines()[-30:])
                raise ProcessingError(
                    f"FFmpeg {operation_name} failed.\n\n{tail or 'No error details were returned.'}"
                )
        finally:
            with self._process_lock:
                self._active_process = None

            try:
                log_path.unlink(missing_ok=True)
            except OSError:
                pass

    def _transcribe(
        self,
        audio_file: Path,
        model_size: str,
        language: str | None,
        requested_device: str,
    ) -> dict[str, object]:
        from faster_whisper import WhisperModel

        device, compute_type = self._resolve_device(requested_device)
        self._log(
            f"Transcription configuration: model={model_size}, "
            f"device={device}, compute_type={compute_type}, "
            f"language={language or 'auto'}"
        )

        self._raise_if_cancelled()

        try:
            model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
            )
        except Exception as exc:
            if requested_device == "auto" and device == "cuda":
                self._log(
                    "CUDA model initialization failed; retrying on CPU with INT8."
                )
                device = "cpu"
                compute_type = "int8"
                try:
                    model = WhisperModel(
                        model_size,
                        device=device,
                        compute_type=compute_type,
                    )
                except Exception as cpu_exc:
                    raise ProcessingError(
                        "Could not load the speech recognition model on CUDA or CPU. "
                        f"CPU error: {cpu_exc}"
                    ) from cpu_exc
            else:
                raise ProcessingError(
                    f"Could not load the speech recognition model: {exc}"
                ) from exc

        self._status("Transcribing speech...")
        self._progress(None)

        try:
            segment_generator, info = model.transcribe(
                str(audio_file),
                beam_size=5,
                language=language,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
                condition_on_previous_text=True,
            )

            segments: list[dict[str, object]] = []
            total_duration = float(getattr(info, "duration", 0.0) or 0.0)

            for segment in segment_generator:
                self._raise_if_cancelled()

                text = self._normalize_segment_text(segment.text)
                if text:
                    segments.append(
                        {
                            "start": float(segment.start),
                            "end": float(segment.end),
                            "text": text,
                        }
                    )

                if total_duration > 0:
                    self._progress(min(float(segment.end) / total_duration, 0.99))

            return {
                "segments": segments,
                "language": getattr(info, "language", None),
                "language_probability": getattr(
                    info,
                    "language_probability",
                    None,
                ),
            }
        except ProcessingCancelled:
            raise
        except Exception as exc:
            raise ProcessingError(f"Speech transcription failed: {exc}") from exc

    def _resolve_device(self, requested_device: str) -> tuple[str, str]:
        if requested_device == "cpu":
            return "cpu", "int8"

        if requested_device == "cuda":
            return "cuda", "float16"

        try:
            import ctranslate2

            if ctranslate2.get_cuda_device_count() > 0:
                supported = ctranslate2.get_supported_compute_types("cuda")
                if "float16" in supported:
                    return "cuda", "float16"
                if "int8_float16" in supported:
                    return "cuda", "int8_float16"
                return "cuda", "float32"
        except Exception as exc:
            self._log(f"CUDA auto-detection was unavailable: {exc}")

        return "cpu", "int8"

    def _build_clean_transcript(
        self,
        segments: Iterable[dict[str, object]],
    ) -> str:
        paragraphs: list[str] = []
        paragraph_parts: list[str] = []
        paragraph_length = 0
        previous_end: float | None = None

        for segment in segments:
            text = str(segment["text"]).strip()
            start = float(segment["start"])
            end = float(segment["end"])

            pause = start - previous_end if previous_end is not None else 0.0
            should_break = (
                bool(paragraph_parts)
                and (
                    pause >= 1.5
                    or paragraph_length >= 650
                )
            )

            if should_break:
                paragraphs.append(self._join_text_parts(paragraph_parts))
                paragraph_parts = []
                paragraph_length = 0

            paragraph_parts.append(text)
            paragraph_length += len(text) + 1
            previous_end = end

        if paragraph_parts:
            paragraphs.append(self._join_text_parts(paragraph_parts))

        return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)

    def _build_timestamped_transcript(
        self,
        segments: Iterable[dict[str, object]],
    ) -> str:
        lines: list[str] = []

        for segment in segments:
            start = self._format_timestamp(float(segment["start"]))
            end = self._format_timestamp(float(segment["end"]))
            text = str(segment["text"]).strip()
            if text:
                lines.append(f"[{start} --> {end}] {text}")

        return "\n".join(lines)

    @staticmethod
    def _join_text_parts(parts: Iterable[str]) -> str:
        text = " ".join(part.strip() for part in parts if part.strip())
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\s+([,.;:!?،؛؟])", r"\1", text)
        text = re.sub(r"([(\[«])\s+", r"\1", text)
        text = re.sub(r"\s+([)\]»])", r"\1", text)
        return text.strip()

    @staticmethod
    def _normalize_segment_text(text: str) -> str:
        text = text.replace("\r", " ").replace("\n", " ")
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        milliseconds = max(0, round(seconds * 1000))
        hours, remainder = divmod(milliseconds, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        secs, millis = divmod(remainder, 1_000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    @staticmethod
    def _write_utf8_text(path: Path, text: str) -> None:
        try:
            path.write_text(text, encoding="utf-8")
        except OSError as exc:
            raise ProcessingError(f"Could not write output file '{path}': {exc}") from exc

    @staticmethod
    def _safe_filename(value: str) -> str:
        cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", value).strip(" .")
        return cleaned or "output"

    @staticmethod
    def _creation_flags() -> int:
        if os.name == "nt":
            return subprocess.CREATE_NO_WINDOW
        return 0

    @staticmethod
    def _terminate_process(process: subprocess.Popen[str]) -> None:
        try:
            process.terminate()
            process.wait(timeout=3)
        except (OSError, subprocess.TimeoutExpired):
            try:
                process.kill()
            except OSError:
                pass

    def _raise_if_cancelled(self) -> None:
        if self._cancel_event.is_set():
            raise ProcessingCancelled("Processing was cancelled.")

    def _status(self, message: str) -> None:
        self._status_callback(message)

    def _log(self, message: str) -> None:
        self._log_callback(message)

    def _progress(self, value: float | None) -> None:
        self._progress_callback(value)
