from __future__ import annotations

import ctypes
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

APP_TITLE = "AutoExcel by AB Alves"
APP_ID = "ABAlves.AutoExcel"

# When frozen by PyInstaller, the EXE stays in the app folder while
# PyInstaller extracts Python internals elsewhere. Always use the EXE folder
# for app.py, the icon and the local virtual environment.
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent

APP_FILE = APP_DIR / "app.py"
ICON_FILE = APP_DIR / "app_icon.ico"
VENV_PYTHON = APP_DIR / ".venv_v4" / "Scripts" / "python.exe"


def set_windows_appusermodelid() -> None:
    """Give Windows a stable identity for taskbar grouping/icon handling."""
    if os.name != "nt":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


def message_box(text: str, title: str = APP_TITLE) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, text, title, 0x10)
    except Exception:
        pass


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_streamlit(url: str, proc: subprocess.Popen, timeout: float = 40.0) -> bool:
    health = f"{url}/_stcore/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(health, timeout=0.8) as response:
                if 200 <= response.status < 300:
                    return True
        except Exception:
            time.sleep(0.18)
    return False


def streamlit_python() -> Path:
    # In the frozen desktop EXE, the Streamlit server must still run from the
    # local venv, not from the frozen EXE itself.
    if VENV_PYTHON.exists():
        return VENV_PYTHON

    executable = Path(sys.executable)
    if executable.name.lower() == "pythonw.exe":
        candidate = executable.with_name("python.exe")
        if candidate.exists():
            return candidate
    return executable


def start_streamlit(port: int) -> subprocess.Popen:
    python_exe = streamlit_python()
    cmd = [
        str(python_exe),
        "-m",
        "streamlit",
        "run",
        str(APP_FILE),
        "--server.headless=true",
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--browser.gatherUsageStats=false",
    ]

    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    return subprocess.Popen(
        cmd,
        cwd=str(APP_DIR),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )


def apply_native_window_icon() -> None:
    """Extra Win32 fallback for title-bar and taskbar icon."""
    if os.name != "nt" or not ICON_FILE.exists():
        return

    user32 = ctypes.windll.user32
    WM_SETICON = 0x0080
    ICON_SMALL = 0
    ICON_BIG = 1
    IMAGE_ICON = 1
    LR_LOADFROMFILE = 0x0010

    hwnd = None
    for _ in range(150):
        try:
            hwnd = user32.FindWindowW(None, APP_TITLE)
        except Exception:
            hwnd = None
        if hwnd:
            break
        time.sleep(0.1)

    if not hwnd:
        return

    try:
        hicon_big = user32.LoadImageW(None, str(ICON_FILE), IMAGE_ICON, 256, 256, LR_LOADFROMFILE)
        hicon_small = user32.LoadImageW(None, str(ICON_FILE), IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
        if hicon_small:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)
        if hicon_big:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)
    except Exception:
        pass


def main() -> int:
    set_windows_appusermodelid()

    try:
        import webview
    except Exception:
        message_box(
            "O componente da janela desktop ainda não está instalado.\n\n"
            "Execute INICIAR_APP.bat uma vez para concluir a instalação."
        )
        return 2

    webview.settings["ALLOW_DOWNLOADS"] = True

    if not APP_FILE.exists():
        message_box("Não encontrei app.py ao lado do AutoExcel.exe.")
        return 4

    if not VENV_PYTHON.exists() and getattr(sys, "frozen", False):
        message_box(
            "O ambiente local do AutoExcel não foi encontrado.\n\n"
            "Execute INICIAR_APP.bat para reparar a instalação."
        )
        return 5

    port = free_port()
    url = f"http://127.0.0.1:{port}"
    server = start_streamlit(port)

    try:
        if not wait_for_streamlit(url, server):
            message_box(
                "Não foi possível iniciar o AutoExcel.\n\n"
                "Execute INICIAR_APP.bat para reparar a instalação."
            )
            return 3

        webview.create_window(
            APP_TITLE,
            url,
            width=1450,
            height=900,
            min_size=(1000, 650),
            resizable=True,
            confirm_close=False,
        )

        start_kwargs = {"func": apply_native_window_icon, "debug": False}
        if ICON_FILE.exists():
            start_kwargs["icon"] = str(ICON_FILE)
        webview.start(**start_kwargs)
        return 0
    finally:
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=4)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
