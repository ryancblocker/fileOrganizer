import sys, os, json, shutil
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QFileDialog, QListWidget, QListWidgetItem, QLabel, QDialog, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QStyle,
    QStyleOptionButton, QStylePainter
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QSize, QObject, QThread, pyqtSignal

# ---------------------------------------------------------------
# Config persistence helpers
# ---------------------------------------------------------------
RULES_FILE = Path.home() / ".file_organizer_rules.json"
DEFAULT_RULES = {
    ".jpg": "Images", ".jpeg": "Images", ".png": "Images",
    ".pdf": "Documents", ".docx": "Documents", ".txt": "Documents",
    ".mp4": "Videos", ".mov": "Videos",
    ".mp3": "Audio", ".wav": "Audio",
}

def load_rules() -> dict[str, str]:
    try:
        if RULES_FILE.exists():
            with RULES_FILE.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
            return {k.lower(): v for k, v in data.items()}
    except Exception:
        pass
    return DEFAULT_RULES.copy()

def save_rules(rules: dict[str, str]):
    try:
        with RULES_FILE.open("w", encoding="utf-8") as fp:
            json.dump(rules, fp, indent=2)
    except Exception as e:
        QMessageBox.warning(None, "Save Error", f"Could not save rules:\n{e}")

# ---------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------

def normalize_ext(ext: str) -> str:
    ext = ext.strip().lower()
    return ext if not ext or ext.startswith('.') else '.' + ext

def unique_path(dest: Path, name: str) -> Path:
    target = dest / name
    if not target.exists():
        return target
    stem, suf = target.stem, target.suffix
    idx = 1
    while True:
        p = dest / f"{stem} ({idx}){suf}"
        if not p.exists():
            return p
        idx += 1

# ---------------------------------------------------------------
# Fancy progress-painting push button
# ---------------------------------------------------------------
class ProgressButton(QPushButton):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._pct = 0.0
    def set_progress(self, pct: float):
        self._pct = max(0.0, min(1.0, pct))
        self.update()
    def paintEvent(self, e):
        opt = QStyleOptionButton(); self.initStyleOption(opt)
        painter = QStylePainter(self)
        painter.drawControl(QStyle.CE_PushButtonBevel, opt)
        if self._pct > 0:
            fill = opt.rect.adjusted(2, 2, -2, -2)
            fill.setWidth(int(fill.width() * self._pct))
            painter.fillRect(fill, self.palette().highlight())
        painter.drawControl(QStyle.CE_PushButtonLabel, opt)

# ---------------------------------------------------------------
# Background worker thread
# ---------------------------------------------------------------
class SortWorker(QObject):
    progress = pyqtSignal(int, int)               # moved, total
    finished = pyqtSignal(list)                   # list[ (src, dest) ] for undo
    error    = pyqtSignal(str)
    def __init__(self, root: Path, files: list[Path], rules: dict[str, str]):
        super().__init__()
        self.root, self.files, self.rules = root, files, rules
    def run(self):
        undo_moves = []
        total = len(self.files)
        done = 0
        for src in self.files:
            ext = src.suffix.lower()
            folder = self.rules.get(ext, "Others")
            dest_dir = self.root / folder
            try: dest_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self.error.emit(f"Could not create {dest_dir}: {e}"); continue
            dest = unique_path(dest_dir, src.name)
            try: shutil.move(str(src), str(dest))
            except Exception as e:
                self.error.emit(f"Move failed for {src}: {e}"); continue
            undo_moves.append((str(dest), str(src)))
            done += 1; self.progress.emit(done, total)
        self.finished.emit(undo_moves)

# ---------------------------------------------------------------
# Settings dialog
# ---------------------------------------------------------------
class SettingsDialog(QDialog):
    rules_saved = pyqtSignal(dict)
    def __init__(self, rules: dict[str, str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sorting Rules")
        self.resize(500, 300)
        self._rules = rules.copy()
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Ext → folder (comma-separate multiple)"))
        self.table = QTableWidget(0, 2); self.table.setHorizontalHeaderLabels(["Extensions", "Folder"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        lay.addWidget(self.table)
        btnrow = QHBoxLayout(); add=QPushButton("Add"); rem=QPushButton("Delete"); save=QPushButton("Save"); cancel=QPushButton("Cancel")
        btnrow.addWidget(add); btnrow.addWidget(rem); btnrow.addStretch(); btnrow.addWidget(cancel); btnrow.addWidget(save)
        lay.addLayout(btnrow)
        add.clicked.connect(lambda: self._add_row())
        rem.clicked.connect(lambda: self._del_rows())
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._save)
        self._populate()
    def _populate(self):
        tmp = {}
        for ext, folder in self._rules.items(): tmp.setdefault(folder, []).append(ext)
        for folder, exts in tmp.items():
            r=self.table.rowCount(); self.table.insertRow(r)
            self.table.setItem(r,0,QTableWidgetItem(','.join(exts))); self.table.setItem(r,1,QTableWidgetItem(folder))
    def _add_row(self):
        r=self.table.rowCount(); self.table.insertRow(r); self.table.setItem(r,0,QTableWidgetItem(".ext")); self.table.setItem(r,1,QTableWidgetItem("Folder"))
    def _del_rows(self):
        rows={i.row() for i in self.table.selectedIndexes()};
        for r in sorted(rows, reverse=True): self.table.removeRow(r)
    def _save(self):
        new={}
        for row in range(self.table.rowCount()):
            exts_item=self.table.item(row,0); folder_item=self.table.item(row,1)
            if not folder_item: continue
            folder=folder_item.text().strip() or "Others"
            if exts_item:
                for ext in exts_item.text().split(','):
                    ne=normalize_ext(ext)
                    if ne: new[ne]=folder
        self.rules_saved.emit(new); self.accept()

# ---------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------
class FileOrganizerUI(QWidget):
    def __init__(self):
        super().__init__(); self.setWindowTitle("File Organizer"); self.resize(900,600)
        self.rules = load_rules(); self.undo_moves=[]; self.current_root:Path|None=None; self.files: list[Path]=[]
        self._build_ui()
    # -------------------- UI Layout --------------------
    def _build_ui(self):
        main=QVBoxLayout(self)
        # ––– Top bar
        top=QHBoxLayout(); browse=QPushButton("Browse"); browse.clicked.connect(self._browse)
        self.path_edit=QLineEdit(); self.path_edit.setPlaceholderText("Select folder…")
        gear_icon=QIcon.fromTheme("preferences-system")
        self.settings_btn=QPushButton()
        if gear_icon.isNull():
            self.settings_btn.setText("⚙︎")
        else:
            self.settings_btn.setIcon(gear_icon)
        self.settings_btn.setFixedWidth(40); self.settings_btn.clicked.connect(self._open_settings)
        top.addWidget(browse); top.addWidget(self.path_edit); top.addWidget(self.settings_btn)
        main.addLayout(top)
        # ––– Preview list (vertical)
        self.view=QListWidget(); self.view.setViewMode(QListWidget.ListMode); self.view.setIconSize(QSize(24,24))
        self.view.setMovement(QListWidget.Static); self.view.setSelectionMode(QListWidget.NoSelection)
        main.addWidget(self.view,1)
        # ––– Bottom bar
        bottom=QHBoxLayout(); self.sort_btn=ProgressButton("Sort Files"); self.sort_btn.setFixedHeight(48); self.sort_btn.clicked.connect(self._start_sort)
        self.undo_btn=QPushButton("Undo"); self.undo_btn.setFixedHeight(48); self.undo_btn.setEnabled(False); self.undo_btn.clicked.connect(self._undo)
        bottom.addWidget(self.sort_btn); bottom.addWidget(self.undo_btn); main.addLayout(bottom)
    # -------------------- Helpers --------------------
    def _icon_for(self,p:Path):
        s=QApplication.style(); return s.standardIcon(QStyle.SP_DirIcon) if p.is_dir() else s.standardIcon(QStyle.SP_FileIcon)
    def _load_preview(self):
        self.view.clear(); self.files.clear()
        if not (self.current_root and self.current_root.exists()): return
        for entry in sorted(self.current_root.iterdir()):
            self.view.addItem(QListWidgetItem(self._icon_for(entry), entry.name))
            if entry.is_file(): self.files.append(entry)
    # -------------------- browse & settings --------------------
    def _browse(self):
        folder=QFileDialog.getExistingDirectory(self,"Select Folder");
        if folder: self._set_root(Path(folder))
    def _set_root(self,p:Path):
        self.current_root=p; self.path_edit.setText(str(p)); self._load_preview()
    def _open_settings(self):
        dlg=SettingsDialog(self.rules,self); dlg.rules_saved.connect(self._update_rules); dlg.exec_()
    def _update_rules(self,new):
        self.rules=new or DEFAULT_RULES.copy(); save_rules(self.rules)
    # -------------------- sorting --------------------
    def _start_sort(self):
        if not self.current_root:
            QMessageBox.warning(self,"No folder","Browse to a folder first."); return
        if not self.files:
            QMessageBox.information(self,"Nothing to do","No files to move."); return
        self.sort_btn.setEnabled(False); self.undo_btn.setEnabled(False)
        self.sort_btn.setText(f"Sorting… 0/{len(self.files)}"); self.sort_btn.set_progress(0)
        self.thread=QThread(); self.worker=SortWorker(self.current_root,self.files.copy(),self.rules); self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run); self.worker.progress.connect(self._on_progress)
        self.worker.error.connect(lambda m: QMessageBox.warning(self,"Error",m))
        self.worker.finished.connect(self._on_sorted); self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater); self.thread.start()
    def _on_progress(self,moved,total):
        self.sort_btn.set_progress(moved/total); self.sort_btn.setText(f"Sorting… {moved}/{total}")
    def _on_sorted(self,moves):
        self.undo_moves=moves; self.sort_btn.setText("Done!"); self.sort_btn.set_progress(1); self.sort_btn.setEnabled(True)
        if moves: self.undo_btn.setEnabled(True)
        self._load_preview()
    # -------------------- undo --------------------
    def _undo(self):
        if not self.undo_moves: return
        errs=[]
        # move files back
        for src,dest in self.undo_moves:
            try: shutil.move(src,unique_path(Path(dest).parent,Path(src).name))
            except Exception as e: errs.append(str(e))
        # remove any now-empty dest folders
        for src,dest in self.undo_moves:
            folder=Path(src).parent
            try:
                if folder.exists() and not any(folder.iterdir()): folder.rmdir()
            except OSError: pass
        self.undo_moves.clear(); self.undo_btn.setEnabled(False)
        # reset sort button
        self.sort_btn.setText("Sort Files"); self.sort_btn.set_progress(0)
        self._load_preview()
        if errs:
            QMessageBox.warning(self,"Undo issues","Some files couldn't be restored:\n"+'\n'.join(errs))

# ---------------------------------------------------------------
if __name__=="__main__":
    app=QApplication(sys.argv); win=FileOrganizerUI(); win.show(); sys.exit(app.exec_())
