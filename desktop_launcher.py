from __future__ import annotations

import ctypes
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request

APP_TITLE = "AutoExcel by AB Alves"
APP_ID = "ABAlves.AutoExcel"
FROZEN = bool(getattr(sys, "frozen", False))
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
APP_FILE = RESOURCE_DIR / "app.py"
LOG_FILE = Path(tempfile.gettempdir()) / "AutoExcel-startup.log"


def write_log(message: str) -> None:
    try:
        with LOG_FILE.open("a", encoding="utf-8", errors="replace") as fh:
            fh.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except Exception:
        pass


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


def wait_for_streamlit(url: str, proc: subprocess.Popen, timeout: float = 180.0) -> bool:
    health = f"{url}/_stcore/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            write_log(f"Servidor Streamlit encerrou antes de iniciar. Código: {proc.returncode}")
            return False
        try:
            with urllib.request.urlopen(health, timeout=1.5) as response:
                if 200 <= response.status < 300:
                    return True
        except Exception:
            time.sleep(0.25)
    write_log(f"Tempo limite excedido aguardando {health}")
    return False


def run_embedded_streamlit(port: int) -> int:
    """Run the bundled Streamlit app in server-only mode inside the standalone EXE."""
    if not APP_FILE.exists():
        write_log(f"app.py não encontrado em {APP_FILE}")
        return 4

    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    os.environ["STREAMLIT_SERVER_ADDRESS"] = "127.0.0.1"
    os.environ["STREAMLIT_SERVER_PORT"] = str(port)
    os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
    os.environ["STREAMLIT_SERVER_SHOW_EMAIL_PROMPT"] = "false"
    os.environ["STREAMLIT_GLOBAL_SHOW_WARNING_ON_DIRECT_EXECUTION"] = "false"

    try:
        import streamlit as st

        write_log(f"Iniciando Streamlit {getattr(st, '__version__', '?')} em 127.0.0.1:{port}")

        # st.App is Streamlit's supported programmatic server API and is more
        # reliable inside a frozen executable than re-entering the Click CLI.
        if hasattr(st, "App"):
            app = st.App(str(APP_FILE), debug=False)
            app.run()
            return 0

        # Compatibility fallback for older Streamlit builds.
        sys.argv = [
            "streamlit",
            "run",
            str(APP_FILE),
            "--server.headless=true",
            "--server.address=127.0.0.1",
            f"--server.port={port}",
            "--server.fileWatcherType=none",
            "--browser.gatherUsageStats=false",
        ]
        from streamlit.web import cli as streamlit_cli

        result = streamlit_cli.main()
        return int(result or 0)
    except SystemExit as exc:
        write_log(f"Streamlit encerrou via SystemExit: {exc.code}")
        return int(exc.code or 0)
    except Exception:
        write_log("Falha ao iniciar o servidor Streamlit:\n" + traceback.format_exc())
        return 5


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

    log_handle = LOG_FILE.open("a", encoding="utf-8", errors="replace")
    write_log("Comando do servidor: " + " ".join(cmd))

    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )
    proc._autoexcel_log_handle = log_handle  # keep handle alive while child runs
    return proc


def close_server_log(proc: subprocess.Popen) -> None:
    handle = getattr(proc, "_autoexcel_log_handle", None)
    if handle is not None:
        try:
            handle.close()
        except Exception:
            pass


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
            write_log("Falha inesperada no modo servidor:\n" + traceback.format_exc())
            return 5

    try:
        LOG_FILE.write_text("", encoding="utf-8")
    except Exception:
        pass

    write_log(f"Iniciando {APP_TITLE}. frozen={FROZEN} executable={sys.executable}")
    set_windows_appusermodelid()

    if not APP_FILE.exists():
        write_log(f"Conteúdo interno não encontrado: {APP_FILE}")
        message_box("O conteúdo interno do AutoExcel não foi encontrado. Baixe novamente o executável oficial.")
        return 4

    try:
        import webview
    except Exception:
        write_log("Falha ao importar pywebview:\n" + traceback.format_exc())
        message_box("Não foi possível carregar a janela do AutoExcel. Baixe novamente o executável oficial.")
        return 2

    webview.settings["ALLOW_DOWNLOADS"] = True

    port = free_port()
    url = f"http://127.0.0.1:{port}"
    server = start_streamlit(port)

    try:
        if not wait_for_streamlit(url, server):
            exit_code = server.poll()
            detail = f" Código do servidor: {exit_code}." if exit_code is not None else ""
            message_box(
                "Não foi possível iniciar o AutoExcel." + detail +
                f"\n\nFoi criado um diagnóstico em:\n{LOG_FILE}"
            )
            return 3

        write_log("Servidor pronto. Abrindo janela do AutoExcel.")
        webview.create_window(
            APP_TITLE,
            url,
            width=1450,
            height=900,
            min_size=(1000, 650),
            resizable=True,
            confirm_close=False,
        )

        webview.start(func=apply_native_window_icon, debug=False)
        return 0
    finally:
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=4)
            except subprocess.TimeoutExpired:
                server.kill()
        close_server_log(server)


if __name__ == "__main__":
    raise SystemExit(main())
