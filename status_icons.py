# status_icons.py
"""
Módulo de íconos (emojis) para mensajes de estado.

Uso rápido:
    from status_icons import ICON_OK, ICON_ERROR, icon_status

    print(f"{ICON_OK} Todo bien")
    icon_status("error", "No se pudo conectar a la base de datos")
"""

ICON_OK = "\U00002705"                # ✅
ICON_OK_ALT = "\U00002714\U0000FE0F"  # ✔️
ICON_WAIT = "\U000023F3"              # ⏳
ICON_WAIT_ALT = "\U0001F552"          # 🕒
ICON_ERROR = "\U0000274C"             # ❌
ICON_WARNING = "\U000026A0\U0000FE0F" # ⚠️
ICON_INFO = "\U00002139\U0000FE0F"    # ℹ️
ICON_FILE = "\U0001F4C4"              # 📄
ICON_INPUT = "\U00002328\U0000FE0F"   # ⌨️
ICON_NETWORK = "\U0001F310"           # 🌐
ICON_UPLOAD = "\U00002B06\U0000FE0F"  # ⬆️
ICON_DOWNLOAD = "\U00002B07\U0000FE0F" # ⬇️
ICON_LOCK = "\U0001F512"              # 🔒
ICON_UNLOCK = "\U0001F513"            # 🔓
ICON_START = "\U000025B6\U0000FE0F"   # ▶️
ICON_PAUSE = "\U000023F8\U0000FE0F"   # ⏸️
ICON_FINISH = "\U0001F3C1"            # 🏁

_ICON_MAP = {
    "ok": ICON_OK,
    "success": ICON_OK,
    "error": ICON_ERROR,
    "fail": ICON_ERROR,
    "wait": ICON_WAIT,
    "processing": ICON_WAIT,
    "warn": ICON_WARNING,
    "warning": ICON_WARNING,
    "info": ICON_INFO,
    "file": ICON_FILE,
    "input": ICON_INPUT,
    "network": ICON_NETWORK,
    "upload": ICON_UPLOAD,
    "download": ICON_DOWNLOAD,
    "lock": ICON_LOCK,
    "unlock": ICON_UNLOCK,
    "start": ICON_START,
    "pause": ICON_PAUSE,
    "finish": ICON_FINISH,
}

def icon_status(status_type: str, message: str) -> None:
    """
    Imprime un mensaje con el ícono correspondiente al tipo de estado.
    Ejemplos de status_type: "ok", "error", "wait", "warn", "info", "start", etc.
    """
    icon = _ICON_MAP.get(status_type.lower(), ICON_INFO)
    print(f"{icon} {message}")
