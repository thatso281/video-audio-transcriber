# Contributing

Thank you for considering a contribution to Video Audio Transcriber.

## Before starting

1. Search existing issues to avoid duplicates.
2. Open an issue for significant changes before implementing them.
3. Do not include private recordings, transcripts, credentials, API keys, or
   downloaded model files in a pull request.

## Development setup

Create and activate a virtual environment, then install the dependencies:

### Windows

```bat
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip setuptools wheel
.venv\Scripts\python -m pip install -r requirements.txt
```

### Linux and macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install -r requirements.txt
```

FFmpeg and ffprobe must be available in `PATH`.

## Running the application

```bash
python app.py
```

Use the virtual environment's Python executable when the environment is not
activated.

## Running tests

```bash
python -m unittest test_text_cleanup.py
```

## Pull requests

- Create a focused branch.
- Keep changes limited to one purpose.
- Add or update tests when behavior changes.
- Update the README when installation or usage changes.
- Use clear commit messages.
- Confirm that generated media, transcripts, `.venv`, and caches are not staged.
- Describe how the change was tested.

## Code style

- Use clear names and type hints.
- Keep media-processing logic outside the GUI where practical.
- Preserve responsive GUI behavior by keeping long-running work off the Tkinter
  main thread.
- Handle errors with user-readable messages.
- Avoid unnecessary dependencies.

## Reporting bugs

Use the bug-report issue template and include:

- Operating system
- Python version
- FFmpeg version
- CPU or GPU mode
- Selected model
- Full error message
- Reproduction steps

Do not attach confidential media. Use a small non-sensitive sample when one is
required to reproduce the issue.
