import tkinter as tk
from tkinter import ttk
from functions import *
import tooltips as tt

def update_entry_details(root):
    """Update the KeePass-style details pane based on Treeview selection."""
    selected_items = root.database_table.selection()
    
    # Enable writing to the Text widget temporarily
    root.txt_details.config(state="normal")
    root.txt_details.delete("1.0", tk.END)

    if len(selected_items) == 1:
        item_id = selected_items[0]
        # Expecting: (title, username, password, url, notes, optional: group, created, modified)
        values = root.database_table.item(item_id, "values")
        
        if values and len(values) >= 5:
            title = values[0] or ""
            username = values[1] or ""
            password = "********" if values[2] else ""
            url = values[3] or ""
            notes = values[4] or ""
            
            # Optional extra fields (fallback to defaults if not in table)
            group = values[5] if len(values) > 5 else "Database"
            created = values[6] if len(values) > 6 else "N/A"
            modified = values[7] if len(values) > 7 else "N/A"

            # --- Row 1: Group, Title, User Name, Password, URL ---
            root.txt_details.insert(tk.END, "Group: ", "bold")
            root.txt_details.insert(tk.END, f"{group}. ", "link")
            
            root.txt_details.insert(tk.END, "Title: ", "bold")
            root.txt_details.insert(tk.END, f"{title}. ")
            
            root.txt_details.insert(tk.END, "User Name: ", "bold")
            root.txt_details.insert(tk.END, f"{username}. ")
            
            root.txt_details.insert(tk.END, "Password: ", "bold")
            root.txt_details.insert(tk.END, f"{password}. ")
            
            root.txt_details.insert(tk.END, "URL: ", "bold")
            root.txt_details.insert(tk.END, f"{url}.\n", "link")

            # --- Row 2: Timestamps ---
            root.txt_details.insert(tk.END, "Creation Time: ", "bold")
            root.txt_details.insert(tk.END, f"{created}. ")
            
            root.txt_details.insert(tk.END, "Last Modification Time: ", "bold")
            root.txt_details.insert(tk.END, f"{modified}.\n\n")

            # --- Row 3: Notes ---
            if notes:
                root.txt_details.insert(tk.END, f"{notes}\n")

    # Lock widget back to read-only state
    root.txt_details.config(state="disabled")

def main():

    # Create the main window
    root = tk.Tk()
    root.title("Password Manager")
    root.geometry("850x650")

    # Load PNG icon
    icon = tk.PhotoImage(file="assets/favicon/application_favicon.png")
    root.iconphoto(True, icon)

    # Database connection holder
    root.conn = None

    #----------MENU BAR----------
    menu_bar = tk.Menu(root, borderwidth=0)

    file_menu = tk.Menu(menu_bar, tearoff=0)
    file_menu.add_command(label="New...", command=lambda: new_database(root))
    file_menu.add_command(label="Open", command=lambda: open_database(root))
    file_menu.add_command(label="Close", command=lambda: close_database(root))
    file_menu.add_separator()
    file_menu.add_command(label="Save", command=lambda: save_database(root))
    file_menu.add_command(label="Save As", command=lambda: save_as_database(root))
    file_menu.add_separator()
    file_menu.add_command(label="Database Settings...", command=lambda: print("Database Settings..."))
    file_menu.add_command(label="Change Master Key...", command=lambda: change_master_key(root))
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=root.quit)
    menu_bar.add_cascade(label="File", menu=file_menu)

    entry_menu = tk.Menu(menu_bar, tearoff=0)
    entry_menu.add_command(label="Copy Username", command=lambda: copy_username(root))
    entry_menu.add_command(label="Copy Password", command=lambda: copy_password(root))
    entry_menu.add_separator()
    entry_menu.add_command(label="Add Entry", command=lambda: add_entry(root))
    entry_menu.add_command(label="Edit Entry", command=lambda: edit_entry(root))
    entry_menu.add_command(label="Duplicate Entry", command=lambda: duplicate_entry(root))
    entry_menu.add_command(label="Delete Entry", command=lambda: delete_entry(root))
    entry_menu.add_separator()
    entry_menu.add_command(label="Select All", command=lambda: select_all(root))
    menu_bar.add_cascade(label="Entry", menu=entry_menu)
    
    root.config(menu=menu_bar)

    #----------TOOL BAR----------
    tool_bar = ttk.Frame(root, padding=5)
    tool_bar.pack(side="top", fill="x")

    icon_new_database = tk.PhotoImage(file="assets/icons/icon_new_database.png")
    img_btn_new_database = tk.Button(tool_bar, image=icon_new_database, command=lambda: new_database(root), bd=0)
    img_btn_new_database.pack(side="left", padx=1, pady=1)
    img_btn_new_database.image = icon_new_database
    tt.ToolTip(img_btn_new_database, "New Database")

    icon_open_database = tk.PhotoImage(file="assets/icons/icon_open_database.png")
    img_btn_open_database = tk.Button(tool_bar, image=icon_open_database, command=lambda: open_database(root), bd=0)
    img_btn_open_database.pack(side="left", padx=1, pady=1)
    img_btn_open_database.image = icon_open_database
    tt.ToolTip(img_btn_open_database, "Open Database")

    icon_save_database = tk.PhotoImage(file="assets/icons/icon_save_database.png")
    img_btn_save_database = tk.Button(tool_bar, image=icon_save_database, command=lambda: save_database(root), bd=0)
    img_btn_save_database.pack(side="left", padx=1, pady=1)
    img_btn_save_database.image = icon_save_database
    tt.ToolTip(img_btn_save_database, "Save Database")

    sep = ttk.Separator(tool_bar, orient="vertical")
    sep.pack(side="left", fill="y", padx=5, pady=2)

    icon_new_entry = tk.PhotoImage(file="assets/icons/icon_new_entry.png")
    img_btn_new_entry = tk.Button(tool_bar, image=icon_new_entry, command=lambda: add_entry(root), bd=0)
    img_btn_new_entry.pack(side="left", padx=1, pady=1)
    img_btn_new_entry.image = icon_new_entry
    tt.ToolTip(img_btn_new_entry, "New Entry")

    sep = ttk.Separator(tool_bar, orient="vertical")
    sep.pack(side="left", fill="y", padx=5, pady=2)

    icon_copy_username = tk.PhotoImage(file="assets/icons/icon_copy_username.png")
    img_btn_copy_username = tk.Button(tool_bar, image=icon_copy_username, command=lambda: copy_username(root), bd=0)
    img_btn_copy_username.pack(side="left", padx=1, pady=1)
    img_btn_copy_username.image = icon_copy_username
    tt.ToolTip(img_btn_copy_username, "Copy Username")

    icon_copy_password = tk.PhotoImage(file="assets/icons/icon_copy_password.png")
    img_btn_copy_password = tk.Button(tool_bar, image=icon_copy_password, command=lambda: copy_password(root), bd=0)
    img_btn_copy_password.pack(side="left", padx=1, pady=1)
    img_btn_copy_password.image = icon_copy_password
    tt.ToolTip(img_btn_copy_password, "Copy Password")

    #----------SEPARATOR----------
    separator = ttk.Separator(root, orient="horizontal")
    separator.pack(fill="x")

    #----------STATUS BAR (Bottom-most)----------
    status_bar = ttk.Frame(root, padding=(10, 3), relief="sunken")
    status_bar.pack(side="bottom", fill="x")

    root.status_label = ttk.Label(status_bar, text="0 of 0 Selected")
    root.status_label.pack(side="left")

    #----------KEEPASS-STYLE DETAILS PANEL (Above Status Bar)----------
    details_container = ttk.Frame(root, relief="sunken", borderwidth=1)
    details_container.pack(side="bottom", fill="x", padx=2, pady=(0, 2))

    details_scroll = ttk.Scrollbar(details_container, orient="vertical")
    details_scroll.pack(side="right", fill="y")

    root.txt_details = tk.Text(
        details_container,
        height=5,
        wrap="word",
        bg="#f0f0f0",
        fg="#000000",
        font=("Segoe UI", 9),
        relief="flat",
        padx=6,
        pady=4,
        yscrollcommand=details_scroll.set
    )
    root.txt_details.pack(side="left", fill="both", expand=True)
    details_scroll.config(command=root.txt_details.yview)

    # Configure text styling tags
    root.txt_details.tag_configure("bold", font=("Segoe UI", 9, "bold"))
    root.txt_details.tag_configure("link", foreground="#0066cc", underline=True)
    root.txt_details.config(state="disabled")  # Make read-only by default

    #----------DATA TABLE (Fills center)----------
    columns = ("title", "username", "password", "url", "notes")

    root.database_table = ttk.Treeview(
        root,
        columns=columns,
        show="headings",
        selectmode="extended"
    )

    for column in columns:
        root.database_table.heading(column, text=column.capitalize())
        root.database_table.column(column, width=150)

    def on_treeview_click(event):
        region = root.database_table.identify_region(event.x, event.y)
        item = root.database_table.identify_row(event.y)
        if not item or region == "nothing":
            root.database_table.selection_remove(root.database_table.selection())

    root.database_table.bind("<Button-1>", on_treeview_click)
    root.database_table.pack(fill="both", expand=True)

    #----------SELECTION EVENT BINDINGS----------
    def handle_selection_change(event):
        update_status_bar(root)
        update_entry_details(root)

    root.database_table.bind("<<TreeviewSelect>>", handle_selection_change)

    # Shortcuts
    root.bind("<Control-a>", lambda event: select_all(root))
    root.bind("<Command-a>", lambda event: select_all(root))

    root.mainloop()

if __name__ == "__main__":
    main()