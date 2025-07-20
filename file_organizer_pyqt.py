"""
File Organizer Utility - UI V2
--------------------------------
Ryan, this version implements the layout you described:

Top Bar:
  [Browse] [path text field...............................................] [⚙️]

Main Preview:
  Big icon/grid preview of the currently selected *top-level* directory contents.
  File-type icons chosen by extension. Shows both files and folders.

Settings Dialog:
  Simple rule editor (extension(s) -> Target Folder). Add / delete rows. Persist in-session.
  Example: ".psd,.ai" -> "Designs"  (folder will be created under selected root when sorting.)

Sorting:
  Clicking **Sort Files** disables the button, shows an in-button progress % + external bar.
  Actual moves happen on a background worker thread so the UI stays responsive.
  As each destination folder is created and each file is moved, the preview refreshes so you
  can *see* the folders appear and files disappear from the root.

Progress Updates:
  - Bottom progress bar tracks % of total files to move.
  - Sort button text changes to "Sorting… {n}/{total}" then "Done!".

Other Notes:
  - Dragging in the preview is disabled (Static movement + NoSelection).
  - Icons: We use robust fallbacks via the current style in case theme icons aren't found.
  - Safe move: if name collision in destination, we append an incremental suffix.

Tested with Python 3.12.x + PyQt5.

TODO ideas (not yet implemented):
  - Persist rules to JSON alongside script or user config dir.
  - Undo / dry-run.
  - Recursive mode toggle.
  - Animated progress overlay in sort button.

"""

import sys
import os
import shutil
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QFileDialog, QListWidget, QListWidgetItem, QLabel,
    QProgressBar, QDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QToolButton, QStyle, QStyleOptionButton,
    QStyledItemDelegate, QSpinBox, QMenu, QAction
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QSize, QTimer, QObject, pyqtSignal, QThread


# -------------------------------------------------------------
# Utility helpers
# -------------------------------------------------------------

def normalize_ext(ext: str) -> str:
    """Return a lowercase extension that always starts with a dot."""
    ext = ext.strip().lower()
    if not ext:
        return ""
    if not ext.startswith('.'):
        ext = '.' + ext
    return ext


def unique_path(dest_dir: Path, name: str) -> Path:
    """Return a non-colliding path under dest_dir for name by appending (1), (2), ..."""
    candidate = dest_dir / name
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    i = 1
    while True:
        new_name = f"{stem} ({i}){suffix}"
        candidate = dest_dir / new_name
        if not candidate.exists():
            return candidate
        i += 1


# -------------------------------------------------------------
# Worker Thread: perform sorting without freezing UI
# -------------------------------------------------------------
class SortWorker(QObject):
    progress = pyqtSignal(int, int)  # moved, total
    folder_created = pyqtSignal(str)  # path str
    file_moved = pyqtSignal(str, str)  # src, dest
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, root_path: Path, files: list[Path], rules: dict[str, str]):
        super().__init__()
        self.root_path = root_path
        self.files = files
        self.rules = rules  # ext -> folder name
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            total = len(self.files)
            moved = 0
            # Pre-create any needed folders lazily on demand.
            for src in self.files:
                if self._stop:
                    break
                ext = src.suffix.lower()
                dest_folder_name = self.rules.get(ext)
                if dest_folder_name is None:
                    dest_folder_name = "Others"
                dest_dir = self.root_path / dest_folder_name
                if not dest_dir.exists():
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    self.folder_created.emit(str(dest_dir))

                dest_path = unique_path(dest_dir, src.name)
                try:
                    shutil.move(str(src), str(dest_path))
                except Exception as move_err:  # keep going but report
                    self.error.emit(f"Failed to move {src.name}: {move_err}")
                else:
                    moved += 1
                    self.file_moved.emit(str(src), str(dest_path))
                    self.progress.emit(moved, total)
            self.finished.emit()
        except Exception as e:  # catastrophic error
            self.error.emit(str(e))
            self.finished.emit()


# -------------------------------------------------------------
# Settings Dialog - rule editor
# -------------------------------------------------------------
class SettingsDialog(QDialog):
    rules_saved = pyqtSignal(dict)  # ext->folder

    def __init__(self, parent=None, rules: dict[str, str] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Sorting Rules")
        self.setMinimumSize(500, 300)
        self.rules = rules.copy() if rules else {}
        self._build_ui()
        self._populate()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Map file extensions to destination folders.\nUse commas to separate multiple extensions."))

        # Table: Extension(s) | Folder
        self.table = QTableWidget(0, 2, self)
        self.table.setHorizontalHeaderLabels(["Extension(s)", "Folder Name"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.table)

        # Buttons row
        btn_row = QHBoxLayout()
        self.add_row_btn = QPushButton("Add Rule")
        self.del_row_btn = QPushButton("Delete Selected")
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        btn_row.addWidget(self.add_row_btn)
        btn_row.addWidget(self.del_row_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.save_btn)
        layout.addLayout(btn_row)

        # Connect
        self.add_row_btn.clicked.connect(self._add_row)
        self.del_row_btn.clicked.connect(self._delete_row)
        self.save_btn.clicked.connect(self._save)
        self.cancel_btn.clicked.connect(self.reject)

    def _populate(self):
        # coalesce: multiple ext may point to same folder -> compress to row by folder
        folder_to_exts: dict[str, list[str]] = {}
        for ext, folder in self.rules.items():
            folder_to_exts.setdefault(folder, []).append(ext)
        for folder, exts in folder_to_exts.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(','.join(exts)))
            self.table.setItem(row, 1, QTableWidgetItem(folder))

    def _add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(".ext"))
        self.table.setItem(row, 1, QTableWidgetItem("Folder"))

    def _delete_row(self):
        rows = {idx.row() for idx in self.table.selectedIndexes()}
        for r in sorted(rows, reverse=True):
            self.table.removeRow(r)

    def _save(self):
        new_rules: dict[str, str] = {}
        for row in range(self.table.rowCount()):
            exts_item = self.table.item(row, 0)
            folder_item = self.table.item(row, 1)
            if not folder_item:
                continue
            folder = folder_item.text().strip() or "Others"
            if exts_item:
                raw = exts_item.text()
                for ext in raw.split(','):
                    ne = normalize_ext(ext)
                    if ne:
                        new_rules[ne] = folder
        self.rules_saved.emit(new_rules)
        self.accept()


# -------------------------------------------------------------
# Main UI
# -------------------------------------------------------------
class FileOrganizerUI(QWidget):
    DEFAULT_RULES = {
        ".jpg": "Images", ".jpeg": "Images", ".png": "Images",
        ".pdf": "Documents", ".docx": "Documents", ".txt": "Documents",
        ".mp4": "Videos", ".mov": "Videos",
        ".mp3": "Audio", ".wav": "Audio",
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Organizer")
        self.setGeometry(100, 100, 900, 600)
        self.setStyleSheet("background-color: #f7f7f7;")

        self.rules: dict[str, str] = self.DEFAULT_RULES.copy()
        self.current_root: Path | None = None
        self.files_to_sort: list[Path] = []  # top-level files only (no dirs)

        self._setup_ui()

    # ------------------------- UI Layout -------------------------
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Top Bar: Browse | Path | Settings ---
        top_bar = QHBoxLayout()
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browse_folder)

        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select a folder to organize...")
        self.path_input.setStyleSheet("padding: 6px;")

        self.settings_btn = QPushButton("\u2699\ufe0f")  # gear glyph
        self.settings_btn.setFixedWidth(40)
        self.settings_btn.clicked.connect(self.open_settings)

        top_bar.addWidget(self.browse_btn)
        top_bar.addWidget(self.path_input)
        top_bar.addWidget(self.settings_btn)
        main_layout.addLayout(top_bar)

        # --- Preview Area (Icon grid) ---
        self.preview_area = QListWidget()
        self.preview_area.setViewMode(QListWidget.IconMode)
        self.preview_area.setIconSize(QSize(64, 64))
        self.preview_area.setResizeMode(QListWidget.Adjust)
        self.preview_area.setMovement(QListWidget.Static)
        self.preview_area.setSelectionMode(QListWidget.NoSelection)
        self.preview_area.setSpacing(16)
        main_layout.addWidget(self.preview_area, stretch=1)

        # --- Sort Button + Progress Bar ---
        bottom_bar = QVBoxLayout()
        self.sort_btn = QPushButton("Sort Files")
        self.sort_btn.setFixedHeight(48)
        self.sort_btn.clicked.connect(self.start_sorting)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.hide()

        bottom_bar.addWidget(self.sort_btn)
        bottom_bar.addWidget(self.progress)
        main_layout.addLayout(bottom_bar)

    # ------------------------- Icons -------------------------
    def _icon_for_path(self, path: Path) -> QIcon:
        style = QApplication.style()
        if path.is_dir():
            return style.standardIcon(QStyle.SP_DirIcon)
        ext = path.suffix.lower()
        # fallback chain: file type groups to theme names -> standard file icon
        theme_map = {
            "image": "image-x-generic",
            "doc": "x-office-document",
            "video": "video-x-generic",
            "audio": "audio-x-generic",
            "other": "application-octet-stream",
        }
        image_exts = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}
        doc_exts = {".pdf", ".doc", ".docx", ".txt", ".rtf"}
        video_exts = {".mp4", ".mov", ".avi", ".mkv"}
        audio_exts = {".mp3", ".wav", ".aac", ".flac"}
        if ext in image_exts:
            ic = QIcon.fromTheme(theme_map["image"])
        elif ext in doc_exts:
            ic = QIcon.fromTheme(theme_map["doc"])
        elif ext in video_exts:
            ic = QIcon.fromTheme(theme_map["video"])
        elif ext in audio_exts:
            ic = QIcon.fromTheme(theme_map["audio"])
        else:
            ic = QIcon.fromTheme(theme_map["other"])
        if ic.isNull():
            ic = style.standardIcon(QStyle.SP_FileIcon)
        return ic

    # ------------------------- Preview Loading -------------------------
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.set_root(Path(folder))

    def set_root(self, path: Path):
        self.current_root = Path(path)
        self.path_input.setText(str(self.current_root))
        self.load_files_preview(self.current_root)

    def load_files_preview(self, folder_path: Path):
        self.preview_area.clear()
        self.files_to_sort.clear()
        try:
            for entry in sorted(folder_path.iterdir()):
                icon = self._icon_for_path(entry)
                item = QListWidgetItem(icon, entry.name)
                item.setToolTip(str(entry))
                self.preview_area.addItem(item)
                if entry.is_file():
                    self.files_to_sort.append(entry)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to list directory:\n{e}")

    # ------------------------- Settings Dialog -------------------------
    def open_settings(self):
        dlg = SettingsDialog(self, rules=self.rules)
        dlg.rules_saved.connect(self._apply_new_rules)
        dlg.exec_()

    def _apply_new_rules(self, new_rules: dict[str, str]):
        # Merge: replace entirely (simpler)
        self.rules = new_rules if new_rules else self.DEFAULT_RULES.copy()
        # Optional: immediate resort preview? (not moving yet)
        # For now, do nothing but update internal rules.

    # ------------------------- Sorting -------------------------
    def start_sorting(self):
        if not self.current_root or not self.current_root.is_dir():
            QMessageBox.warning(self, "No Folder", "Please select a folder first.")
            return
        if not self.files_to_sort:
            QMessageBox.information(self, "Nothing to Sort", "No top-level files found to move.")
            return

        self.sort_btn.setEnabled(False)
        self.progress.show()
        self.progress.setRange(0, len(self.files_to_sort))
        self.progress.setValue(0)
        self.sort_btn.setText("Sorting… 0/{}".format(len(self.files_to_sort)))

        # Launch worker thread
        self.thread = QThread(self)
        self.worker = SortWorker(self.current_root, self.files_to_sort.copy(), self.rules)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_worker_progress)
        self.worker.folder_created.connect(self._on_worker_folder_created)
        self.worker.file_moved.connect(self._on_worker_file_moved)
        self.worker.error.connect(self._on_worker_error)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _on_worker_progress(self, moved: int, total: int):
        self.progress.setValue(moved)
        self.sort_btn.setText(f"Sorting… {moved}/{total}")

    def _on_worker_folder_created(self, folder_path: str):
        # reload preview to show new folder
        self.load_files_preview(self.current_root)

    def _on_worker_file_moved(self, src: str, dest: str):
        # refresh preview to remove file from root (it moved)
        self.load_files_preview(self.current_root)

    def _on_worker_error(self, msg: str):
        # show non-blocking message
        QMessageBox.warning(self, "Move Error", msg)

    def _on_worker_finished(self):
        self.sort_btn.setEnabled(True)
        self.sort_btn.setText("Done!")
        # After finishing refresh preview one last time (now shows just folders).
        self.load_files_preview(self.current_root)
        # Clear list so re-sorting won't double-move; next click will recount.
        self.files_to_sort.clear()


# -------------------------------------------------------------
# Entry point
# -------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileOrganizerUI()
    window.show()
    sys.exit(app.exec_())
