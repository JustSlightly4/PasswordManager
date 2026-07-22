import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import apsw


def new_database(root):
    db_path = filedialog.asksaveasfilename(
        defaultextension=".db",
        filetypes=[("Database Files", "*.db"), ("All Files", "*.*")],
        title="Create New Password Database",
    )

    if not db_path:
        return

    add_win = tk.Toplevel(root)
    add_win.title("Create Master Key")
    add_win.geometry("400x180")
    add_win.resizable(False, False)
    add_win.grab_set()
    add_win.transient(root)

    form_frame = ttk.Frame(add_win, padding=15)
    form_frame.pack(fill="both", expand=True)
    form_frame.columnconfigure(1, weight=1)

    # Master Password Entry
    ttk.Label(form_frame, text="Master Password:").grid(
        row=0, column=0, sticky="w", pady=5
    )
    password_entry = ttk.Entry(form_frame, show="*")
    password_entry.grid(row=0, column=1, sticky="ew", pady=5)
    password_entry.focus_set()

    # Master Password Repeat Entry
    ttk.Label(form_frame, text="Repeat Password:").grid(
        row=1, column=0, sticky="w", pady=5
    )
    repeat_password_entry = ttk.Entry(form_frame, show="*")
    repeat_password_entry.grid(row=1, column=1, sticky="ew", pady=5)

    def create_database():
        master_key = password_entry.get()
        repeat_key = repeat_password_entry.get()

        if not master_key:
            messagebox.showerror(
                "Error", "Master password cannot be empty!", parent=add_win
            )
            return

        if master_key != repeat_key:
            messagebox.showerror(
                "Error", "Passwords do not match!", parent=add_win
            )
            return

        try:
            close_database(root)

            # Open connection using apsw
            root.conn = apsw.Connection(db_path)

            # Set cipher to SQLCipher (AES-256) and pass key via APSW pragma method
            root.conn.pragma("cipher", "sqlcipher")
            root.conn.pragma("key", master_key)

            cursor = root.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL UNIQUE,
                    username TEXT,
                    password TEXT,
                    url TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            clear_table(root.database_table)

            messagebox.showinfo(
                "Success", "Database created successfully!", parent=root
            )
            add_win.destroy()

        except Exception as e:
            messagebox.showerror(
                "Error", f"Failed to create database: {e}", parent=add_win
            )
            close_database(root)
            if os.path.exists(db_path):
                os.remove(db_path)

    btn_frame = ttk.Frame(form_frame)
    btn_frame.grid(row=2, column=0, columnspan=2, pady=(15, 0), sticky="e")

    cancel_btn = ttk.Button(btn_frame, text="Cancel", command=add_win.destroy)
    cancel_btn.pack(side="right", padx=(5, 0))

    create_btn = ttk.Button(
        btn_frame, text="Create Database", command=create_database
    )
    create_btn.pack(side="right")

    add_win.bind("<Return>", lambda event: create_database())

def open_database(root):
    # 1. Prompt user to select an existing database file
    db_path = filedialog.askopenfilename(
        filetypes=[("Database Files", "*.db"), ("All Files", "*.*")],
        title="Open Password Database"
    )
    
    if not db_path:
        return  # User canceled file selection

    # 2. Prompt user for the master password
    pass_win = tk.Toplevel(root)
    pass_win.title("Enter Master Password")
    pass_win.geometry("350x130")
    pass_win.resizable(False, False)
    pass_win.grab_set()
    pass_win.transient(root)

    form_frame = ttk.Frame(pass_win, padding=15)
    form_frame.pack(fill="both", expand=True)
    form_frame.columnconfigure(1, weight=1)

    ttk.Label(form_frame, text="Master Password:").grid(row=0, column=0, sticky="w", pady=5)
    password_entry = ttk.Entry(form_frame, show="*")
    password_entry.grid(row=0, column=1, sticky="ew", pady=5)
    password_entry.focus_set()

    def unlock():
        master_key = password_entry.get()
        if not master_key:
            messagebox.showerror("Error", "Password cannot be empty!", parent=pass_win)
            return

        try:
            # Close existing connection if any
            if root.conn is not None:
                close_database(root)

            root.conn = apsw.Connection(db_path)

            # Set cipher and pass key safely using APSW's pragma method
            root.conn.pragma("cipher", "sqlcipher")
            root.conn.pragma("key", master_key)

            cursor = root.conn.cursor()
            # Force a read against sqlite_master to verify key correctness
            cursor.execute("SELECT count(*) FROM sqlite_master;")

            populate_table(root)
            pass_win.destroy()
            messagebox.showinfo("Success", "Database unlocked successfully!", parent=root)

        except apsw.SQLError:
            messagebox.showerror("Error", "Incorrect master password or corrupt database.", parent=pass_win)
            close_database(root)

    btn_frame = ttk.Frame(form_frame)
    btn_frame.grid(row=1, column=0, columnspan=2, pady=(15, 0), sticky="e")

    cancel_btn = ttk.Button(btn_frame, text="Cancel", command=pass_win.destroy)
    cancel_btn.pack(side="right", padx=(5, 0))

    open_btn = ttk.Button(btn_frame, text="Unlock", command=unlock)
    open_btn.pack(side="right")

    pass_win.bind("<Return>", lambda event: unlock())

def clear_table(tree):
    """Deletes all items/rows from a Treeview table."""
    for item in tree.get_children():
        tree.delete(item)

def close_database(root):
    if root.conn is not None:
        root.conn.close()
        root.conn = None
        clear_table(root.database_table)


def save_database(root):
    if root.conn is None:
        messagebox.showwarning("Warning", "No database is currently open.")
        return

    try:
        # Note: APSW autocommits by default outside of explicit transactions.
        # Running COMMIT manually is only needed inside a manual transaction block.
        print("Database changes saved to disk.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save database: {e}")


def populate_table(root):
    for row in root.database_table.get_children():
        root.database_table.delete(row)

    cursor = root.conn.cursor()
    cursor.execute("""
        SELECT title, username, url, notes
        FROM users
    """)

    for row in cursor.fetchall():
        root.database_table.insert("", "end", values=row)


def open_add_entry_window(root):
    if root.conn is None:
        messagebox.showwarning(
            "No Database", "Please open or create a database first!"
        )
        return

    add_win = tk.Toplevel(root)
    add_win.title("Add Entry")
    add_win.geometry("400x380")
    add_win.resizable(False, False)
    add_win.grab_set()
    add_win.transient(root)

    form_frame = ttk.Frame(add_win, padding=15)
    form_frame.pack(fill="both", expand=True)
    form_frame.columnconfigure(1, weight=1)

    # Form Fields
    ttk.Label(form_frame, text="Title:").grid(
        row=0, column=0, sticky="w", pady=5
    )
    title_entry = ttk.Entry(form_frame)
    title_entry.grid(row=0, column=1, sticky="ew", pady=5)

    ttk.Label(form_frame, text="Username:").grid(
        row=1, column=0, sticky="w", pady=5
    )
    username_entry = ttk.Entry(form_frame)
    username_entry.grid(row=1, column=1, sticky="ew", pady=5)

    ttk.Label(form_frame, text="Password:").grid(
        row=2, column=0, sticky="w", pady=5
    )
    password_entry = ttk.Entry(form_frame, show="*")
    password_entry.grid(row=2, column=1, sticky="ew", pady=5)

    ttk.Label(form_frame, text="Repeat Password:").grid(
        row=3, column=0, sticky="w", pady=5
    )
    repeat_password_entry = ttk.Entry(form_frame, show="*")
    repeat_password_entry.grid(row=3, column=1, sticky="ew", pady=5)

    ttk.Label(form_frame, text="URL:").grid(row=4, column=0, sticky="w", pady=5)
    url_entry = ttk.Entry(form_frame)
    url_entry.grid(row=4, column=1, sticky="ew", pady=5)

    ttk.Label(form_frame, text="Notes:").grid(
        row=5, column=0, sticky="nw", pady=5
    )
    notes_entry = tk.Text(form_frame, width=20, height=4, font=("Segoe UI", 9))
    notes_entry.grid(row=5, column=1, sticky="ew", pady=5)

    def save_entry():
        title = title_entry.get().strip()
        username = username_entry.get().strip()
        pwd = password_entry.get()
        repeat_pwd = repeat_password_entry.get()
        url = url_entry.get().strip()
        notes = notes_entry.get("1.0", tk.END).strip()

        if not title:
            messagebox.showerror("Error", "Title is required!", parent=add_win)
            return

        if pwd != repeat_pwd:
            messagebox.showerror(
                "Error", "Passwords do not match!", parent=add_win
            )
            return

        try:
            cursor = root.conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (title, username, password, url, notes)
                VALUES (?, ?, ?, ?, ?)
            """,
                (title, username, pwd, url, notes),
            )

            populate_table(root)
            add_win.destroy()

        except apsw.ConstraintError:
            messagebox.showerror(
                "Error",
                f"An entry titled '{title}' already exists.",
                parent=add_win,
            )
        except Exception as e:
            messagebox.showerror(
                "Error", f"Failed to save entry: {e}", parent=add_win
            )

    btn_frame = ttk.Frame(form_frame)
    btn_frame.grid(row=6, column=0, columnspan=2, pady=(15, 0), sticky="e")

    cancel_btn = ttk.Button(btn_frame, text="Cancel", command=add_win.destroy)
    cancel_btn.pack(side="right", padx=(5, 0))

    save_btn = ttk.Button(btn_frame, text="Save Entry", command=save_entry)
    save_btn.pack(side="right")