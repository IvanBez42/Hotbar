# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed
# SPDX-FileCopyrightText: Copyright 2025-2026 kramo
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

import json
import logging
import os
import subprocess
from contextlib import suppress
from pathlib import Path
from shlex import quote
from types import UnionType
from typing import Any, NamedTuple, Self

from gi.repository import Gdk, Gio, GObject

from . import DATA_DIR

GAMES_DIR = DATA_DIR / "games"

_logger = logging.getLogger(__name__)


class _GameProp(NamedTuple):
    name: str
    type_: type | UnionType
    required: bool = False
    editable: bool = False


PROPERTIES: tuple[_GameProp, ...] = (
    _GameProp("added", int),
    _GameProp("executable", str | list[str], required=True, editable=True),
    _GameProp("game_id", str, required=True),
    _GameProp("source", str, required=True),
    _GameProp("hidden", bool),
    _GameProp("last_played", int),
    _GameProp("name", str, required=True, editable=True),
    _GameProp("developer", str, editable=True),
    _GameProp("blacklisted", bool),
    _GameProp("version", int),
)

_SPEC_VERSION = 1

# Properties the user can change, saved to disk as soon as they change
_USER_PROPS = ("hidden", "last_played", "name", "developer", "executable")


class Game(Gio.SimpleActionGroup):
    """Game data class."""

    __gtype_name__ = __qualname__

    added = GObject.Property(type=int)
    executable = GObject.Property(type=str)
    game_id = GObject.Property(type=str)
    source = GObject.Property(type=str)
    hidden = GObject.Property(type=bool, default=False)
    last_played = GObject.Property(type=int)
    name = GObject.Property(type=str)
    developer = GObject.Property(type=str)
    blacklisted = GObject.Property(type=bool, default=False)
    modified = GObject.Property(type=bool, default=False)
    version = GObject.Property(type=int, default=_SPEC_VERSION)

    cover = GObject.Property(type=Gdk.Paintable)

    # The source's own values, so only the user's changes get saved.
    _source_values: dict[str, Any] | None = None
    _saved: dict[str, Any] | None = None
    _save_handler = 0

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> Self:
        """Create a game from data. Useful for loading from JSON."""
        game = cls()

        for prop in PROPERTIES:
            value = data.get(prop.name)

            if not prop.required and value is None:
                continue

            if not isinstance(value, prop.type_):
                raise TypeError

            match prop.name:
                case "executable" if isinstance(value, list):
                    value = " ".join(value)
                case "version" if value and value > _SPEC_VERSION:
                    raise TypeError
                case "version":
                    continue

            setattr(game, prop.name, value)

        # The data came from disk, so saving it unchanged can be skipped
        game._saved = data

        return game

    def play(self):
        """Run the executable command in a shell."""
        subprocess.Popen(  # noqa: S602
            format_executable(self.executable),
            cwd=Path.home(),
            shell=True,
            start_new_session=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )

    def apply_saved(self):
        """Apply the user's saved changes, if any, over the data from the source."""
        # Remember the source's values, so only the user's changes get saved
        self._source_values = {name: getattr(self, name) for name in _USER_PROPS}

        try:
            with Path(f"{GAMES_DIR / self.game_id}.json").open(encoding="utf-8") as f:
                saved = json.load(f)
        except (OSError, ValueError):
            return

        if (
            not isinstance(saved, dict)
            or not isinstance(saved.get("version"), int)
            or saved["version"] > _SPEC_VERSION
        ):
            return

        for prop in PROPERTIES:
            if (
                prop.name not in (*_USER_PROPS, "added")
                or prop.name not in saved
                or not isinstance(saved[prop.name], prop.type_)
            ):
                continue

            value = saved[prop.name]

            if prop.name == "executable" and isinstance(value, list):
                value = " ".join(value)
            if prop.name == "last_played":
                value = max(value, self.last_played)

            setattr(self, prop.name, value)

        self._saved = saved

    def save_on_change(self):
        """Save whenever the user changes the game. Call once it's fully loaded."""
        # Never need more than one save handler (e.g. readding game)
        if not self._save_handler:
            self._save_handler = self.connect("notify", Game._on_notify)

    def _on_notify(self, pspec: GObject.ParamSpec):
        if pspec.name.replace("-", "_") in _USER_PROPS:
            self.save()

    def _update_modified(self):
        if self._source_values is None:
            return

        self.modified = any(
            (getattr(self, prop.name) or "") != (self._source_values[prop.name] or "")
            for prop in PROPERTIES
            if prop.editable
        )

    def save(self):
        """Save the user's changes to disk, or everything for imported games."""
        self._update_modified()

        if self._source_values is None:
            data = {prop.name: getattr(self, prop.name) for prop in PROPERTIES}
        else:
            data = {}
            for name, value in self._source_values.items():
                if getattr(self, name) != value:
                    data[name] = getattr(self, name)

            data["game_id"] = self.game_id
            data["source"] = self.source
            data["added"] = self.added

        data["version"] = _SPEC_VERSION

        # Setting a property to its current value still notifies, so skip no-ops
        if data == self._saved:
            return

        path = Path(f"{GAMES_DIR / self.game_id}.json")
        tmp = path.with_name(f"{path.name}.tmp")

        # Write to a temporary file and swap it in, so a crash can't corrupt the game
        try:
            GAMES_DIR.mkdir(parents=True, exist_ok=True)
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, sort_keys=True)
                f.flush()
                os.fsync(f.fileno())
            tmp.replace(path)
        except OSError:
            # Log error and remove tmp file
            _logger.exception("Couldn't save %s", self.game_id)
            with suppress(OSError):
                tmp.unlink(missing_ok=True)
            return

        self._saved = data


def format_executable(executable: str) -> str:
    """Get the correct executable for the user's environment."""
    if not Path("/.flatpak-info").exists():
        return executable

    # flatpak-session-helper's sometime lack display variables
    env_args = []
    for var in ("WAYLAND_DISPLAY", "XDG_SESSION_TYPE", "DISPLAY"):
        value = os.environ.get(var)
        if not value or (var == "DISPLAY" and value == ":99"):
            continue
        env_args.append(quote(f"--env={var}={value}"))

    return " ".join(
        ("flatpak-spawn", "--host", *env_args, "/bin/sh", "-c", quote(executable))
    )
