import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import apsw
import math
import string
import json
from passwordqualitymeter import PasswordQualityMeter
from passwordgenerator import PasswordGenerator
import tooltips as tt

PROFILES_FILE = "profiles.json"

def confirm_weak_password(parent_window, bits, threshold=80):
    """
    Checks if entropy bits are below threshold. If so, shows a confirmation dialog.
    Returns True if password is acceptable (or user confirms usage anyway), False otherwise.
    """
    if bits >= threshold:
        return True  # Password meets standard, no warning needed

    message = (
        "The specified master password is weak.\n\n"
        "Are you sure that you want to use this master password?"
    )
    
    return messagebox.askyesno(
        "Weak Password Warning",
        message,
        icon="warning",
        parent=parent_window
    )

# Updates the main window title bar to include the open database name
def update_window_title(root, db_path=None):
    base_title = "Password Manager"
    if db_path:
        file_name = os.path.basename(db_path)
        root.title(f"{file_name} - {base_title}")
    else:
        root.title(base_title)

def new_database(root):
    # Opens the file system to search for a place for the file
    db_path = filedialog.asksaveasfilename(
        defaultextension=".db",
        filetypes=[("Database Files", "*.db"), ("All Files", "*.*")],
        title="Create New Password Database",
    )

    # If user backed out, end function
    if not db_path:
        return

    intro_text = (
        "Specify a new master key, which will be used to encrypt the database.\n\n"
        "A master key consists of one or more of the following components. "
        "All components that you specify will be required to open the database. "
        "If you lose one component, you will not be able to open the database anymore."
    )

    def on_create(master_key, dialog):
        try:
            close_database(root)

            root.conn = apsw.Connection(db_path)
            root.conn.pragma("cipher", "sqlcipher")
            root.conn.pragma("key", master_key)

            root.master_key = master_key
            cursor = root.conn.cursor()

            cursor.execute("BEGIN IMMEDIATE;")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL UNIQUE,
                    username TEXT,
                    password TEXT,
                    url TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            sample_entries = [
                ("Sample Entry", "User Name", "Password", "", "Notes"),
                ("Sample Entry #2", "Michael321", "12345", "", ""),
            ]

            cursor.executemany(
                """
                INSERT INTO users (title, username, password, url, notes)
                VALUES (?, ?, ?, ?, ?)
            """,
                sample_entries,
            )

            cursor.execute("COMMIT;")
            cursor.execute("BEGIN IMMEDIATE;")

            clear_table(root.database_table)
            populate_table(root)
            update_window_title(root, db_path)

            messagebox.showinfo("Success", "Database created successfully!", parent=root)
            dialog.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to create database: {e}", parent=dialog)
            close_database(root)
            if os.path.exists(db_path):
                os.remove(db_path)

    show_master_key_dialog(
        root=root,
        title="Create Master Key",
        subtitle_path=db_path,
        intro_text=intro_text,
        ok_button_text="OK",
        on_submit=on_create,
    )

#Open a database from the file system
def open_database(root):
    #Get the user to select an existing database file
    db_path = filedialog.askopenfilename(
        filetypes=[("Database Files", "*.db"), ("All Files", "*.*")],
        title="Open Password Database"
    )
    
    #If user backed out, end function
    if not db_path:
        return

    #Fields to enter the database base password
    pass_win = tk.Toplevel(root)
    pass_win.title("Enter Master Password")
    pass_win.geometry("350x160")
    pass_win.resizable(False, False)
    pass_win.grab_set()
    pass_win.transient(root)

    # ==================== HEADER BANNER ====================
    header_frame = tk.Frame(pass_win, bg="#1b2a47", height=60)
    header_frame.pack(side="top", fill="x")
    header_frame.pack_propagate(False)

    title_label = tk.Label(
        header_frame,
        text="Enter Master Password",
        font=("Segoe UI", 12, "bold"),
        fg="white",
        bg="#1b2a47",
    )
    title_label.pack(anchor="w", padx=15, pady=(8, 0))

    path_label = tk.Label(
        header_frame,
        text=os.path.basename(db_path),
        font=("Segoe UI", 8),
        fg="#a2b3d1",
        bg="#1b2a47",
    )
    path_label.pack(anchor="w", padx=15, pady=(2, 5))

    accent_bar = tk.Frame(pass_win, bg="#e67e22", height=2)
    accent_bar.pack(side="top", fill="x")

    form_frame = ttk.Frame(pass_win, padding=15)
    form_frame.pack(fill="both", expand=True)
    form_frame.columnconfigure(1, weight=1)

    ttk.Label(form_frame, text="Master Password:").grid(row=0, column=0, sticky="w", pady=5)
    password_entry = ttk.Entry(form_frame, show="*")
    password_entry.grid(row=0, column=1, sticky="ew", pady=5)
    password_entry.focus_set()

    #Attempts to unlock a database with a given password
    def unlock():
        #Get the password from the entry field
        master_key = password_entry.get()

        try:
            #Close existing connection
            close_database(root)

            #Establish connection with database
            root.conn = apsw.Connection(db_path)

            #Set cipher and pass key safely using APSW's pragma method
            root.conn.pragma("cipher", "sqlcipher")
            root.conn.pragma("key", master_key)

            cursor = root.conn.cursor()

            #Force a read against sqlite_master to verify key correctness
            cursor.execute("SELECT count(*) FROM sqlite_master;")

            root.master_key = master_key

            #1. Start an explicit transaction to pause auto-saving
            cursor.execute("BEGIN IMMEDIATE;")

            #Populate the table with the information from the database
            populate_table(root)
            update_window_title(root, db_path)

            #Get rid of the popup window
            pass_win.destroy()

        #If there is an error of some kind catch the exception, show an error, and close database
        except apsw.Error:
            messagebox.showerror(
                "Error",
                f"{db_path}\n\n" 
                "Failed to load the specified file!\n\n"
                "The master key is invalid!\n\n"
                "Make sure that the master key is correct and try it again.", 
                parent=pass_win
            )
            close_database(root)

    #Buttons for canceling the form and to attempt to unlock the database
    btn_frame = ttk.Frame(form_frame)
    btn_frame.grid(row=1, column=0, columnspan=2, pady=(15, 0), sticky="e")

    cancel_btn = ttk.Button(btn_frame, text="Cancel", command=pass_win.destroy)
    cancel_btn.pack(side="right", padx=(5, 0))

    open_btn = ttk.Button(btn_frame, text="OK", command=unlock)
    open_btn.pack(side="right")

    pass_win.bind("<Return>", lambda event: unlock()) #Pressing enter will unlock the database

#Deletes all items/rows from a Treeview table.
def clear_table(tree):
    for item in tree.get_children():
        tree.delete(item)

    # Reset status bar if available
    if hasattr(tree.winfo_toplevel(), "status_label"):
        tree.winfo_toplevel().status_label.config(text="0 of 0 selected")

#Closes a database if it has a connection
def close_database(root):
    if root.conn is not None:
        try:
            cursor = root.conn.cursor()
            #Cancel any unsaved changes before closing connection
            cursor.execute("ROLLBACK;")
        except Exception:
            pass  #Fail gracefully if no transaction was active
        
        root.conn.close()
        root.conn = None
        root.master_key = None
        clear_table(root.database_table)
        update_window_title(root, None)

#Saves a database file
def save_database(root):
    if root.conn is None:
        messagebox.showwarning("Warning", "No database is currently open.")
        return

    try:
        cursor = root.conn.cursor()
        
        #1. Commit all uncommitted changes (new entries, edits, etc.)
        cursor.execute("COMMIT;")
        
        #2. Re-open a transaction for future uncommitted edits
        cursor.execute("BEGIN IMMEDIATE;")
        
        messagebox.showinfo("Saved", "Database changes saved to disk.", parent=root)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save database: {e}", parent=root)

# Saves the current database under a new file path without prompting for the key again
def save_as_database(root):
    if root.conn is None:
        messagebox.showwarning("Warning", "No database is currently open.", parent=root)
        return

    # Check if we have the active master key stored
    if not hasattr(root, "master_key") or not root.master_key:
        messagebox.showerror("Error", "Master key is missing or invalid.", parent=root)
        return

    # Ask the user where to save the new copy
    new_db_path = filedialog.asksaveasfilename(
        defaultextension=".db",
        filetypes=[("Database Files", "*.db"), ("All Files", "*.*")],
        title="Save Database As...",
        parent=root
    )

    if not new_db_path:
        return

    # If destination file already exists, remove it first (VACUUM INTO requires target path to be clean)
    if os.path.exists(new_db_path):
        try:
            os.remove(new_db_path)
        except Exception as e:
            messagebox.showerror("Error", f"Could not prepare destination file: {e}", parent=root)
            return

    # Store master key in local variable before close_database clears it
    current_key = root.master_key

    try:
        cursor = root.conn.cursor()

        # 1. Commit active transaction so all pending changes are written
        cursor.execute("COMMIT;")

        # 2. Create an encrypted duplicate of the current database at the new path using parameter binding
        cursor.execute("VACUUM INTO ?;", (new_db_path,))

        # 3. Close old connection (this sets root.master_key = None internally)
        close_database(root)

        # 4. Connect to the newly created database file using stored key
        root.conn = apsw.Connection(new_db_path)
        root.conn.pragma("cipher", "sqlcipher")
        root.conn.pragma("key", current_key)

        # Restore key back to root object
        root.master_key = current_key

        # 5. Re-open transaction on the new connection
        new_cursor = root.conn.cursor()
        new_cursor.execute("BEGIN IMMEDIATE;")

        # Refresh UI table view
        populate_table(root)
        update_window_title(root, new_db_path)

        messagebox.showinfo("Success", f"Database successfully saved as:\n{new_db_path}", parent=root)

    except Exception as e:
        # Re-open transaction on old connection if save failed
        try:
            if root.conn:
                root.conn.cursor().execute("BEGIN IMMEDIATE;")
        except Exception:
            pass

        messagebox.showerror("Error", f"Failed to perform Save As: {e}", parent=root)

# Populates the table with the data from a database
def populate_table(root):
    for row in root.database_table.get_children():
        root.database_table.delete(row)

    cursor = root.conn.cursor()
    cursor.execute("""
        SELECT title, username, password, url, notes
        FROM users
    """)

    for row in cursor.fetchall():
        title, username, password, url, notes = row
        display_password = "********" if password else ""
        root.database_table.insert("", "end", values=(title, username, display_password, url, notes))
    
    # Update selection status back to zero
    update_status_bar(root)

def add_entry(root):
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

    #Form Fields
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

# Deletes the selected entry/entries from the database
def delete_entry(root):
    if root.conn is None:
        messagebox.showwarning("Warning", "No database is currently open.", parent=root)
        return

    selected_items = root.database_table.selection()
    if not selected_items:
        messagebox.showinfo("Information", "Please select an entry to delete.", parent=root)
        return

    # Gather titles for all selected rows
    titles_to_delete = []
    for item in selected_items:
        values = root.database_table.item(item, "values")
        titles_to_delete.append(values[0])

    # Build confirmation prompt
    if len(titles_to_delete) == 1:
        msg = f"Are you sure you want to delete '{titles_to_delete[0]}'?"
    else:
        msg = f"Are you sure you want to delete these {len(titles_to_delete)} entries?\n\n" + \
              "\n".join(f"• {t}" for t in titles_to_delete[:5])
        if len(titles_to_delete) > 5:
            msg += f"\n...and {len(titles_to_delete) - 5} more."

    confirm = messagebox.askyesno("Confirm Delete", msg, icon="warning", parent=root)
    if not confirm:
        return

    try:
        cursor = root.conn.cursor()

        # Delete all target records
        for title in titles_to_delete:
            cursor.execute("DELETE FROM users WHERE title = ?", (title,))

        # Refresh table view and status bar
        populate_table(root)

    except Exception as e:
        messagebox.showerror("Error", f"Failed to delete entry: {e}", parent=root)

# Duplicates the currently selected entry in the database
def duplicate_entry(root):
    if root.conn is None:
        messagebox.showwarning("Warning", "No database is currently open.", parent=root)
        return

    selected_item = root.database_table.selection()
    if not selected_item:
        messagebox.showinfo("Information", "Please select an entry to duplicate.", parent=root)
        return

    # Get title from selected row (column index 0)
    values = root.database_table.item(selected_item[0], "values")
    original_title = values[0]

    cursor = root.conn.cursor()

    # Fetch original row details from SQLite
    cursor.execute(
        "SELECT username, password, url, notes FROM users WHERE title = ?",
        (original_title,)
    )
    result = cursor.fetchone()

    if not result:
        messagebox.showerror("Error", "Could not find the selected record in the database.", parent=root)
        return

    username, password, url, notes = result

    # Generate a unique copy title (e.g., "My Account - Copy")
    base_copy_title = f"{original_title} - Copy"
    new_title = base_copy_title
    counter = 2

    # Loop to check if "Title - Copy" already exists to avoid UNIQUE constraint errors
    while True:
        cursor.execute("SELECT COUNT(*) FROM users WHERE title = ?", (new_title,))
        if cursor.fetchone()[0] == 0:
            break
        new_title = f"{base_copy_title} ({counter})"
        counter += 1

    try:
        cursor.execute(
            """
            INSERT INTO users (title, username, password, url, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (new_title, username, password, url, notes)
        )

        # Refresh the UI table view
        populate_table(root)

    except Exception as e:
        messagebox.showerror("Error", f"Failed to duplicate entry: {e}", parent=root)

# Copies the username of the selected row to the clipboard
def copy_username(root):
    if root.conn is None:
        messagebox.showwarning("Warning", "No database is open.")
        return

    # Get selected item from the Treeview
    selected_item = root.database_table.selection()
    if not selected_item:
        messagebox.showinfo("Information", "Please select an entry first.")
        return

    # Extract title from the selected row (column index 0 is 'title')
    values = root.database_table.item(selected_item[0], "values")
    title = values[0]

    # Query the real database record to get the exact unmasked data
    cursor = root.conn.cursor()
    cursor.execute("SELECT username FROM users WHERE title = ?", (title,))
    result = cursor.fetchone()

    if result and result[0]:
        root.clipboard_clear()
        root.clipboard_append(result[0])
        root.update()  # Keeps clipboard content active after window focus shifts


# Copies the password of the selected row to the clipboard
def copy_password(root):
    if root.conn is None:
        messagebox.showwarning("Warning", "No database is open.")
        return

    # Get selected item from the Treeview
    selected_item = root.database_table.selection()
    if not selected_item:
        messagebox.showinfo("Information", "Please select an entry first.")
        return

    # Extract title from the selected row
    values = root.database_table.item(selected_item[0], "values")
    title = values[0]

    # Query database for the raw password (bypassing table masking)
    cursor = root.conn.cursor()
    cursor.execute("SELECT password FROM users WHERE title = ?", (title,))
    result = cursor.fetchone()

    if result and result[0]:
        root.clipboard_clear()
        root.clipboard_append(result[0])
        root.update()  # Keeps clipboard content active after window focus shifts

# Updates the bottom status bar with the selection count and total entries count
def update_status_bar(root):
    # Total entries currently displayed in the Treeview table
    total_entries = len(root.database_table.get_children())
    
    # Selected entries count
    selected_count = len(root.database_table.selection())

    # Format the message (e.g., "2 of 5 selected")
    root.status_label.config(text=f"{selected_count} of {total_entries} selected")

# Changes the master key/password for the active database
def change_master_key(root):
    if root.conn is None:
        messagebox.showwarning("Warning", "No database is currently open.", parent=root)
        return

    db_path = getattr(root, "db_path", "Active Database")
    intro = (
        "Specify a new master key, which will be used to re-encrypt the database.\n\n"
        "A master key consists of one or more of the following components. "
        "All components that you specify will be required to open the database. "
        "If you lose one component, you will not be able to open the database anymore."
    )

    def on_change(new_key, dialog):
        try:
            cursor = root.conn.cursor()

            # 1. Commit active transaction so database file state is clean
            cursor.execute("COMMIT;")

            # 2. Re-encrypt database with SQLCipher's PRAGMA rekey
            cursor.execute(f"PRAGMA rekey = '{new_key}';")

            # 3. Update session master key
            root.master_key = new_key

            # 4. Re-open transaction
            cursor.execute("BEGIN IMMEDIATE;")

            messagebox.showinfo("Success", "Master key changed successfully!", parent=root)
            dialog.destroy()
        except Exception as e:
            try:
                root.conn.cursor().execute("BEGIN IMMEDIATE;")
            except Exception:
                pass
            messagebox.showerror("Error", f"Failed to change master key: {e}", parent=dialog)

    show_master_key_dialog(
        root=root,
        title="Change Master Key",
        subtitle_path=db_path,
        intro_text=intro,
        ok_button_text="OK",
        on_submit=on_change,
    )

# Selects all rows currently displayed in the table
def select_all(root):
    if root.conn is None:
        return

    # Get all item IDs in the Treeview
    all_items = root.database_table.get_children()
    if not all_items:
        return

    # Set selection to all items
    root.database_table.selection_set(all_items)

    # Focus on the first item so keyboard navigation continues to work smoothly
    root.database_table.focus(all_items[0])

    # Manually trigger status bar update since setting selection programmatically
    # doesn't always automatically fire the <<TreeviewSelect>> event on all OS versions
    update_status_bar(root)

def show_master_key_dialog(
    root,
    title,
    subtitle_path,
    intro_text,
    ok_button_text="OK",
    on_submit=None,
):
    """
    Reusable popup dialog for setting or changing a master key.
    Handles layout, toggle show/hide, repeat password validation,
    and weak password confirmation dialogs.
    """
    dialog = tk.Toplevel(root)
    dialog.title(title)
    dialog.geometry("520x540")
    dialog.resizable(False, False)
    dialog.grab_set()
    dialog.transient(root)
    dialog.configure(bg="#f0f0f0")

    # ==================== HEADER BANNER ====================
    header_frame = tk.Frame(dialog, bg="#1b2a47", height=70)
    header_frame.pack(side="top", fill="x")
    header_frame.pack_propagate(False)

    title_label = tk.Label(
        header_frame,
        text=title,
        font=("Segoe UI", 13, "bold"),
        fg="white",
        bg="#1b2a47",
    )
    title_label.pack(anchor="w", padx=20, pady=(10, 0))

    path_label = tk.Label(
        header_frame,
        text=subtitle_path,
        font=("Segoe UI", 8),
        fg="#a2b3d1",
        bg="#1b2a47",
    )
    path_label.pack(anchor="w", padx=20, pady=(2, 5))

    accent_bar = tk.Frame(dialog, bg="#e67e22", height=2)
    accent_bar.pack(side="top", fill="x")

    # ==================== MAIN CONTENT ====================
    main_frame = ttk.Frame(dialog, padding=20)
    main_frame.pack(side="top", fill="both", expand=True)

    desc_label = ttk.Label(
        main_frame, text=intro_text, wraplength=460, justify="left"
    )
    desc_label.pack(anchor="w", pady=(0, 15))

    # ---------- FORM ROW LAYOUT ----------
    form_grid = ttk.Frame(main_frame)
    form_grid.pack(fill="x", pady=5)
    form_grid.columnconfigure(1, weight=1)

    # Master Password Row
    ttk.Label(
        form_grid, text="Master password:", font=("Segoe UI", 9, "bold")
    ).grid(row=0, column=0, sticky="e", padx=(0, 10), pady=5)

    password_entry = ttk.Entry(form_grid, show="•")
    password_entry.grid(row=0, column=1, sticky="ew", pady=5)
    password_entry.focus_set()

    # Toggle show/hide password button
    def toggle_show_password():
        show_char = "" if password_entry.cget("show") == "•" else "•"
        password_entry.config(show=show_char)
        repeat_entry.config(show=show_char)

    btn_show = tk.Button(
        form_grid,
        text="•••",
        width=3,
        relief="groove",
        bd=1,
        command=toggle_show_password,
    )
    btn_show.grid(row=0, column=2, padx=(4, 0), pady=5)

    # Repeat Password Row
    ttk.Label(form_grid, text="Repeat password:").grid(
        row=1, column=0, sticky="e", padx=(0, 10), pady=5
    )
    repeat_entry = tk.Entry(
        form_grid, show="•", bg="#ffcccc", relief="solid", bd=1
    )
    repeat_entry.grid(row=1, column=1, sticky="ew", pady=5)

    # Estimated Quality Row
    ttk.Label(form_grid, text="Estimated quality:").grid(
        row=2, column=0, sticky="e", padx=(0, 10), pady=5
    )
    quality_meter = PasswordQualityMeter(
        form_grid, entry_widget=password_entry
    )
    quality_meter.grid(row=2, column=1, sticky="ew", pady=5)

    # Repeat Password Validation
    def validate_repeat_password(event=None):
        p1 = password_entry.get()
        p2 = repeat_entry.get()
        if p2 == "":
            repeat_entry.config(bg="#ffcccc")
        elif p1 == p2:
            repeat_entry.config(bg="#ffffff")
        else:
            repeat_entry.config(bg="#ffcccc")

    password_entry.bind("<KeyRelease>", validate_repeat_password, add="+")
    repeat_entry.bind("<KeyRelease>", validate_repeat_password, add="+")

    # ==================== BOTTOM BAR ====================
    sep = ttk.Separator(dialog, orient="horizontal")
    sep.pack(side="bottom", fill="x")

    btn_bar = ttk.Frame(dialog, padding=(12, 10))
    btn_bar.pack(side="bottom", fill="x")

    def handle_submit():
        new_pwd = password_entry.get()
        repeat_pwd = repeat_entry.get()

        if not new_pwd:
            messagebox.showerror(
                "Error", "Master password cannot be empty!", parent=dialog
            )
            return

        if new_pwd != repeat_pwd:
            messagebox.showerror(
                "Error", "Passwords do not match!", parent=dialog
            )
            return

        # Check weak password threshold (< 80 bits)
        bits, _ = PasswordQualityMeter.calculate_entropy(new_pwd)
        if not confirm_weak_password(dialog, bits, threshold=80):
            return

        # Trigger database logic passed by caller
        if on_submit:
            on_submit(new_pwd, dialog)

    # Action Buttons
    cancel_btn = ttk.Button(
        btn_bar, text="Cancel", width=10, command=dialog.destroy
    )
    cancel_btn.pack(side="right", padx=(5, 0))

    ok_btn = ttk.Button(
        btn_bar, text=ok_button_text, width=10, command=handle_submit
    )
    ok_btn.pack(side="right")

    dialog.bind("<Return>", lambda event: handle_submit())
    dialog.after(10, quality_meter.update_meter)

def show_entry_dialog(root, is_edit=False, item_id=None):
    """
    Reusable dialog for both Add Entry and Edit Entry matching KeePass UI.
    """
    if root.conn is None:
        messagebox.showwarning("No Database", "Please open or create a database first!")
        return

    dialog_title = "Edit Entry" if is_edit else "Add Entry"
    subtitle = "Edit an existing entry." if is_edit else "Create a new entry."

    dialog = tk.Toplevel(root)
    dialog.title(dialog_title)
    dialog.geometry("540x560")
    dialog.resizable(False, False)
    dialog.grab_set()
    dialog.transient(root)
    dialog.configure(bg="#f0f0f0")

    # ==================== HEADER BANNER ====================
    header_frame = tk.Frame(dialog, bg="#323e51", height=70)
    header_frame.pack(side="top", fill="x")
    header_frame.pack_propagate(False)

    title_label = tk.Label(
        header_frame,
        text=dialog_title,
        font=("Segoe UI", 13, "bold"),
        fg="white",
        bg="#323e51",
    )
    title_label.pack(anchor="w", padx=15, pady=(10, 0))

    sub_label = tk.Label(
        header_frame,
        text=subtitle,
        font=("Segoe UI", 9),
        fg="#d0d7de",
        bg="#323e51",
    )
    sub_label.pack(anchor="w", padx=15, pady=(2, 5))

    accent_bar = tk.Frame(dialog, bg="#e67e22", height=2)
    accent_bar.pack(side="top", fill="x")

    # ==================== TABBED NOTEBOOK ====================
    notebook = ttk.Notebook(dialog)
    notebook.pack(fill="both", expand=True, padx=8, pady=8)

    tab_general = ttk.Frame(notebook, padding=12)

    notebook.add(tab_general, text="General")

    # ==================== GENERAL TAB CONTENT ====================
    tab_general.columnconfigure(1, weight=1)

    # 1. Title Row
    ttk.Label(tab_general, text="Title:").grid(row=0, column=0, sticky="w", pady=4)
    title_entry = ttk.Entry(tab_general)
    title_entry.grid(row=0, column=1, columnspan=2, sticky="ew", pady=4)

    # 2. Username Row
    ttk.Label(tab_general, text="User name:").grid(row=1, column=0, sticky="w", pady=4)
    username_entry = ttk.Entry(tab_general)
    username_entry.grid(row=1, column=1, columnspan=2, sticky="ew", pady=4)

    # 3. Password Row
    ttk.Label(tab_general, text="Password:").grid(row=2, column=0, sticky="w", pady=4)
    password_entry = ttk.Entry(tab_general, show="•")
    password_entry.grid(row=2, column=1, sticky="ew", pady=4, padx=(0, 5))

    def toggle_show_password():
        show_char = "" if password_entry.cget("show") == "•" else "•"
        password_entry.config(show=show_char)
        repeat_entry.config(show=show_char)

    # Load the image (use PhotoImage for .gif / .png)
    eye_icon = tk.PhotoImage(file="assets/icons/icon_toggle_password_visibility.png")
    btn_gen = ttk.Button(tab_general, image=eye_icon, width=4, command=toggle_show_password)
    btn_gen.image = eye_icon  # Keep a reference so Python's garbage collector doesn't erase it!
    btn_gen.grid(row=2, column=2, pady=4)
    tt.ToolTip(btn_gen, "Show/hide password using asterisks")

    # 4. Repeat Password Row (tk.Entry used for background highlight)
    ttk.Label(tab_general, text="Repeat:").grid(row=3, column=0, sticky="w", pady=4)
    repeat_entry = tk.Entry(tab_general, show="•", bg="#ffcccc", relief="solid", bd=1)
    repeat_entry.grid(row=3, column=1, sticky="ew", pady=4, padx=(0, 5))

    # ==================== REPEAT PASSWORD HIGHLIGHT VALIDATION ====================
    def validate_repeat_password(event=None):
        p1 = password_entry.get()
        p2 = repeat_entry.get()
        if p2 == "":
            repeat_entry.config(bg="#ffcccc")
        elif p1 == p2:
            repeat_entry.config(bg="#ffffff")
        else:
            repeat_entry.config(bg="#ffcccc")

    password_entry.bind("<KeyRelease>", validate_repeat_password, add="+")
    repeat_entry.bind("<KeyRelease>", validate_repeat_password, add="+")

    def open_password_generator():
        def set_generated_password(gen_pwd):
            # Clear existing text
            password_entry.delete(0, tk.END)
            repeat_entry.delete(0, tk.END)
            
            # Insert generated password
            password_entry.insert(0, gen_pwd)
            repeat_entry.insert(0, gen_pwd)
            
            # Re-trigger validation highlighting & quality meter
            validate_repeat_password()
            quality_meter.update_meter()

        # Launch generator dialog with the callback attached
        show_password_generator_dialog(dialog, callback=set_generated_password)

    icon_password_generator = tk.PhotoImage(file="assets/icons/icon_generate_password.png")
    img_btn_gen_pass = ttk.Button(tab_general, image=icon_password_generator, width=4, command=open_password_generator)
    img_btn_gen_pass.image = icon_password_generator  # Keep a reference so Python's garbage collector doesn't erase it!
    img_btn_gen_pass.grid(row=3, column=2, pady=4)
    tt.ToolTip(img_btn_gen_pass, "Generate a password")

    # 5. Quality Meter Row
    ttk.Label(tab_general, text="Quality:").grid(row=4, column=0, sticky="w", pady=4)
    quality_meter = PasswordQualityMeter(tab_general, entry_widget=password_entry)
    quality_meter.grid(row=4, column=1, sticky="ew", pady=4, padx=(0, 60))

    icon_toggle_quality_estimation = tk.PhotoImage(file="assets/icons/icon_toggle_quality_estimation.png")
    img_btn_toggle_quality_estimation = ttk.Button(tab_general, image=icon_toggle_quality_estimation, width=4, command=open_password_generator)
    img_btn_toggle_quality_estimation.image = icon_toggle_quality_estimation  # Keep a reference so Python's garbage collector doesn't erase it!
    img_btn_toggle_quality_estimation.grid(row=4, column=2, pady=4)
    tt.ToolTip(img_btn_toggle_quality_estimation, "Generate a password")

    # 6. URL Row
    ttk.Label(tab_general, text="URL:").grid(row=5, column=0, sticky="w", pady=4)
    url_entry = ttk.Entry(tab_general)
    url_entry.grid(row=5, column=1, columnspan=2, sticky="ew", pady=4)

    # 7. Notes Row
    ttk.Label(tab_general, text="Notes:").grid(row=6, column=0, sticky="nw", pady=4)
    notes_text = tk.Text(tab_general, height=6, font=("Segoe UI", 9), relief="solid", bd=1)
    notes_text.grid(row=6, column=1, columnspan=2, sticky="nsew", pady=4)
    tab_general.rowconfigure(6, weight=1)

    # ==================== POPULATE EDIT DATA ====================
    original_title = None
    if is_edit and item_id:
        values = root.database_table.item(item_id, "values")
        if values:
            original_title = values[0]
            
            # Fetch full raw fields from database
            cursor = root.conn.cursor()
            cursor.execute("SELECT title, username, password, url, notes FROM users WHERE title=?", (original_title,))
            row = cursor.fetchone()
            if row:
                title_entry.insert(0, row[0] or "")
                username_entry.insert(0, row[1] or "")
                password_entry.insert(0, row[2] or "")
                repeat_entry.insert(0, row[2] or "")
                url_entry.insert(0, row[3] or "")
                notes_text.insert("1.0", row[4] or "")

    # Trigger initial validation state
    validate_repeat_password()

    # ==================== BOTTOM BUTTON BAR ====================
    sep = ttk.Separator(dialog, orient="horizontal")
    sep.pack(side="bottom", fill="x")

    bottom_bar = ttk.Frame(dialog, padding=(10, 8))
    bottom_bar.pack(side="bottom", fill="x")

    btn_cancel = ttk.Button(bottom_bar, text="Cancel", width=10, command=dialog.destroy)
    btn_cancel.pack(side="right", padx=(5, 0))

    def save_entry():
        title = title_entry.get().strip()
        username = username_entry.get().strip()
        pwd = password_entry.get()
        repeat_pwd = repeat_entry.get()
        url = url_entry.get().strip()
        notes = notes_text.get("1.0", tk.END).strip()

        if not title:
            messagebox.showerror("Error", "Title is required!", parent=dialog)
            return

        if pwd != repeat_pwd:
            messagebox.showerror("Error", "Passwords do not match!", parent=dialog)
            return

        try:
            cursor = root.conn.cursor()
            if is_edit:
                cursor.execute(
                    """
                    UPDATE users 
                    SET title=?, username=?, password=?, url=?, notes=?, last_modification=CURRENT_TIMESTAMP
                    WHERE title=?
                    """,
                    (title, username, pwd, url, notes, original_title)
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO users (title, username, password, url, notes)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (title, username, pwd, url, notes)
                )

            populate_table(root)
            dialog.destroy()

        except apsw.ConstraintError:
            messagebox.showerror("Error", f"An entry titled '{title}' already exists.", parent=dialog)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save entry: {e}", parent=dialog)

    btn_ok = ttk.Button(bottom_bar, text="OK", width=10, command=save_entry)
    btn_ok.pack(side="right")

    dialog.bind("<Return>", lambda e: save_entry())
    dialog.after(10, quality_meter.update_meter)


def add_entry(root):
    show_entry_dialog(root, is_edit=False)


def edit_entry(root):
    if root.conn is None:
        messagebox.showwarning("Warning", "No database is currently open.", parent=root)
        return

    selected = root.database_table.selection()
    if not selected:
        messagebox.showinfo("Information", "Please select an entry to edit.", parent=root)
        return

    show_entry_dialog(root, is_edit=True, item_id=selected[0])

PROFILES_FILE = "profiles.json"


def show_password_generator_dialog(parent_window, callback=None):
    """Displays the KeePass-style Password Generation Options dialog box with profile saving support."""
    dialog = tk.Toplevel(parent_window)
    dialog.title("Password Generator")
    dialog.geometry("540x540")
    dialog.resizable(False, False)
    dialog.grab_set()
    dialog.transient(parent_window)
    dialog.configure(bg="#f0f0f0")

    # ==================== HEADER BANNER ====================
    header_frame = tk.Frame(dialog, bg="#1b2a47", height=70)
    header_frame.pack(side="top", fill="x")
    header_frame.pack_propagate(False)

    title_label = tk.Label(
        header_frame,
        text="Password Generation Options",
        font=("Segoe UI", 13, "bold"),
        fg="white",
        bg="#1b2a47",
    )
    title_label.pack(anchor="w", padx=20, pady=(10, 0))

    subtitle_label = tk.Label(
        header_frame,
        text="Here you can define properties of generated passwords.",
        font=("Segoe UI", 9),
        fg="#a2b3d1",
        bg="#1b2a47",
    )
    subtitle_label.pack(anchor="w", padx=20, pady=(2, 5))

    accent_bar = tk.Frame(dialog, bg="#e67e22", height=2)
    accent_bar.pack(side="top", fill="x")

    # ==================== TABBED NOTEBOOK ====================
    notebook = ttk.Notebook(dialog)
    notebook.pack(fill="both", expand=True, padx=8, pady=8)

    tab_settings = ttk.Frame(notebook, padding=10)
    tab_advanced = ttk.Frame(notebook, padding=10)
    tab_preview = ttk.Frame(notebook, padding=10)

    notebook.add(tab_settings, text="Settings")
    notebook.add(tab_advanced, text="Advanced")
    notebook.add(tab_preview, text="Preview")

    # ==================== PROFILES DATA & JSON PERSISTENCE ====================
    DEFAULT_PROFILES = {
        "Automatically generated passwords",
        "Hex Key 128-bit",
        "Hex Key 256-bit",
    }

    base_profiles = {
        "Automatically generated passwords": {
            "length": 20, "upper": True, "lower": True, "digits": True,
            "minus": False, "underline": False, "space": False, "special": True,
            "brackets": False, "latin1": False, "custom": ""
        },
        "Hex Key 128-bit": {
            "length": 32, "upper": True, "lower": False, "digits": True,
            "minus": False, "underline": False, "space": False, "special": False,
            "brackets": False, "latin1": False, "custom": ""
        },
        "Hex Key 256-bit": {
            "length": 64, "upper": True, "lower": False, "digits": True,
            "minus": False, "underline": False, "space": False, "special": False,
            "brackets": False, "latin1": False, "custom": ""
        }
    }

    # Load profile data from JSON if file exists, falling back to built-ins
    profiles_data = base_profiles.copy()
    if os.path.exists(PROFILES_FILE):
        try:
            with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                loaded_profiles = json.load(f)
                profiles_data.update(loaded_profiles)
        except Exception as e:
            messagebox.showwarning("Warning", f"Could not load profiles from JSON: {e}", parent=dialog)

    def save_profiles_to_json():
        """Helper to write current profiles_data dict to JSON file."""
        try:
            with open(PROFILES_FILE, "w", encoding="utf-8") as f:
                json.dump(profiles_data, f, indent=4)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save profiles to JSON: {e}", parent=dialog)

    # ==================== PROFILE ROW ====================
    profile_frame = ttk.Frame(tab_settings)
    profile_frame.pack(fill="x", pady=(0, 10))

    ttk.Label(profile_frame, text="Profile:").pack(side="left", padx=(0, 5))

    profile_cb = ttk.Combobox(
        profile_frame,
        values=list(profiles_data.keys()),
        state="readonly",
    )
    profile_cb.current(0)
    profile_cb.pack(side="left", fill="x", expand=True, padx=(0, 5))

    btn_edit = ttk.Button(profile_frame, text="📝", width=3)
    btn_edit.pack(side="left", padx=1)

    btn_del = ttk.Button(profile_frame, text="✖", width=3)
    btn_del.pack(side="left", padx=1)

    btn_sec = ttk.Button(profile_frame, text="🛡️", width=3)
    btn_sec.pack(side="left", padx=1)

    # ==================== CURRENT SETTINGS GROUP ====================
    settings_group = ttk.LabelFrame(
        tab_settings, text="Character Set Options", padding=10
    )
    settings_group.pack(fill="both", expand=True)

    charset_container = ttk.Frame(settings_group)
    charset_container.pack(fill="x", anchor="w")

    # Variables
    var_length = tk.IntVar(value=20)
    var_upper = tk.BooleanVar(value=True)
    var_lower = tk.BooleanVar(value=True)
    var_digits = tk.BooleanVar(value=True)
    var_minus = tk.BooleanVar(value=False)
    var_underline = tk.BooleanVar(value=False)

    var_space = tk.BooleanVar(value=False)
    var_special = tk.BooleanVar(value=False)
    var_brackets = tk.BooleanVar(value=False)
    var_latin1 = tk.BooleanVar(value=False)

    # Length Spinbox
    len_frame = ttk.Frame(charset_container)
    len_frame.pack(fill="x", pady=2)
    ttk.Label(len_frame, text="Length of generated password:").pack(side="left")

    spin_length = ttk.Spinbox(
        len_frame, from_=1, to=128, textvariable=var_length, width=6
    )
    spin_length.pack(side="right")

    # Checkboxes Grid
    chk_frame = ttk.Frame(charset_container)
    chk_frame.pack(fill="x", pady=5)
    chk_frame.columnconfigure(0, weight=1)
    chk_frame.columnconfigure(1, weight=1)

    # Column 1
    ttk.Checkbutton(chk_frame, text="Upper-case (A, B, C, ...)", variable=var_upper).grid(row=0, column=0, sticky="w", pady=2)
    ttk.Checkbutton(chk_frame, text="Lower-case (a, b, c, ...)", variable=var_lower).grid(row=1, column=0, sticky="w", pady=2)
    ttk.Checkbutton(chk_frame, text="Digits (0, 1, 2, ...)", variable=var_digits).grid(row=2, column=0, sticky="w", pady=2)
    ttk.Checkbutton(chk_frame, text="Minus (-)", variable=var_minus).grid(row=3, column=0, sticky="w", pady=2)
    ttk.Checkbutton(chk_frame, text="Underline (_)", variable=var_underline).grid(row=4, column=0, sticky="w", pady=2)

    # Column 2
    ttk.Checkbutton(chk_frame, text="Space ( )", variable=var_space).grid(row=0, column=1, sticky="w", pady=2)
    ttk.Checkbutton(chk_frame, text="Special (!, $, %, &, ...)", variable=var_special).grid(row=1, column=1, sticky="w", pady=2)
    ttk.Checkbutton(chk_frame, text="Brackets ([, ], {, }, (, ), <, >)", variable=var_brackets).grid(row=2, column=1, sticky="w", pady=2)
    ttk.Checkbutton(chk_frame, text="Latin-1 Supplement (Ä, μ, ¶, ...)", variable=var_latin1).grid(row=3, column=1, sticky="w", pady=2)

    # Custom characters input
    ttk.Label(charset_container, text="Also include the following characters:").pack(anchor="w", pady=(5, 2))
    ent_custom_chars = ttk.Entry(charset_container)
    ent_custom_chars.pack(fill="x", pady=(0, 5))

    # ==================== PROFILE CONTROL LOGIC ====================
    def load_profile_settings(event=None):
        selected_profile = profile_cb.get()
        if selected_profile not in profiles_data:
            return

        data = profiles_data[selected_profile]
        var_length.set(data.get("length", 20))
        var_upper.set(data.get("upper", True))
        var_lower.set(data.get("lower", True))
        var_digits.set(data.get("digits", True))
        var_minus.set(data.get("minus", False))
        var_underline.set(data.get("underline", False))
        var_space.set(data.get("space", False))
        var_special.set(data.get("special", False))
        var_brackets.set(data.get("brackets", False))
        var_latin1.set(data.get("latin1", False))

        ent_custom_chars.delete(0, tk.END)
        ent_custom_chars.insert(0, data.get("custom", ""))

    profile_cb.bind("<<ComboboxSelected>>", load_profile_settings)

    def save_custom_profile():
        """Saves current character set configurations to a new or existing profile and writes to JSON."""
        from tkinter import simpledialog

        current_name = profile_cb.get()
        profile_name = simpledialog.askstring(
            "Save Profile",
            "Enter profile name to save current generator options:",
            parent=dialog,
            initialvalue=current_name
        )

        if not profile_name or not profile_name.strip():
            return

        profile_name = profile_name.strip()

        # Update dictionary state with form inputs
        profiles_data[profile_name] = {
            "length": var_length.get(),
            "upper": var_upper.get(),
            "lower": var_lower.get(),
            "digits": var_digits.get(),
            "minus": var_minus.get(),
            "underline": var_underline.get(),
            "space": var_space.get(),
            "special": var_special.get(),
            "brackets": var_brackets.get(),
            "latin1": var_latin1.get(),
            "custom": ent_custom_chars.get(),
        }

        # Persist to disk
        save_profiles_to_json()

        # Refresh combobox options
        profile_cb["values"] = list(profiles_data.keys())
        profile_cb.set(profile_name)

    def delete_custom_profile():
        """Deletes the currently selected custom profile and updates JSON."""
        current_profile = profile_cb.get()

        if current_profile in DEFAULT_PROFILES:
            messagebox.showwarning(
                "Protected Profile",
                f"The built-in profile '{current_profile}' cannot be deleted.",
                parent=dialog
            )
            return

        confirm = messagebox.askyesno(
            "Delete Profile",
            f"Are you sure you want to delete profile '{current_profile}'?",
            parent=dialog
        )

        if confirm:
            del profiles_data[current_profile]
            save_profiles_to_json()
            profile_cb["values"] = list(profiles_data.keys())
            profile_cb.current(0)
            load_profile_settings()

    btn_edit.config(command=save_custom_profile)
    btn_del.config(command=delete_custom_profile)

    # Initial load trigger
    load_profile_settings()

    # ==================== BOTTOM BUTTON BAR ====================
    sep = ttk.Separator(dialog, orient="horizontal")
    sep.pack(side="bottom", fill="x")

    btn_bar = ttk.Frame(dialog, padding=(10, 8))
    btn_bar.pack(side="bottom", fill="x")

    btn_help = ttk.Button(btn_bar, text="Help", width=10)
    btn_help.pack(side="left")

    btn_cancel = ttk.Button(btn_bar, text="Cancel", width=10, command=dialog.destroy)
    btn_cancel.pack(side="right", padx=(5, 0))

    def handle_ok():
        try:
            generated_pwd = PasswordGenerator.generate(
                length=var_length.get(),
                use_upper=var_upper.get(),
                use_lower=var_lower.get(),
                use_digits=var_digits.get(),
                use_minus=var_minus.get(),
                use_underline=var_underline.get(),
                use_space=var_space.get(),
                use_special=var_special.get(),
                use_brackets=var_brackets.get(),
                use_latin1=var_latin1.get(),
                custom_chars=ent_custom_chars.get(),
            )

            if callback:
                callback(generated_pwd)

            dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=dialog)

    btn_ok = ttk.Button(btn_bar, text="OK", width=10, command=handle_ok)
    btn_ok.pack(side="right")