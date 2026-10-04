# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed
# SPDX-FileCopyrightText: Copyright 2025 kramo
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

import locale
from gettext import gettext as _
from typing import TYPE_CHECKING, Any, cast

from gi.repository import Gio, GLib, GObject, Gtk

from hotbar import SETTINGS, STATE_SETTINGS, sources
from hotbar.games import Game
from hotbar.sources import imported

from . import closures

if TYPE_CHECKING:
    from .window import Window

_SORT_MODES = {
    "last_played": ("last-played", True),
    "a-z": ("name", False),
    "z-a": ("name", True),
    "newest": ("added", True),
    "oldest": ("added", False),
}

_QUIT_DELAY = 2


class GameActions(Gio.SimpleActionGroup):
    """Action group for game actions."""

    __gtype_name__ = __qualname__

    game = GObject.Property(type=Game)

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        self.add_action_entries((
            ("add", lambda *_: add()),
            ("edit", lambda *_: edit(self.game)),
            ("play", lambda *_: play(self.game)),
            ("hide", lambda *_: hide(self.game)),
            ("unhide", lambda *_: unhide(self.game)),
            ("remove", lambda *_: remove(self.game)),
        ))

        game = Gtk.PropertyExpression.new(GameActions, None, "game")
        has_game = Gtk.ClosureExpression.new(bool, closures.bool_, (game,))
        hidden = Gtk.PropertyExpression.new(Game, game, "hidden")
        not_hidden = Gtk.ClosureExpression.new(bool, closures.not_, (hidden,))
        removed = Gtk.PropertyExpression.new(Game, game, "removed")
        not_removed = Gtk.ClosureExpression.new(bool, closures.not_, (removed,))
        false = Gtk.ConstantExpression.new_for_value(False)

        edit_action = cast(Gio.SimpleAction, self.lookup_action("edit"))
        play_action = cast(Gio.SimpleAction, self.lookup_action("play"))
        hide_action = cast(Gio.SimpleAction, self.lookup_action("hide"))
        unhide_action = cast(Gio.SimpleAction, self.lookup_action("unhide"))
        remove_action = cast(Gio.SimpleAction, self.lookup_action("remove"))

        has_game.bind(edit_action, "enabled", self)
        has_game.bind(play_action, "enabled", self)
        Gtk.TryExpression.new((hidden, false)).bind(unhide_action, "enabled", self)
        Gtk.TryExpression.new((not_hidden, false)).bind(hide_action, "enabled", self)
        Gtk.TryExpression.new((not_removed, false)).bind(remove_action, "enabled", self)


class GameEditable(GObject.Object):
    """A helper object for editing a game."""

    __gtype_name__ = __qualname__

    game = GObject.Property(type=Game)

    valid = GObject.Property(type=bool, default=False)

    executable = GObject.Property(type=str)
    name = GObject.Property(type=str)
    developer = GObject.Property(type=str)

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        executable = Gtk.PropertyExpression.new(GameEditable, None, "executable")
        name = Gtk.PropertyExpression.new(GameEditable, None, "name")
        valid = Gtk.ClosureExpression.new(bool, closures.all_, (executable, name))
        valid.bind(self, "valid", self)

    def apply(self):
        """Apply the changes."""
        if not self.valid:
            return

        if not self.game:
            self.game = imported.new()
            sources.get(imported.ID).append(self.game)

        self.game.executable = self.executable
        if self.game.name != self.name:
            self.game.name = self.name
            sorter.changed(Gtk.SorterChange.DIFFERENT)
        self.game.developer = self.developer


def play(game: Game):
    """Play `game`, quitting afterwards if the user enabled it."""
    try:
        game.play()
    except OSError:
        _window().send_toast(_("Couldn’t launch {}").format(game.name))
        return

    if not SETTINGS.get_boolean("quit-on-launch"):
        return

    # Give the launcher time to hand the game off #
    app = cast(Gtk.Application, Gio.Application.get_default())
    for window in app.get_windows():
        window.set_visible(False)
    GLib.timeout_add_seconds(_QUIT_DELAY, app.quit)


def add():
    """Add a new game."""
    window = _window()
    if window.navigation_view.props.visible_page_tag != "details":
        window.navigation_view.push_by_tag("details")
    window.details.add()


def edit(game: Game):
    """Edit `game`."""
    window = _window()
    window.details.game = game
    window.navigation_view.push_by_tag("details")
    window.details.edit()


def hide(game: Game):
    """Hide `game` and notify the user with a toast."""
    game.hidden = True
    _window().send_toast(
        _("{} hidden").format(game.name),
        undo=lambda: setattr(game, "hidden", False),
    )


def unhide(game: Game):
    """Unhide `game` and notify the user with a toast."""
    game.hidden = False
    _window().send_toast(
        _("{} unhidden").format(game.name),
        undo=lambda: setattr(game, "hidden", True),
    )


def remove(game: Game):
    """Remove `game` and notify the user with a toast."""
    game.removed = True
    _window().send_toast(
        _("{} removed").format(game.name),
        undo=lambda: setattr(game, "removed", False),
    )


def _window() -> "Window":
    app = cast(Gtk.Application, Gio.Application.get_default())
    return cast("Window", app.props.active_window)


def _sort(game1: Game, game2: Game) -> int:
    prop, invert = _SORT_MODES[STATE_SETTINGS.get_string("sort-mode")]
    a = (game2 if invert else game1).get_property(prop)
    b = (game1 if invert else game2).get_property(prop)

    return (
        _name_cmp(a, b)
        if isinstance(a, str)
        else ((a > b) - (a < b)) or _name_cmp(game1.name, game2.name)
    )


def _name_cmp(a: str, b: str) -> int:
    a, b = (name.lower().removeprefix("the ") for name in (a, b))
    return locale.strcoll(a, b)


filter_ = Gtk.EveryFilter()
filter_.append(
    Gtk.BoolFilter(
        expression=Gtk.PropertyExpression.new(Game, None, "removed"),
        invert=True,
    )
)
filter_.append(
    Gtk.BoolFilter(
        expression=Gtk.PropertyExpression.new(Game, None, "blacklisted"),
        invert=True,
    )
)

sorter = Gtk.CustomSorter.new(lambda game1, game2, _: _sort(game1, game2))
STATE_SETTINGS.connect(
    "changed::sort-mode", lambda *_: sorter.changed(Gtk.SorterChange.DIFFERENT)
)

model = Gtk.SortListModel(
    model=Gtk.FilterListModel(
        model=Gtk.FlattenListModel(model=sources.model),
        filter=filter_,
        watch_items=True,
    ),
    sorter=sorter,
)
