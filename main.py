import tkinter as tk
from tkinter import ttk
from functions import *
import tooltips as tt

def main():

    #Create the main window
    root = tk.Tk()
    root.title("Password Manager")
    root.geometry("800x500")

    #Create database connection
    root.conn = None

    #----------MENU BAR----------
    #Create a menu bar
    menu_bar = tk.Menu(root, borderwidth=0)

    #Add the File button to the menu bar
    #along with its menu buttons
    file_menu = tk.Menu(menu_bar, tearoff=0)
    file_menu.add_command(label="New...", command=lambda: new_database(root))
    file_menu.add_command(label="Open", command=lambda: open_database(root))
    file_menu.add_command(label="Close", command=lambda: close_database(root))
    file_menu.add_separator()
    file_menu.add_command(label="Save", command=lambda: save_database(root))
    file_menu.add_command(label="Save As", command=lambda: print("Save As"))
    file_menu.add_separator()
    file_menu.add_command(label="Database Settings...", command=lambda: print("Database Settings..."))
    file_menu.add_command(label="Change Master Key...", command=lambda: print("Change Master Key..."))
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=root.quit)
    menu_bar.add_cascade(label="File", menu=file_menu)

    #Add the Group button to the menu bar
    #along with its menu buttons
    group_menu = tk.Menu(menu_bar, tearoff=0)
    group_menu.add_command(label="New Vault", command=lambda: print("New Vault selected"))
    group_menu.add_command(label="Open Vault...", command=lambda: print("Open Vault selected"))
    #group_menu.add_separator()
    group_menu.add_command(label="Exit", command=root.quit)
    menu_bar.add_cascade(label="Group", menu=group_menu)
    
    root.config(menu=menu_bar)

    #----------TOOL BAR----------
    #Create the frame for the tool bar
    tool_bar = ttk.Frame(root, padding=5)
    tool_bar.pack(side="top", fill="x")

    #Add new database button
    icon_new_database = tk.PhotoImage(file="assets/icons/icon_new_database.png")
    img_btn_new_database = tk.Button(
        tool_bar,
        image=icon_new_database,
        command=lambda: new_database(root),
        bd=0,
    )
    img_btn_new_database.pack(side="left", padx=1, pady=1)
    img_btn_new_database.image = icon_new_database
    tt.ToolTip(img_btn_new_database, "New Database")

    #Add new entry button
    icon_new_entry = tk.PhotoImage(file="assets/icons/icon_new_entry.png")
    img_btn_new_entry = tk.Button(
        tool_bar,
        image=icon_new_entry,
        command=lambda: add_entry(root),
        bd=0,
    )
    img_btn_new_entry.pack(side="left", padx=1, pady=1)
    img_btn_new_entry.image = icon_new_entry
    tt.ToolTip(img_btn_new_entry, "New Entry")

    #Add save database button
    icon_save_database = tk.PhotoImage(file="assets/icons/icon_save_database.png")
    img_btn_save_database = tk.Button(
        tool_bar,
        image=icon_save_database,
        command=lambda: save_database(root),
        bd=0,
    )
    img_btn_save_database.pack(side="left", padx=1, pady=1)
    img_btn_save_database.image = icon_save_database
    tt.ToolTip(img_btn_save_database, "Save Database")

    #----------SEPARATOR----------
    separator = ttk.Separator(root, orient="horizontal")
    separator.pack(fill="x")

    #----------DATA TABLE----------
    columns = ("title", "username", "url", "notes")

    root.database_table = ttk.Treeview(
        root,
        columns=columns,
        show="headings"
    )

    for column in columns:
        root.database_table.heading(column, text=column.capitalize())
        root.database_table.column(column, width=150)

    root.database_table.pack(fill="both", expand=True)

    #Start the event loop
    root.mainloop()

if __name__ == "__main__":
    main()