"""Entry point for the one-file Windows build (PyInstaller). Not used by the Python version."""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import traceback
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))
BASE = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent
BUNDLE = Path(getattr(sys, "_MEIPASS", BASE))
BIN = BUNDLE / "bin"
LOG_FILE = BASE / "musicsync.log"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _setup_environment() -> None:
    os.chdir(BASE)
    if (BIN / "ffmpeg.exe").is_file():
        os.environ.setdefault("FFMPEG_LOCATION", str(BIN))
        os.environ["PATH"] = str(BIN) + os.pathsep + os.environ.get("PATH", "")
    deno = BIN / "deno.exe"
    if deno.is_file():
        os.environ.setdefault("YTDLP_JS_RUNTIME", f"deno:{deno}")


def _fail(message: str) -> None:
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(message + "\n")
    except OSError:
        pass
    try:
        import tkinter
        from tkinter import messagebox

        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror("Music Sync", f"{message[-900:]}\n\nDetails in: {LOG_FILE}")
        root.destroy()
    except Exception:  # noqa: BLE001
        pass


def _selftest() -> int:
    """Checks that everything the program needs is inside the exe. Writes selftest.txt next to it."""
    lines = []
    ok = True

    def check(name: str, fn) -> None:
        nonlocal ok
        try:
            lines.append(f"OK    {name}: {fn()}")
        except Exception as exc:  # noqa: BLE001
            ok = False
            lines.append(f"FAIL  {name}: {exc!r}")

    def tool(exe: str) -> str:
        out = subprocess.run(
            [str(BIN / exe), "-version" if exe != "deno.exe" else "--version"],
            capture_output=True, text=True, timeout=60, creationflags=NO_WINDOW, check=True,
        ).stdout
        return out.splitlines()[0]

    def tk() -> str:
        import tkinter

        return str(tkinter.Tcl().eval("info patchlevel"))

    def mods() -> str:
        import importlib

        for name in ("yt_dlp", "yt_dlp_ejs", "ytmusicapi", "requests", "pydantic", "musicsync.gui", "musicsync.pipeline"):
            importlib.import_module(name)
        return "imports"

    def ejs() -> str:
        import yt_dlp_ejs

        return str(Path(yt_dlp_ejs.__file__).parent)

    def ytm() -> str:
        import ytmusicapi

        locales = Path(ytmusicapi.__file__).parent / "locales"
        return f"locales dir present={locales.is_dir()}"

    def icon() -> str:
        icon_path = BUNDLE / "assets" / "icon.ico"
        if not icon_path.is_file():
            raise FileNotFoundError(icon_path)
        return str(icon_path)

    check("tkinter", tk)
    check("modules", mods)
    check("yt-dlp EJS scripts", ejs)
    check("ytmusicapi", ytm)
    check("icon", icon)
    check("ffmpeg", lambda: tool("ffmpeg.exe"))
    check("ffprobe", lambda: tool("ffprobe.exe"))
    check("deno", lambda: tool("deno.exe"))
    (BASE / "selftest.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if ok else 1


def main() -> int:
    _setup_environment()
    if "--selftest" in sys.argv:
        return _selftest()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8")],
    )
    try:
        from musicsync.gui import run_gui

        run_gui(BASE)
    except Exception:  # noqa: BLE001
        _fail(traceback.format_exc())
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
