"""
Save As Dialog Screen for Inventory Files
Allows users to enter a custom filename for saving inventory
"""

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Input, Button, Label
from textual.binding import Binding
from pathlib import Path


class SaveAsDialog(ModalScreen):
    """Modal dialog for Save As functionality"""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "save", "Save"),
    ]

    def __init__(self, current_filename: str = "", inventories_dir: Path = None):
        super().__init__()
        self.current_filename = current_filename
        self.inventories_dir = inventories_dir or Path("./data/inventories")
        self.result = None

    def compose(self) -> ComposeResult:
        """Compose the dialog UI"""
        with Container(id="dialog_container"):
            yield Static("💾 Save Inventory As", classes="dialog-title")
            yield Static("Enter a name for your inventory file:", classes="dialog-subtitle")

            with Vertical(classes="form-section"):
                yield Label("Filename:")
                yield Input(
                    placeholder="my_inventory.yml",
                    id="filename_input",
                    value=self.current_filename
                )
                yield Static("File will be saved with .yml extension", classes="help-text")

            with Horizontal(classes="button-container"):
                yield Button("💾 Save", id="save_button", variant="success")
                yield Button("❌ Cancel", id="cancel_button", variant="default")

    CSS = """
    SaveAsDialog {
        align: center middle;
    }

    #dialog_container {
        width: 60;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 2;
    }

    .dialog-title {
        text-style: bold;
        color: $primary;
        margin: 0 0 1 0;
    }

    .dialog-subtitle {
        color: $text-muted;
        margin: 0 0 2 0;
    }

    .form-section {
        margin: 1 0 2 0;
    }

    .form-section Label {
        margin: 0 0 0 0;
    }

    .form-section Input {
        width: 1fr;
        margin: 0 0 1 0;
    }

    .help-text {
        color: $text-muted;
        text-style: italic;
        margin: 0 0 0 0;
    }

    .button-container {
        height: auto;
        margin: 1 0 0 0;
    }

    .button-container Button {
        margin: 0 0 0 1;
    }
    """

    def on_mount(self):
        """Focus on the input field when dialog is mounted"""
        filename_input = self.query_one("#filename_input", Input)
        filename_input.focus()
        # Select the text if there's a current filename
        if self.current_filename:
            filename_input.select_all()

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses"""
        if event.button.id == "save_button":
            self._save()
        elif event.button.id == "cancel_button":
            self._cancel()

    def action_save(self):
        """Handle Enter key binding"""
        self._save()

    def action_cancel(self):
        """Handle Escape key binding"""
        self._cancel()

    def _save(self):
        """Save the entered filename"""
        filename_input = self.query_one("#filename_input", Input)
        filename = filename_input.value.strip()

        # Remove .yml extension if present to avoid duplication
        if filename.lower().endswith('.yml'):
            filename = filename[:-4]
        elif filename.lower().endswith('.yaml'):
            filename = filename[:-5]

        if not filename:
            self.notify("Please enter a filename", severity="error")
            return

        # Ensure .yml extension
        full_filename = f"{filename}.yml"

        # Check if file exists
        file_path = self.inventories_dir / full_filename
        if file_path.exists():
            # You could add a confirmation dialog here if needed
            pass

        self.result = full_filename
        self.dismiss(full_filename)

    def _cancel(self):
        """Cancel the dialog"""
        self.result = None
        self.dismiss(None)