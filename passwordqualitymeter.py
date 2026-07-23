import math
import string
import tkinter as tk
from tkinter import ttk

import math
import string
import tkinter as tk
from tkinter import ttk


class PasswordQualityMeter(ttk.Frame):
    """Reusable widget for displaying password entropy quality bar and character count."""

    def __init__(self, parent, entry_widget=None, max_bits=128, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.entry_widget = entry_widget
        self.max_bits = max_bits

        # Quality meter canvas
        self.quality_bar = tk.Canvas(
            self,
            height=18,
            bg="#e0e0e0",
            highlightthickness=1,
            highlightbackground="#a0a0a0",
        )
        self.quality_bar.pack(side="left", fill="x", expand=True)

        # Character length label
        self.lbl_ch = ttk.Label(self, text="0 ch.", font=("Segoe UI", 8))
        self.lbl_ch.pack(side="right", padx=(8, 0))

        # Handle window resizes
        self.quality_bar.bind("<Configure>", lambda e: self.update_meter())

        # Bind target entry widget if supplied during initialization
        if self.entry_widget:
            self.attach_entry(self.entry_widget)

    @staticmethod
    def calculate_entropy(password):
        """Calculates entropy in bits based on character set size and length."""
        if not password:
            return 0, 0

        has_lowercase = any(c in string.ascii_lowercase for c in password)
        has_uppercase = any(c in string.ascii_uppercase for c in password)
        has_digits = any(c in string.digits for c in password)
        has_symbols = any(c in string.punctuation for c in password)

        charset_size = 0
        if has_lowercase:
            charset_size += 26
        if has_uppercase:
            charset_size += 26
        if has_digits:
            charset_size += 10
        if has_symbols:
            charset_size += 32  # standard punctuation set count

        # Fallback for any non-standard unicode characters
        if charset_size == 0:
            charset_size = 256

        # Entropy (bits) = Length * log2(Charset Size)
        entropy_bits = round(len(password) * math.log2(charset_size))
        return entropy_bits, len(password)

    def attach_entry(self, entry_widget):
        """Bind live updates to a specific Entry widget."""
        self.entry_widget = entry_widget
        self.entry_widget.bind(
            "<KeyRelease>", lambda e: self.update_meter(), add="+"
        )

    def update_meter(self, password=None):
        """Calculate entropy and update canvas graphics & character label."""
        if password is None and self.entry_widget:
            password = self.entry_widget.get()
        elif password is None:
            password = ""

        bits, ch_count = self.calculate_entropy(password)
        self.lbl_ch.config(text=f"{ch_count} ch.")

        # Canvas redrawing logic
        self.quality_bar.delete("all")
        canvas_width = self.quality_bar.winfo_width()
        if canvas_width <= 1:
            canvas_width = 240

        fill_ratio = min(bits / float(self.max_bits), 1.0)
        fill_width = int(canvas_width * fill_ratio)

        # Dynamic color thresholding
        if bits < 40:
            bar_color = "#ff4d4d"  # Red
        elif bits < 64:
            bar_color = "#ff9900"  # Orange
        elif bits < 80:
            bar_color = "#ffcc00"  # Yellow
        elif bits < 100:
            bar_color = "#99cc00"  # Light Green
        else:
            bar_color = "#00cc44"  # Dark Green

        if fill_width > 0:
            self.quality_bar.create_rectangle(
                0, 0, fill_width, 18, fill=bar_color, outline=""
            )

        # Text overlay
        self.quality_bar.create_text(
            canvas_width // 2,
            9,
            text=f"{bits} bits",
            font=("Segoe UI", 8, "bold"),
            fill="black",
        )