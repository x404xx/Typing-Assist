import sys
from string import Template

import httpx
import pyperclip
from pynput import keyboard
from pynput.keyboard import Controller, Key
from rich.box import HEAVY_EDGE
from rich.console import Console
from rich.live import Live
from rich.table import Table


class TypingAssist:
    def __init__(self):
        self.controller = Controller()
        self.console = Console()
        self.OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"
        self.OLLAMA_CONFIG = {
            "model": "mistral:7b-instruct-v0.2-q4_K_S",
            "keep_alive": "5m",
            "stream": False,
        }
        self.PROMPT_TEMPLATE = Template(
            """Fix all typos and casing and punctuation in this text, but preserve all new line characters:

            $text

            Return only the corrected text, don't include a preamble.
            """
        )

    def press_keys(self, *keys):
        """
        Presses a sequence of keys.

        Args:
            *keys: Variable number of keys to be pressed.

        Returns:
            None
        """

        with self.controller.pressed(*keys[:-1]):
            self.controller.tap(keys[-1])

    def fix_text(self, text):
        """
        Fixes the text by sending it to an external service for correction.

        Args:
            text: The text to be fixed.

        Returns:
            str: The corrected text.
        """

        prompt = self.PROMPT_TEMPLATE.substitute(text=text)
        try:
            with httpx.Client() as client:
                response = client.post(
                    self.OLLAMA_ENDPOINT,
                    json={"prompt": prompt, **self.OLLAMA_CONFIG},
                    headers={"Content-Type": "application/json"},
                    timeout=60,
                )
                response.raise_for_status()
                return response.json()["response"].strip()
        except httpx.RequestError as e:
            self.console.print(f"[red]HTTP error occurred:[/red] {e}")
            return None

    def fix_current_line(self):
        """
        Fixes the text in the current line by selecting the entire line and sending it for correction.

        Args:
            None

        Returns:
            None
        """

        self.press_keys(Key.home)
        self.press_keys(Key.shift, Key.end)
        self.fix_selection()

    def create_table(self, selection_text, fixed_text="Waiting for update..."):
        """
        Creates a table with the given selection text and fixed text.

        Args:
            self: Instance of the class.
            selection_text: The original text to display in the table.
            fixed_text: The corrected text to display in the table (default is "Waiting for update...").

        Returns:
            Table: A Table object displaying the selection and fixed text.
        """

        table = Table(header_style="yellow", expand=True)
        table.add_column("Selection", style="blue1", justify="center")
        table.add_column("Fixed Text", style="blue_violet", justify="center")
        table.add_row(selection_text, fixed_text)
        return table

    def fix_selection(self):
        """
        Fixes the selected text by sending it for correction and replaces it with the corrected version.

        Args:
            self: Instance of the class.

        Returns:
            None
        """

        self.press_keys(Key.ctrl, "c")
        text = pyperclip.paste()

        if not text:
            return

        initial_table = self.create_table(text)
        with Live(initial_table, console=self.console) as live:
            fixed_text = self.fix_text(text)

            if not fixed_text:
                self.console.print("[red]No changes made to the selection.[/]")
                return

            updated_table = self.create_table(text, fixed_text)
            live.update(updated_table)

        pyperclip.copy(fixed_text)
        self.press_keys(Key.ctrl, "v")

    def on_f9(self):
        """
        Handles the event triggered by pressing the F9 key to fix the text in the current line.

        Args:
            None

        Returns:
            None
        """

        self.fix_current_line()

    def on_f10(self):
        """
        Handles the event triggered by pressing the F10 key to fix the selected text.

        Args:
            None

        Returns:
            None
        """

        self.fix_selection()

    def on_esc(self):
        """
        Handles the event triggered by pressing the Esc key to exit the Typing Assist program.

        Args:
            None

        Returns:
            None
        """

        self.console.print("\n[red1]Exiting Typing Assist...[/]\n")
        sys.exit(0)

    def start_typing_assist(self):
        """
        Starts the Typing Assist program and sets up global hotkeys for specific actions.

        Args:
            None

        Returns:
            None
        """

        self.console.clear()
        self.console.print(
            ":play_or_pause_button:  [yellow]Typing Assist Started..[/]",
            justify="center",
        )
        with keyboard.GlobalHotKeys(
            {"<f9>": self.on_f9, "<f10>": self.on_f10, "<esc>": self.on_esc}
        ) as h:
            h.join()
