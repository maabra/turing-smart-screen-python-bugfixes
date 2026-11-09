# SPDX-License-Identifier: GPL-3.0-or-later
#
# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/
#
# Copyright (C) 2021 Matthieu Houdebine (mathoudebine)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Configure logging format
import locale
import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

# use current locale for date/time formatting in logs
locale.setlocale(locale.LC_ALL, '')

def _log_handlers():
    handlers = [logging.StreamHandler()]
    if os.name == "nt":
        # Installed applications commonly live in Program Files, which is not
        # writable by a normal user. Keep logs in that user's local app data.
        log_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Turing System Monitor"
        log_path = log_dir / "log.log"
    else:
        log_path = Path.cwd() / "log.log"

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.insert(0, RotatingFileHandler(log_path, maxBytes=1000000, backupCount=0))
    except OSError:
        # Logging to the console is still useful when file logging is unavailable.
        pass
    return handlers


logging.basicConfig(  # format='%(asctime)s [%(levelname)s] %(message)s in %(pathname)s:%(lineno)d',
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=_log_handlers(),
    datefmt='%x %X')

logger = logging.getLogger('turing')
logger.setLevel(logging.DEBUG)  # Lowest log level : print all messages
