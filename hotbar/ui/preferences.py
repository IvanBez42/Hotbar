from typing import Any

from gi.repository import Adw, Gio, Gtk

from hotbar import SETTINGS
from hotbar.config import PREFIX


@Gtk.Template(resource_path=f"{PREFIX}/preferences.ui")
class Preferences(Adw.PreferencesDialog):
    """The preferences dialog."""

    __gtype_name__ = __qualname__

    quit_on_launch_row: Adw.SwitchRow = Gtk.Template.Child()

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        SETTINGS.bind(
            "quit-on-launch",
            self.quit_on_launch_row,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )
