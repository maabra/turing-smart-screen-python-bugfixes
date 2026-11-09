# SPDX-License-Identifier: GPL-3.0-or-later
#
# Select the volume used for disk capacity sensors. On Windows, '/' is not a
# reliable way to express the system volume; use the configured system drive.

import os


def usage_path(configured_path: str = "AUTO") -> str:
    """Return the configured disk volume, or the OS volume when set to AUTO."""
    if configured_path and configured_path.upper() != "AUTO":
        return configured_path

    if os.name == "nt":
        system_drive = os.environ.get("SystemDrive")
        if system_drive:
            return system_drive + os.sep
    return os.path.abspath(os.sep)
