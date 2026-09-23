"""Best-effort operating-system presentation preferences for the native UI."""

from __future__ import annotations

import ctypes
import platform
import subprocess
from functools import lru_cache


@lru_cache(maxsize=1)
def system_reduced_motion() -> bool:
    """Read the host animation preference without changing it or blocking startup."""

    system = platform.system()
    if system == "Darwin":
        try:
            result = subprocess.run(
                ["defaults", "read", "com.apple.universalaccess", "reduceMotion"],
                check=False,
                capture_output=True,
                text=True,
                timeout=0.25,
            )
            return result.returncode == 0 and result.stdout.strip().lower() in {
                "1",
                "true",
                "yes",
            }
        except (OSError, subprocess.SubprocessError):
            return False
    if system == "Windows":
        enabled = ctypes.c_bool()
        # SPI_GETCLIENTAREAANIMATION is the supported Windows accessibility setting.
        windll = getattr(ctypes, "windll")  # noqa: B009
        available = bool(windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0))
        return available and not enabled.value
    if system == "Linux":
        try:
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "enable-animations"],
                check=False,
                capture_output=True,
                text=True,
                timeout=0.25,
            )
            return result.returncode == 0 and result.stdout.strip().lower() == "false"
        except (OSError, subprocess.SubprocessError):
            return False
    return False
