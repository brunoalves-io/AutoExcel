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
FROZEN = bool(getattr(sys, "frozen", False))
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
APP_FILE = RESOURCE_DIR / "app.py"


def set_windows_appusermodelid() -> None:
    if os.name != "nt":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


def message_box(text: str, title: str = APP_TITLE) -> None:
    if os.name != "nt":
        return
    try:
        ctypes.windll.user32.MessageBoxW(None, text, title, 0x10)
    except Exception:
        pass


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_streamlit(url: str, proc: subprocess.Popen, timeout: float = 60.0) -> bool:
    health = f"{url}/_stcore/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(health, timeout=1.0) as response:
                if 200 <= response.status < 300:
                    return True
        except Exception:
            time.sleep(0.2)
    return False


def run_embedded_streamlit(port: int) -> int:
    """Run the bundled Streamlit app inside the same standalone EXE."""
    if not APP_FILE.exists():
        return 4

    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "true")

    sys.argv = [
        "streamlit",
        "run",
        str(APP_FILE),
        "--server.headless=true",
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--browser.gatherUsageStats=false",
    ]

    from streamlit.web import cli as streamlit_cli

    try:
        result = streamlit_cli.main()
        return int(result or 0)
    except SystemExit as exc:
        return int(exc.code or 0)


def start_streamlit(port: int) -> subprocess.Popen:
    if FROZEN:
        cmd = [sys.executable, "--streamlit-server", str(port)]
        cwd = str(Path(sys.executable).resolve().parent)
    else:
        cmd = [sys.executable, str(Path(__file__).resolve()), "--streamlit-server", str(port)]
        cwd = str(Path(__file__).resolve().parent)

    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    return subprocess.Popen(
        cmd,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )


def apply_native_window_icon() -> None:
    """Apply the icon embedded in the standalone EXE to the pywebview window."""
    if os.name != "nt" or not FROZEN:
        return

    try:
        user32 = ctypes.windll.user32
        shell32 = ctypes.windll.shell32
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1

        hwnd = None
        for _ in range(150):
            hwnd = user32.FindWindowW(None, APP_TITLE)
            if hwnd:
                break
            time.sleep(0.1)
        if not hwnd:
            return

        large = (ctypes.c_void_p * 1)()
        small = (ctypes.c_void_p * 1)()
        extracted = shell32.ExtractIconExW(str(Path(sys.executable).resolve()), 0, large, small, 1)
        if extracted:
            if small[0]:
                user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, small[0])
            if large[0]:
                user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, large[0])
    except Exception:
        pass


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--streamlit-server":
        try:
            return run_embedded_streamlit(int(sys.argv[2]))
        except Exception:
            return 5

    set_windows_appusermodelid()

    if not APP_FILE.exists():
        message_box("O conteúdo interno do AutoExcel não foi encontrado. Baixe novamente o executável oficial.")
        return 4

    try:
        import webview
    except Exception:
        message_box("Não foi possível carregar a janela do AutoExcel. Baixe novamente o executável oficial.")
        return 2

    webview.settings["ALLOW_DOWNLOADS"] = True

    port = free_port()
    url = f"http://127.0.0.1:{port}"
    server = start_streamlit(port)

    try:
        if not wait_for_streamlit(url, server):
            message_box("Não foi possível iniciar o AutoExcel.")
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

        # On Windows, use the icon embedded in the executable itself. This keeps
        # Explorer, taskbar and title-bar icon rendering consistent.
        webview.start(func=apply_native_window_icon, debug=False)
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
