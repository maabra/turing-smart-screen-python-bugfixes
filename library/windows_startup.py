# SPDX-License-Identifier: GPL-3.0-or-later

"""Manage the current user's Windows Startup Apps Run entry."""

import os
import subprocess
import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "Turing System Monitor"
OLD_RUN_VALUE = "TuringSystemMonitor"
LEGACY_TASK_NAME = "TuringSystemMonitor"
IS_WINDOWS = os.name == "nt"


def startup_command(main_directory: Path, executable=None, frozen=None) -> str:
    """Build a quoted command that launches the monitor executable or script."""
    main_directory = Path(main_directory).resolve()
    executable = Path(executable or sys.executable).resolve()
    if frozen is None:
        frozen = getattr(sys, "frozen", False)

    if frozen:
        program = main_directory / ("main.exe" if IS_WINDOWS else "main")
        if not program.is_file():
            raise FileNotFoundError("Packaged main executable was not found: %s" % program)
        command_parts = [str(program)]
    else:
        script = main_directory / "main.py"
        pythonw = executable.with_name("pythonw.exe") if IS_WINDOWS else executable
        if IS_WINDOWS and not pythonw.is_file():
            pythonw = executable
        command_parts = [str(pythonw), str(script)]

    return subprocess.list2cmdline(command_parts)


def _remove_legacy_task():
    """Best-effort removal of the earlier Task Scheduler startup registration."""
    if not IS_WINDOWS:
        return
    try:
        subprocess.run(
            ["schtasks.exe", "/Delete", "/TN", LEGACY_TASK_NAME, "/F"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
        )
    except OSError:
        pass


def is_enabled():
    if not IS_WINDOWS:
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_QUERY_VALUE) as key:
            for value_name in (RUN_VALUE, OLD_RUN_VALUE):
                try:
                    winreg.QueryValueEx(key, value_name)
                    return True
                except FileNotFoundError:
                    pass
            return False
    except (FileNotFoundError, OSError):
        return False


def set_enabled(enabled: bool, command=None, main_directory=None):
    """Add/remove the per-user Run entry shown in Windows Startup Apps."""
    if not IS_WINDOWS:
        raise OSError("Windows startup settings are only available on Windows")
    import winreg

    _remove_legacy_task()
    if enabled:
        if command is None:
            if main_directory is None:
                raise ValueError("main_directory is required when command is omitted")
            command = startup_command(main_directory)
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, command)
    else:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                for value_name in (RUN_VALUE, OLD_RUN_VALUE):
                    try:
                        winreg.DeleteValue(key, value_name)
                    except FileNotFoundError:
                        pass
        except FileNotFoundError:
            pass
