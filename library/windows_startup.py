# SPDX-License-Identifier: GPL-3.0-or-later

"""Manage an elevated, per-user Windows logon task for the system monitor."""

import base64
import os
import subprocess
import sys
from pathlib import Path

TASK_NAME = "TuringSystemMonitor"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "TuringSystemMonitor"
IS_WINDOWS = os.name == "nt"


def _command_parts(main_directory: Path, executable=None, frozen=None):
    main_directory = Path(main_directory).resolve()
    executable = Path(executable or sys.executable).resolve()
    if frozen is None:
        frozen = getattr(sys, "frozen", False)
    if frozen:
        program = main_directory / ("main.exe" if IS_WINDOWS else "main")
        if not program.is_file():
            raise FileNotFoundError("Packaged main executable was not found: %s" % program)
        return str(program), ""
    script = main_directory / "main.py"
    pythonw = executable.with_name("pythonw.exe") if IS_WINDOWS else executable
    if IS_WINDOWS and not pythonw.is_file():
        pythonw = executable
    return str(pythonw), '"%s"' % script


def startup_command(main_directory: Path, executable=None, frozen=None) -> str:
    """Build the command used by the scheduled task."""
    program, arguments = _command_parts(main_directory, executable, frozen)
    return subprocess.list2cmdline([program] + ([arguments.strip('"')] if arguments else []))


def _run_elevated(script: str):
    """Run a PowerShell task update after one explicit Windows UAC approval."""
    encoded_script = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    ps_quote = lambda value: "'" + str(value).replace("'", "''") + "'"
    arguments = "-NoProfile -NonInteractive -EncodedCommand " + encoded_script
    wrapper = (
        "$p=Start-Process -FilePath 'powershell.exe' -Verb RunAs -Wait -PassThru "
        "-ArgumentList " + ps_quote(arguments) + "; exit $p.ExitCode"
    )
    encoded_wrapper = base64.b64encode(wrapper.encode("utf-16le")).decode("ascii")
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-EncodedCommand", encoded_wrapper],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise OSError(detail or "Windows did not create or update the startup task")


def is_enabled():
    if not IS_WINDOWS:
        return False
    result = subprocess.run(
        ["schtasks.exe", "/Query", "/TN", TASK_NAME],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    if result.returncode == 0:
        return True
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_QUERY_VALUE) as key:
            winreg.QueryValueEx(key, RUN_VALUE)
            return True
    except (FileNotFoundError, OSError):
        return False


def set_enabled(enabled: bool, command=None, main_directory=None):
    """Create or remove the elevated logon task (Windows will request UAC once)."""
    if not IS_WINDOWS:
        raise OSError("Windows startup tasks are only available on Windows")
    if enabled:
        if main_directory is None:
            raise ValueError("main_directory is required when enabling startup")
        program, arguments = _command_parts(main_directory)
        if command:
            # Preserve callers that provide a complete command.
            program = command
            arguments = ""
        ps_quote = lambda value: "'" + str(value).replace("'", "''") + "'"
        account = os.environ.get("USERDOMAIN", "") + "\\" + os.environ.get("USERNAME", "")
        script = "\n".join([
            "$ErrorActionPreference = 'Stop'",
            "$action = New-ScheduledTaskAction -Execute " + ps_quote(program) +
                (" -Argument " + ps_quote(arguments) if arguments else "") +
                " -WorkingDirectory " + ps_quote(Path(main_directory).resolve()),
            "$trigger = New-ScheduledTaskTrigger -AtLogOn -User " + ps_quote(account),
            "$principal = New-ScheduledTaskPrincipal -UserId " + ps_quote(account) + " -LogonType Interactive -RunLevel Highest",
            "$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable",
            "Register-ScheduledTask -TaskName " + ps_quote(TASK_NAME) +
                " -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null",
        ])
    else:
        script = "\n".join([
            "$ErrorActionPreference = 'Stop'",
            "Unregister-ScheduledTask -TaskName '" + TASK_NAME + "' -Confirm:$false -ErrorAction SilentlyContinue",
        ])
    _run_elevated(script)
    # Remove the old non-elevated Run entry so it cannot launch a second instance.
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, RUN_VALUE)
            except FileNotFoundError:
                pass
    except FileNotFoundError:
        pass
