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
        """Calculates exact Shannon entropy in bits for a given password string."""
        if not password:
            return 0, 0

        length = len(password)

        # 1. Count occurrences of each character
        char_counts = {}
        for char in password:
            char_counts[char] = char_counts.get(char, 0) + 1

        # 2. Compute Shannon Entropy: -sum(P(x) * log2(P(x)))
        shannon_entropy = 0.0
        for count in char_counts.values():
            p = count / length
            shannon_entropy -= p * math.log2(p)

        # 3. Total bits = entropy per character * total character count
        total_bits = shannon_entropy * length

        return round(total_bits), length

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

        # KeePass standard thresholds: 
        # < 64 (Very Weak), 64-80 (Weak), 80-112 (Moderate), 112-128 (Strong), >= 128 (Very Strong)
        if bits < 64:
            bar_color = "#ff4d4d"  # Very Weak (Red)
        elif bits < 80:
            bar_color = "#ff9900"  # Weak (Orange)
        elif bits < 112:
            bar_color = "#ffcc00"  # Moderate (Yellow)
        elif bits < 128:
            bar_color = "#99cc00"  # Strong (Light Green)
        else:
            bar_color = "#00cc44"  # Very Strong (Dark Green)

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