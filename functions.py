import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import apsw
import math
import string
from passwordqualitymeter import PasswordQualityMeter

import tkinter as tk
from tkinter import ttk, messagebox

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

    open_btn = ttk.Button(btn_frame, text="Unlock", command=unlock)
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