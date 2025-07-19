import os
import shutil
import logging
import json
import argparse
from datetime import datetime

# ---------- Config ----------
UNDO_LOG = "undo_log.json"
LOG_FILE = "file_organizer_log.txt"

# ---------- Logging ----------
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# ---------- File Categories ----------
FILE_CATEGORIES = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
    "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx"],
    "Videos": [".mp4", ".mov", ".avi", ".mkv"],
    "Audio": [".mp3", ".wav", ".aac"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Code": [".py", ".js", ".html", ".css", ".cpp", ".java", ".c"],
    "Others": []
}

# ---------- Helpers ----------
def categorize_file(file_name):
    _, ext = os.path.splitext(file_name)
    ext = ext.lower()
    for category, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            return category
    return "Others"

# ---------- Core Logic ----------
def organize_files(folder_path, preview=False):
    undo_map = {}

    for file in os.listdir(folder_path):
        src_path = os.path.join(folder_path, file)

        if not os.path.isfile(src_path):
            continue  # Skip folders

        category = categorize_file(file)
        dest_dir = os.path.join(folder_path, category)
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, file)

        if preview:
            print(f"[PREVIEW] Would move: {src_path} → {dest_path}")
        else:
            try:
                shutil.move(src_path, dest_path)
                undo_map[dest_path] = src_path
                logging.info(f"Moved '{file}' to '{category}/'")
            except Exception as e:
                logging.error(f"Failed to move '{file}': {e}")

    # Save undo map
    if not preview and undo_map:
        with open(UNDO_LOG, "w") as f:
            json.dump(undo_map, f, indent=2)

# ---------- Undo Logic ----------
def undo_last_operation():
    if not os.path.exists(UNDO_LOG):
        print("No undo history found.")
        return

    with open(UNDO_LOG, "r") as f:
        undo_map = json.load(f)

    for new_path, original_path in undo_map.items():
        try:
            shutil.move(new_path, original_path)
            logging.info(f"Restored '{os.path.basename(new_path)}' to original location.")
        except Exception as e:
            logging.error(f"Failed to restore '{new_path}': {e}")

    os.remove(UNDO_LOG)
    print("Undo complete.")

# ---------- CLI ----------
def main():
    parser = argparse.ArgumentParser(description="Organize files by type with optional preview and undo.")
    parser.add_argument("--folder", type=str, default=os.path.expanduser("~/Downloads"), help="Folder to organize")
    parser.add_argument("--preview", action="store_true", help="Preview only (dry run)")
    parser.add_argument("--undo", action="store_true", help="Undo last operation")

    args = parser.parse_args()

    if args.undo:
        undo_last_operation()
    else:
        print(f"{'Previewing' if args.preview else 'Organizing'} files in: {args.folder}")
        organize_files(args.folder, preview=args.preview)

if __name__ == "__main__":
    main()