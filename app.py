from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from media_processor import (
    MediaProcessor,
    ProcessingCancelled,
    ProcessingError,
    ProcessingOptions,
    ProcessingResult,
)


APP_TITLE = "Video Audio Transcriber"
VIDEO_FILE_TYPES = [
    (
        "Video files",
        "*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.wmv *.flv *.mpeg *.mpg *.ts",
    ),
    ("All files", "*.*"),
]


class VideoTranscriberApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title(APP_TITLE)
        self.geometry("820x650")
        self.minsize(720, 560)

        self._event_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._worker_thread: threading.Thread | None = None
        self._processor: MediaProcessor | None = None
        self._last_output_directory: Path | None = None

        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.model_var = tk.StringVar(value="small")
        self.language_var = tk.StringVar(value="auto")
        self.device_var = tk.StringVar(value="auto")
        self.timestamps_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Select a video to begin.")

        self._configure_styles()
        self._build_interface()
        self._set_running_state(False)

        self.after(100, self._drain_event_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)

        available_themes = style.theme_names()
        for preferred in ("vista", "clam", "default"):
            if preferred in available_themes:
                style.theme_use(preferred)
                break

        style.configure("Title.TLabel", font=("TkDefaultFont", 17, "bold"))
        style.configure("Subtitle.TLabel", font=("TkDefaultFont", 10))
        style.configure("Section.TLabelframe.Label", font=("TkDefaultFont", 10, "bold"))
        style.configure("Primary.TButton", padding=(18, 9))
        style.configure("Secondary.TButton", padding=(12, 7))

    def _build_interface(self) -> None:
        container = ttk.Frame(self, padding=18)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(4, weight=1)

        header = ttk.Frame(container)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))

        ttk.Label(
            header,
            text=APP_TITLE,
            style="Title.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            header,
            text=(
                "Separate video and audio, then create a clean local speech transcript."
            ),
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        files_frame = ttk.LabelFrame(
            container,
            text="Files",
            padding=12,
            style="Section.TLabelframe",
        )
        files_frame.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        files_frame.columnconfigure(1, weight=1)

        ttk.Label(files_frame, text="Input video:").grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 10),
            pady=5,
        )
        self.input_entry = ttk.Entry(
            files_frame,
            textvariable=self.input_var,
        )
        self.input_entry.grid(row=0, column=1, sticky="ew", pady=5)
        self.input_button = ttk.Button(
            files_frame,
            text="Browse...",
            command=self._choose_input_file,
            style="Secondary.TButton",
        )
        self.input_button.grid(row=0, column=2, padx=(10, 0), pady=5)

        ttk.Label(files_frame, text="Output folder:").grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 10),
            pady=5,
        )
        self.output_entry = ttk.Entry(
            files_frame,
            textvariable=self.output_var,
        )
        self.output_entry.grid(row=1, column=1, sticky="ew", pady=5)
        self.output_button = ttk.Button(
            files_frame,
            text="Browse...",
            command=self._choose_output_directory,
            style="Secondary.TButton",
        )
        self.output_button.grid(row=1, column=2, padx=(10, 0), pady=5)

        options_frame = ttk.LabelFrame(
            container,
            text="Transcription options",
            padding=12,
            style="Section.TLabelframe",
        )
        options_frame.grid(row=2, column=0, sticky="ew", pady=(0, 12))

        for column in range(6):
            options_frame.columnconfigure(column, weight=1 if column in (1, 3, 5) else 0)

        ttk.Label(options_frame, text="Model:").grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=5,
        )
        self.model_combo = ttk.Combobox(
            options_frame,
            textvariable=self.model_var,
            values=("tiny", "base", "small", "medium", "large-v3", "turbo"),
            state="readonly",
            width=13,
        )
        self.model_combo.grid(row=0, column=1, sticky="ew", padx=(0, 18), pady=5)

        ttk.Label(options_frame, text="Language:").grid(
            row=0,
            column=2,
            sticky="w",
            padx=(0, 8),
            pady=5,
        )
        self.language_combo = ttk.Combobox(
            options_frame,
            textvariable=self.language_var,
            values=(
                "auto",
                "en",
                "fa",
                "de",
                "fr",
                "es",
                "it",
                "ar",
                "tr",
                "ru",
                "zh",
                "ja",
            ),
            width=10,
        )
        self.language_combo.grid(row=0, column=3, sticky="ew", padx=(0, 18), pady=5)

        ttk.Label(options_frame, text="Device:").grid(
            row=0,
            column=4,
            sticky="w",
            padx=(0, 8),
            pady=5,
        )
        self.device_combo = ttk.Combobox(
            options_frame,
            textvariable=self.device_var,
            values=("auto", "cpu", "cuda"),
            state="readonly",
            width=10,
        )
        self.device_combo.grid(row=0, column=5, sticky="ew", pady=5)

        self.timestamps_check = ttk.Checkbutton(
            options_frame,
            text="Also save a transcript with timestamps",
            variable=self.timestamps_var,
        )
        self.timestamps_check.grid(
            row=1,
            column=0,
            columnspan=6,
            sticky="w",
            pady=(8, 2),
        )

        hint = (
            "Recommended: small + auto. Use language “auto” for automatic detection. "
            "Large models are more accurate but require more memory and processing time."
        )
        ttk.Label(
            options_frame,
            text=hint,
            wraplength=720,
        ).grid(
            row=2,
            column=0,
            columnspan=6,
            sticky="w",
            pady=(7, 0),
        )

        actions_frame = ttk.Frame(container)
        actions_frame.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        actions_frame.columnconfigure(0, weight=1)

        left_actions = ttk.Frame(actions_frame)
        left_actions.grid(row=0, column=0, sticky="w")

        self.start_button = ttk.Button(
            left_actions,
            text="Start processing",
            command=self._start_processing,
            style="Primary.TButton",
        )
        self.start_button.pack(side="left")

        self.cancel_button = ttk.Button(
            left_actions,
            text="Cancel",
            command=self._cancel_processing,
            style="Secondary.TButton",
        )
        self.cancel_button.pack(side="left", padx=(8, 0))

        self.open_folder_button = ttk.Button(
            actions_frame,
            text="Open output folder",
            command=self._open_output_folder,
            style="Secondary.TButton",
        )
        self.open_folder_button.grid(row=0, column=1, sticky="e")

        activity_frame = ttk.LabelFrame(
            container,
            text="Progress",
            padding=12,
            style="Section.TLabelframe",
        )
        activity_frame.grid(row=4, column=0, sticky="nsew")
        activity_frame.columnconfigure(0, weight=1)
        activity_frame.rowconfigure(2, weight=1)

        ttk.Label(
            activity_frame,
            textvariable=self.status_var,
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.progress_bar = ttk.Progressbar(
            activity_frame,
            mode="determinate",
            maximum=100,
        )
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        log_container = ttk.Frame(activity_frame)
        log_container.grid(row=2, column=0, sticky="nsew")
        log_container.columnconfigure(0, weight=1)
        log_container.rowconfigure(0, weight=1)

        self.log_text = tk.Text(
            log_container,
            height=12,
            wrap="word",
            state="disabled",
            font=("TkFixedFont", 9),
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            log_container,
            orient="vertical",
            command=self.log_text.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def _choose_input_file(self) -> None:
        filename = filedialog.askopenfilename(
            title="Select a video",
            filetypes=VIDEO_FILE_TYPES,
        )
        if not filename:
            return

        input_path = Path(filename)
        self.input_var.set(str(input_path))

        default_output = input_path.parent / f"{input_path.stem}_output"
        self.output_var.set(str(default_output))

    def _choose_output_directory(self) -> None:
        initial_directory = self.output_var.get().strip() or self.input_var.get().strip()
        if initial_directory and Path(initial_directory).is_file():
            initial_directory = str(Path(initial_directory).parent)

        directory = filedialog.askdirectory(
            title="Select output folder",
            initialdir=initial_directory or None,
        )
        if directory:
            self.output_var.set(directory)

    def _start_processing(self) -> None:
        if self._is_running():
            return

        input_text = self.input_var.get().strip()
        output_text = self.output_var.get().strip()

        if not input_text:
            messagebox.showwarning(APP_TITLE, "Select an input video first.")
            return

        if not output_text:
            input_path = Path(input_text)
            output_text = str(input_path.parent / f"{input_path.stem}_output")
            self.output_var.set(output_text)

        language_text = self.language_var.get().strip().lower()
        language = None if language_text in {"", "auto"} else language_text

        options = ProcessingOptions(
            input_file=Path(input_text),
            output_directory=Path(output_text),
            model_size=self.model_var.get().strip(),
            language=language,
            device=self.device_var.get().strip(),
            save_timestamps=self.timestamps_var.get(),
        )

        self._clear_log()
        self._append_log("Starting job...")
        self.status_var.set("Starting...")
        self._last_output_directory = None
        self._set_running_state(True)

        self._processor = MediaProcessor(
            status_callback=lambda message: self._event_queue.put(
                ("status", message)
            ),
            log_callback=lambda message: self._event_queue.put(
                ("log", message)
            ),
            progress_callback=lambda value: self._event_queue.put(
                ("progress", value)
            ),
        )

        self._worker_thread = threading.Thread(
            target=self._worker,
            args=(options,),
            daemon=True,
        )
        self._worker_thread.start()

    def _worker(self, options: ProcessingOptions) -> None:
        assert self._processor is not None

        try:
            result = self._processor.process(options)
        except ProcessingCancelled as exc:
            self._event_queue.put(("cancelled", str(exc)))
        except ProcessingError as exc:
            self._event_queue.put(("error", str(exc)))
        except Exception as exc:
            self._event_queue.put(
                (
                    "error",
                    "An unexpected error occurred:\n"
                    f"{type(exc).__name__}: {exc}",
                )
            )
        else:
            self._event_queue.put(("completed", result))

    def _cancel_processing(self) -> None:
        if not self._is_running() or self._processor is None:
            return

        self.status_var.set("Cancelling...")
        self._append_log("Cancellation requested.")
        self._processor.cancel()
        self.cancel_button.configure(state="disabled")

    def _drain_event_queue(self) -> None:
        try:
            while True:
                event_type, payload = self._event_queue.get_nowait()

                if event_type == "status":
                    self.status_var.set(str(payload))
                elif event_type == "log":
                    self._append_log(str(payload))
                elif event_type == "progress":
                    self._update_progress(payload)
                elif event_type == "completed":
                    self._handle_completed(payload)
                elif event_type == "cancelled":
                    self._handle_cancelled(str(payload))
                elif event_type == "error":
                    self._handle_error(str(payload))
        except queue.Empty:
            pass
        finally:
            self.after(100, self._drain_event_queue)

    def _update_progress(self, value: object) -> None:
        if value is None:
            if str(self.progress_bar["mode"]) != "indeterminate":
                self.progress_bar.configure(mode="indeterminate")
                self.progress_bar.start(12)
            return

        numeric_value = max(0.0, min(float(value), 1.0))

        if str(self.progress_bar["mode"]) != "determinate":
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")

        self.progress_bar["value"] = numeric_value * 100

    def _handle_completed(self, payload: object) -> None:
        result = payload
        if not isinstance(result, ProcessingResult):
            self._handle_error("The processor returned an invalid result.")
            return

        self._last_output_directory = result.transcript_file.parent
        self._set_running_state(False)
        self._update_progress(1.0)
        self.status_var.set("Completed successfully.")

        language_details = ""
        if result.detected_language:
            language_details = f"\nDetected language: {result.detected_language}"
            if result.language_probability is not None:
                language_details += (
                    f" ({result.language_probability * 100:.1f}% confidence)"
                )

        timestamp_line = ""
        if result.timestamped_transcript_file is not None:
            timestamp_line = (
                f"\nTimestamped text: {result.timestamped_transcript_file.name}"
            )

        messagebox.showinfo(
            APP_TITLE,
            "Processing completed.\n\n"
            f"Video: {result.video_file.name}\n"
            f"Audio: {result.audio_file.name}\n"
            f"Transcript: {result.transcript_file.name}"
            f"{timestamp_line}"
            f"{language_details}",
        )

    def _handle_cancelled(self, message: str) -> None:
        self._set_running_state(False)
        self._reset_progress()
        self.status_var.set("Cancelled.")
        self._append_log(message)

    def _handle_error(self, message: str) -> None:
        self._set_running_state(False)
        self._reset_progress()
        self.status_var.set("Failed.")
        self._append_log("ERROR: " + message)
        messagebox.showerror(APP_TITLE, message)

    def _set_running_state(self, running: bool) -> None:
        normal_or_disabled = "disabled" if running else "normal"
        readonly_or_disabled = "disabled" if running else "readonly"

        self.start_button.configure(state=normal_or_disabled)
        self.input_button.configure(state=normal_or_disabled)
        self.output_button.configure(state=normal_or_disabled)
        self.input_entry.configure(state=normal_or_disabled)
        self.output_entry.configure(state=normal_or_disabled)
        self.model_combo.configure(state=readonly_or_disabled)
        self.device_combo.configure(state=readonly_or_disabled)
        self.language_combo.configure(state=normal_or_disabled)
        self.timestamps_check.configure(state=normal_or_disabled)
        self.cancel_button.configure(state="normal" if running else "disabled")
        self.open_folder_button.configure(
            state="normal"
            if not running and self._last_output_directory is not None
            else "disabled"
        )

        if not running and str(self.progress_bar["mode"]) == "indeterminate":
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")

    def _reset_progress(self) -> None:
        if str(self.progress_bar["mode"]) == "indeterminate":
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")
        self.progress_bar["value"] = 0

    def _append_log(self, text: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text.rstrip() + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _open_output_folder(self) -> None:
        directory = self._last_output_directory
        if directory is None:
            output_text = self.output_var.get().strip()
            if output_text:
                directory = Path(output_text)

        if directory is None or not directory.exists():
            messagebox.showwarning(APP_TITLE, "The output folder does not exist yet.")
            return

        try:
            if sys.platform.startswith("win"):
                os.startfile(directory)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(directory)])
            else:
                subprocess.Popen(["xdg-open", str(directory)])
        except OSError as exc:
            messagebox.showerror(
                APP_TITLE,
                f"Could not open the output folder:\n{exc}",
            )

    def _is_running(self) -> bool:
        return self._worker_thread is not None and self._worker_thread.is_alive()

    def _on_close(self) -> None:
        if self._is_running():
            should_close = messagebox.askyesno(
                APP_TITLE,
                "Processing is still running. Cancel it and close the application?",
            )
            if not should_close:
                return

            if self._processor is not None:
                self._processor.cancel()

        self.destroy()


if __name__ == "__main__":
    app = VideoTranscriberApp()
    app.mainloop()
