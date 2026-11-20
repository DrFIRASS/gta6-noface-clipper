# noface-clipper setup: one command, safe to re-run.
# Usage: python3 setup.py            (from the skill folder, with Python 3.10 to 3.12)
# Creates .venv, installs requirements.txt, checks ffmpeg has the subtitle filter (libass).
# On a Mac whose ffmpeg has no libass it uses Homebrew's ffmpeg-full (keg-only: your normal ffmpeg is untouched)
# and writes a .pth file inside .venv so every skill script finds that ffmpeg first.
import os, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV = HERE / ".venv"
PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
FULL = Path("/opt/homebrew/opt/ffmpeg-full/bin")  # Apple Silicon Homebrew; Intel Macs: /usr/local/opt/ffmpeg-full/bin
FULL_INTEL = Path("/usr/local/opt/ffmpeg-full/bin")


def has_ass(ffmpeg):
    try:
        out = subprocess.run([str(ffmpeg), "-hide_banner", "-filters"], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.TimeoutExpired):
        return False
    return any(line.split()[1:2] == ["ass"] for line in out.splitlines() if len(line.split()) > 1)


def step(msg): print(f"\n== {msg}", flush=True)


def main():
    if not (3, 10) <= sys.version_info[:2] <= (3, 12):
        sys.exit(f"Python {sys.version.split()[0]} found. Use Python 3.10 to 3.12 (Mac: brew install python@3.12, then python3.12 setup.py).")
    step("ffmpeg")
    ff = shutil.which("ffmpeg")
    ff_dir = None
    if ff and has_ass(ff):
        print(f"ok: {ff} has the subtitle filter")
    elif sys.platform == "darwin":
        full = next((d for d in (FULL, FULL_INTEL) if (d / "ffmpeg").exists()), None)
        if not full:
            print("Your ffmpeg has no subtitle filter (libass). Installing Homebrew's ffmpeg-full next to it (your ffmpeg stays as is)...")
            subprocess.run(["brew", "install", "ffmpeg-full"], check=True)
            full = next((d for d in (FULL, FULL_INTEL) if (d / "ffmpeg").exists()), None)
        if not full or not has_ass(full / "ffmpeg"):
            sys.exit("ffmpeg-full is missing or has no libass. Run: brew install ffmpeg-full")
        ff_dir = full
        print(f"ok: using {full}/ffmpeg for the skill")
    else:
        sys.exit("ffmpeg with libass is required. Windows: winget install Gyan.FFmpeg  ·  Linux: sudo apt install ffmpeg")
    step("Python environment")
    if not PY.exists():
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    subprocess.run([str(PY), "-m", "pip", "install", "-q", "--upgrade", "pip"], check=True)
    subprocess.run([str(PY), "-m", "pip", "install", "-q", "-r", str(HERE / "requirements.txt")], check=True)
    site = subprocess.run([str(PY), "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"], capture_output=True, text=True, check=True).stdout.strip()
    pth = Path(site) / "noface_clipper_ffmpeg.pth"  # a .pth "import" line runs at every start of this venv's python (a sitecustomize.py can be shadowed by Homebrew's own)
    old = Path(site) / "sitecustomize.py"
    if old.exists() and "noface-clipper" in old.read_text(encoding="utf-8"): old.unlink()
    if ff_dir:
        pth.write_text(f"import os; os.environ['PATH'] = {str(ff_dir)!r} + os.pathsep + os.environ.get('PATH', '')\n", encoding="utf-8")
        print(f"ok: {pth.name} puts {ff_dir} first on PATH for the skill only")
    elif pth.exists():
        pth.unlink()
    step("check")
    r = subprocess.run([str(PY), "-c", "import shutil, cv2, mediapipe, faster_whisper, yt_dlp; print('ffmpeg:', shutil.which('ffmpeg')); print('opencv', cv2.__version__, '· mediapipe', mediapipe.__version__, '· yt-dlp', yt_dlp.version.__version__)"],
                       capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip()[-800:])
    if r.returncode:
        sys.exit("setup check failed (see above)")
    print("\nnoface-clipper is ready.")


if __name__ == "__main__":
    main()
