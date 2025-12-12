"""
Theme Selector Component

A modal dialog for selecting and applying themes to the TUI application.
Supports Tokyo Night, Nord, and GruvBox themes.
"""

from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Button, Static, Label, Select
from textual.reactive import reactive
from textual import work
from textual.binding import Binding
from pathlib import Path

from textual.events import Mount


class ThemeSelectorScreen(Screen):
    """Theme selector screen for switching between themes"""

    BINDINGS = [
        Binding("escape,q", "dismiss", "Close"),
        Binding("enter", "apply_theme", "Apply Theme"),
    ]

    selected_theme: reactive[str] = reactive("tokyo_night")

    def __init__(self):
        super().__init__()
        self.theme_options = [
            ("🌃 Tokyo Night", "tokyo_night"),
            ("❄️ Nord", "nord"),
            ("🟨 GruvBox", "gruvbox"),
        ]
        self.theme_descriptions = {
            "tokyo_night": "🌃 Dark blue theme with cyan accents",
            "nord": "❄️ Cool blue theme inspired by Nord",
            "gruvbox": "🟨 Warm retro theme with earth tones",
        }

    def compose(self):
        """Compose the theme selector UI"""
        yield Header("🎨 Theme Selector")

        with Container(classes="theme-selector-container"):
            with Vertical(classes="theme-content"):
                yield Static(
                    "Choose your preferred theme for the Network Automation TUI",
                    classes="theme-description"
                )

                # Theme selection
                yield Label("Select Theme:", classes="theme-label")

                # Create select widget with theme options
                theme_select = Select(
                    options=self.theme_options,
                    value=self.selected_theme,
                    id="theme_select"
                )
                yield theme_select

                # Theme preview
                yield Static("", id="theme_preview", classes="theme-preview")

                # Action buttons
                with Horizontal(classes="button-container"):
                    yield Button("Apply", id="btn_apply", variant="primary")
                    yield Button("Cancel", id="btn_cancel")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the screen when mounted"""
        self._update_theme_preview()
        self._select_widget("theme_select").focus()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle theme selection changes"""
        if event.select.id == "theme_select":
            self.selected_theme = event.value
            self._update_theme_preview()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events"""
        if event.button.id == "btn_apply":
            self.action_apply_theme()
        elif event.button.id == "btn_cancel":
            self.action_dismiss()

    def action_apply_theme(self) -> None:
        """Apply the selected theme"""
        self._save_theme_preference()
        self._apply_theme_to_app()
        self.notify(f"Applied {self._get_theme_name()} theme", severity="information")
        self.dismiss()

    def action_dismiss(self) -> None:
        """Close the theme selector without applying"""
        self.dismiss()

    def _update_theme_preview(self) -> None:
        """Update the theme preview text"""
        theme_name = self._get_theme_name()
        theme_description = self._get_theme_description()

        preview_widget = self._select_widget("#theme_preview")
        if preview_widget:
            preview_widget.update(
                f"📋 Current Selection: {theme_name}\n"
                f"📝 {theme_description}\n\n"
                f"✨ Preview:\n"
                f"   • Headers: [Primary Color]\n"
                f"   • Buttons: [Accent Color]\n"
                f"   • Background: [Dark/Light Tone]\n"
                f"   • Text: [Contrasting Color]"
            )

    def _get_theme_name(self) -> str:
        """Get the display name of the selected theme"""
        for name, value in self.theme_options:
            if value == self.selected_theme:
                return name
        return "Unknown Theme"

    def _get_theme_description(self) -> str:
        """Get the description of the selected theme"""
        return self.theme_descriptions.get(self.selected_theme, "Unknown theme")

    def _save_theme_preference(self) -> None:
        """Save the theme preference to a config file"""
        try:
            config_dir = Path.home() / ".config" / "netstudio"
            config_dir.mkdir(parents=True, exist_ok=True)

            config_file = config_dir / "theme_config.yml"

            import yaml
            config = {"theme": self.selected_theme}

            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)

        except Exception as e:
            # If saving fails, continue but don't crash
            pass

    @work(exclusive=True)
    async def _apply_theme_to_app(self) -> None:
        """Apply the selected theme to the application"""
        try:
            # Get the main app instance
            app = self.app

            # Check if the app has set_theme method
            if hasattr(app, 'set_theme'):
                # Use the app's set_theme method
                app.set_theme(self.selected_theme)
            else:
                # Fallback to manual theme loading
                theme_paths = {
                    "tokyo_night": Path(__file__).parent.parent / "tokyo_night.tcss",
                    "nord": Path(__file__).parent.parent / "nord.tcss",
                    "gruvbox": Path(__file__).parent.parent / "gruvbox.tcss",
                }

                theme_path = theme_paths.get(self.selected_theme)
                if theme_path and theme_path.exists():
                    app.stylesheet.load(str(theme_path))
                    app.bell()  # Trigger a refresh
                else:
                    self.notify(f"Theme file not found: {theme_path}", severity="error")

        except Exception as e:
            self.notify(f"Failed to apply theme: {str(e)}", severity="error")

    def _load_theme_preference(self) -> str:
        """Load the theme preference from config file"""
        try:
            config_dir = Path.home() / ".config" / "netstudio"
            config_file = config_dir / "theme_config.yml"

            if config_file.exists():
                import yaml
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                    return config.get("theme", "tokyo_night")

        except Exception:
            # If loading fails, return default theme
            pass

        return "tokyo_night"


# Theme helper functions
def get_available_themes() -> list:
    """Get list of available themes"""
    return [
        {
            "id": "tokyo_night",
            "name": "Tokyo Night",
            "description": "🌃 Dark blue theme with cyan accents",
            "file": "tokyo_night.tcss"
        },
        {
            "id": "nord",
            "name": "Nord",
            "description": "❄️ Cool blue theme inspired by Nord",
            "file": "nord.tcss"
        },
        {
            "id": "gruvbox",
            "name": "GruvBox",
            "description": "🟨 Warm retro theme with earth tones",
            "file": "gruvbox.tcss"
        }
    ]


def get_theme_path(theme_id: str) -> Path:
    """Get the file path for a theme"""
    theme_files = {
        "tokyo_night": "tokyo_night.tcss",
        "nord": "nord.tcss",
        "gruvbox": "gruvbox.tcss"
    }

    if theme_id in theme_files:
        return Path(__file__).parent.parent / theme_files[theme_id]

    # Default to Tokyo Night if theme not found
    return Path(__file__).parent.parent / "tokyo_night.tcss"


def load_theme_preference() -> str:
    """Load saved theme preference"""
    try:
        config_dir = Path.home() / ".config" / "netstudio"
        config_file = config_dir / "theme_config.yml"

        if config_file.exists():
            import yaml
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
                return config.get("theme", "tokyo_night")

    except Exception:
        pass

    return "tokyo_night"