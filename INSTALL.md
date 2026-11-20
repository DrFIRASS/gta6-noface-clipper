# Install

The short way is in the [README](README.md#install): clone into your Claude Code skills folder and run `setup.py`.

## What setup.py does

1. Checks Python (3.10 to 3.12).
2. Checks that ffmpeg has the subtitle filter (libass). On a Mac without it, installs Homebrew's `ffmpeg-full` next to your ffmpeg and points the skill at it (your own ffmpeg is untouched).
3. Creates `.venv` inside the skill folder and installs `requirements.txt` (faster-whisper, OpenCV, MediaPipe, yt-dlp...).
4. Prints a final check. Run it again any time: it is safe to re-run.

## Manual install

| Step | Windows (PowerShell) | macOS (Terminal) | Linux (Debian/Ubuntu) |
|---|---|---|---|
| ffmpeg + ffprobe | `winget install Gyan.FFmpeg` | `brew install ffmpeg-full` | `sudo apt install ffmpeg` |
| Python venv | `py -3.12 -m venv .venv` | `python3.12 -m venv .venv` | `python3 -m venv .venv` (`sudo apt install python3-venv`) |
| Libraries | `.venv\Scripts\pip install -r requirements.txt` | `.venv/bin/pip install -r requirements.txt` | `.venv/bin/pip install -r requirements.txt` |

- Open a NEW terminal after installing ffmpeg. Check: `ffmpeg -version`.
- GPU is optional. Windows/Linux with an NVIDIA card: `pip install -r requirements-gpu.txt`. Mac and PCs without a GPU: transcription runs on the CPU on its own.
- Colour emoji in captions need Segoe UI Emoji (Windows), Apple Color Emoji (Mac) or `sudo apt install fonts-noto-color-emoji` (Linux). Without it the emoji style is skipped; nothing breaks.

## Optional services

- **HeyGen** (your avatar on the Shorts): add a custom connector in Claude with the URL `https://mcp.heygen.com/mcp/v1/`.
- **Blotato** (posting): create an account on [Blotato](https://blotato.com/?ref=firas), connect your social accounts, then connect Blotato's MCP server in Claude.
