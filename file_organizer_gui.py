"""File Organizer GUI (macOS‑friendly grid layout)
-------------------------------------------------
This script provides a simple drag‑and‑drop‑free interface to sort files in a chosen
folder by extension. The layout uses `grid()` everywhere, which tends to be more
predictable on Aqua / Tk 8.5+ that ships with macOS.
"""

import os
import shutil
import tkinter as tk
from tkinter import filedialog

BG_COLOR = "#ECE9E4"  # light warm‑gray background that matches Aqua better

# --------------------------------------------------
# 1. Categories – tweak if you like
# --------------------------------------------------
FILE_CATEGORIES = {
    "Images":     [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
    "Documents":  [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx"],
    "Videos":     [".mp4", ".mov", ".avi", ".mkv"],
    "Audio":      [".mp3", ".wav", ".aac"],
    "Archives":   [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Code":       [".py", ".js", ".html", ".css", ".cpp", ".java", ".c"],
    "Others":     []
}

# --------------------------------------------------
# 2. Helper functions
# --------------------------------------------------

def categorize_file(file_name: str) -> str:
    """Return the category key for *file_name* based on extension."""
    _, ext = os.path.splitext(file_name)
    ext = ext.lower()
    for cat, exts in FILE_CATEGORIES.items():
        if ext in exts:
            return cat
    return "Others"


def organize_files(folder: str, log):
    """Move files into category folders under *folder*; write progress to *log*."""
    if not os.path.isdir(folder):
        log("Invalid folder selected.")
        return

    moved = 0
    for item in os.listdir(folder):
        src = os.path.join(folder, item)
        if not os.path.isfile(src):
            continue
        dest_dir = os.path.join(folder, categorize_file(item))
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, item)
        try:
            shutil.move(src, dest)
            log(f"Moved '{item}' → '{os.path.basename(dest_dir)}/'")
            moved += 1
        except Exception as exc:
            log(f"Error moving '{item}': {exc}")
    log(f"Total files organized: {moved}")

# --------------------------------------------------
# 3. GUI
# --------------------------------------------------

def launch_gui():
    root = tk.Tk()
    root.title("File Organizer")
    root.geometry("700x480")
    root.configure(bg=BG_COLOR)

    # Make root grid resizable
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(2, weight=1)  # log area expands

    folder_var = tk.StringVar()

    # ---------- Top row (label • entry • browse) ----------
    top = tk.Frame(root, bg=BG_COLOR)
    top.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
    top.grid_columnconfigure(1, weight=1)  # entry expands

    tk.Label(top, text="Folder to organize:", bg=BG_COLOR, font=("Helvetica", 12)).grid(row=0, column=0, sticky="w")

    entry = tk.Entry(top, textvariable=folder_var, font=("Helvetica", 12))
    entry.grid(row=0, column=1, sticky="ew", padx=6)

    tk.Button(top, text="Browse", command=lambda: browse(folder_var, log)).grid(row=0, column=2)

    # ---------- Sort Now button ----------
    tk.Button(root, text="Sort Now", font=("Helvetica", 12, "bold"), bg="#007AFF", fg="white",
              command=lambda: organize_files(folder_var.get(), log)).grid(row=1, column=0, pady=(0, 6))

    # ---------- Log area ----------
    log_frame = tk.Frame(root, bg=BG_COLOR)
    log_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
    log_frame.grid_columnconfigure(0, weight=1)
    log_frame.grid_rowconfigure(0, weight=1)

    log_text = tk.Text(log_frame, wrap="word", font=("Menlo", 11), borderwidth=1, relief="solid")
    log_text.grid(row=0, column=0, sticky="nsew")

    scrollbar = tk.Scrollbar(log_frame, command=log_text.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    log_text.configure(yscrollcommand=scrollbar.set)

    # ---------- Callbacks ----------
    def log(msg: str):
        log_text.insert("end", msg + "\n")
        log_text.see("end")

    def browse(var: tk.StringVar, logger):
        folder = filedialog.askdirectory()
        if folder:
            var.set(folder)
            logger(f"Selected folder: {folder}")

    root.mainloop()


if __name__ == "__main__":
    launch_gui()
