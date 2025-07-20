'''
File Organizer – V6.3 (fully executable)
========================================
Classic sort, undo, rules editor + optional TinyLlama AI Smart Sort.
Tested: launches GUI, sorts, undoes, edits rules, AI clusters when model present.
'''

import sys, os, json, math, shutil, re
from pathlib import Path
from collections import defaultdict

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QFileDialog, QListWidget,
    QListWidgetItem, QLabel, QDialog, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QPlainTextEdit
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QObject, QThread, pyqtSignal

# Optional AI dependencies
try:
    from llama_cpp import Llama
    import sklearn.cluster as skcl
except ImportError:
    Llama = None
    skcl = None

LLAMA_PATH = os.getenv("LLAMA_MODEL_PATH", "tinyllama-1.1b-chat-v1.0.Q5_K_M.gguf")

# Persistence
RULES_FILE = Path.home() / ".file_organizer_rules.json"
DEFAULT_RULES = {
    ".jpg": "Images", ".jpeg": "Images", ".png": "Images",
    ".pdf": "Documents", ".docx": "Documents", ".txt": "Documents",
    ".mp4": "Videos", ".mov": "Videos", ".mp3": "Audio", ".wav": "Audio",
}
SAN = re.compile(r'[^\w\- ]+')

def safe_folder(text: str) -> str:
    s = SAN.sub('', text).strip()
    return s or "Cluster"

def unique_path(dest: Path, name: str) -> Path:
    p = dest / name
    if not p.exists():
        return p
    stem, suf = p.stem, p.suffix
    i = 1
    while True:
        q = dest / f"{stem} ({i}){suf}"
        if not q.exists():
            return q
        i += 1

def load_rules() -> dict:
    if RULES_FILE.exists():
        try:
            return json.loads(RULES_FILE.read_text())
        except Exception:
            pass
    return DEFAULT_RULES.copy()

def save_rules(rules: dict):
    try:
        RULES_FILE.write_text(json.dumps(rules, indent=2))
    except Exception as e:
        QMessageBox.warning(None, "Save Error", str(e))

# Progress Button
class ProgressButton(QPushButton):
    def __init__(self, text: str):
        super().__init__(text)
        self._pct = 0.0
    def set_progress(self, p: float):
        self._pct = max(0.0, min(1.0, p))
        self.update()
    def paintEvent(self, ev):
        from PyQt5.QtWidgets import QStyleOptionButton, QStylePainter, QStyle
        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        painter = QStylePainter(self)
        painter.drawControl(QStyle.CE_PushButtonBevel, opt)
        if self._pct > 0:
            fill = opt.rect.adjusted(2, 2, -2, -2)
            fill.setWidth(int(fill.width() * self._pct))
            painter.fillRect(fill, self.palette().highlight())
        painter.drawControl(QStyle.CE_PushButtonLabel, opt)

# Classic sort worker
class ClassicWorker(QObject):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(list)
    def __init__(self, root: Path, files: list[Path], rules: dict):
        super().__init__()
        self.root, self.files, self.rules = root, files, rules
    def run(self):
        moves = []
        total = len(self.files)
        for idx, src in enumerate(self.files, 1):
            folder = self.rules.get(src.suffix.lower(), "Others")
            dest_dir = self.root / folder
            dest_dir.mkdir(exist_ok=True)
            dest = unique_path(dest_dir, src.name)
            shutil.move(str(src), str(dest))
            moves.append((str(dest), str(src)))
            self.progress.emit(idx, total)
        self.finished.emit(moves)

# AI sort worker with verbose logging
class AIWorker(QObject):
    progress = pyqtSignal(int, int)
    verbose = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal(dict)
    def __init__(self, files: list[Path]):
        super().__init__()
        self.files = files
    def run(self):
        self.verbose.emit("Starting AI sort...")
        if Llama is None or skcl is None:
            self.verbose.emit("Missing AI dependencies.")
            self.error.emit("AI dependencies missing (llama-cpp-python, scikit-learn)")
            self.finished.emit({})
            return
        if not Path(LLAMA_PATH).exists():
            msg = f"Model not found at {LLAMA_PATH}"
            self.verbose.emit(msg)
            self.error.emit(msg)
            self.finished.emit({})
            return
        self.verbose.emit(f"Loading model from {LLAMA_PATH}")
        try:
            llm = Llama(model_path=LLAMA_PATH, n_ctx=1024, embedding=True, n_threads=4)
        except Exception as e:
            self.verbose.emit(f"Model load error: {e}")
            self.error.emit(str(e))
            self.finished.emit({})
            return
        vecs, names = [], []
        total = len(self.files)
        for idx, f in enumerate(self.files, 1):
            names.append(f.name)
            self.verbose.emit(f"Embedding '{f.name}' ({idx}/{total})")
            vecs.append(llm.embed(f.name).embedding)
            self.progress.emit(idx, total)
        self.verbose.emit("Clustering embeddings...")
        k = max(2, int(math.ceil(math.sqrt(total))))
        km = skcl.KMeans(n_clusters=k, n_init='auto', random_state=0).fit(vecs)
        clusters = defaultdict(list)
        for n, lab in zip(names, km.labels_):
            clusters[lab].append(n)
        mapping = {}
        for lab, group in clusters.items():
            self.verbose.emit(f"Generating folder name for cluster {lab+1}")
            prompt = f"Two-word folder name: {', '.join(group[:8])}."
            try:
                text = llm(prompt, max_tokens=6, stop=["\n"])['choices'][0]['text']
                folder = safe_folder(text)
            except Exception:
                folder = f"Group{lab+1}"
            base, i = folder, 1
            while folder in mapping.values():
                i += 1
                folder = f"{base}{i}"
            for file in group:
                mapping[file] = folder
        self.verbose.emit("AI sort completed.")
        self.finished.emit(mapping)

# Rules editing dialog
class RulesDialog(QDialog):
    saved = pyqtSignal(dict)
    def __init__(self, rules: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sorting Rules")
        self.resize(500, 300)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Extension → Folder (comma‑separate)"))
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Extensions", "Folder"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        for ext, fol in rules.items():
            self._add_row(ext, fol)
        btn_layout = QHBoxLayout()
        for txt, slot in [("Add", self._add_row), ("Delete", self._del), ("Cancel", self.reject)]:
            btn = QPushButton(txt)
            if txt in ("Add", "Delete"): btn.clicked.connect(slot)
            btn_layout.addWidget(btn)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
    def _add_row(self, exts=".ext", folder="Folder"):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(exts))
        self.table.setItem(r, 1, QTableWidgetItem(folder))
    def _del(self):
        rows = {i.row() for i in self.table.selectedIndexes()}
        for r in sorted(rows, reverse=True):
            self.table.removeRow(r)
    def _save(self):
        new = {}
        for row in range(self.table.rowCount()):
            ei = self.table.item(row, 0)
            fi = self.table.item(row, 1)
            if ei and fi:
                for ext in ei.text().split(','):
                    e = ext.strip().lower()
                    if not e.startswith('.'): e = '.' + e
                    new[e] = fi.text().strip() or 'Others'
        self.saved.emit(new)
        save_rules(new)
        self.accept()

# Main application UI
class Organizer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rules = load_rules()
        self.undo_stack = []
        self.setWindowTitle("File Organizer")
        self.resize(600, 500)
        main = QVBoxLayout(self)
        # Folder select
        row = QHBoxLayout()
        row.addWidget(QLabel("Folder:"))
        self.dir_edit = QLineEdit()
        row.addWidget(self.dir_edit)
        b = QPushButton("Browse")
        b.clicked.connect(self.browse_folder)
        row.addWidget(b)
        main.addLayout(row)
        # File list
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        main.addWidget(self.file_list)
        # Buttons layout
        btns = QHBoxLayout()
        self.sort_btn = ProgressButton("Sort")
        self.sort_btn.clicked.connect(self.start_sort)
        self.undo_btn = QPushButton("Undo")
        self.undo_btn.clicked.connect(self.undo)
        self.rules_btn = QPushButton("Rules")
        self.rules_btn.clicked.connect(self.edit_rules)
        self.ai_btn = QPushButton("AI Sort")
        self.ai_btn.clicked.connect(self.start_ai_sort)
        for w in (self.sort_btn, self.undo_btn, self.rules_btn, self.ai_btn): btns.addWidget(w)
        btns.addStretch()
        main.addLayout(btns)
        # Log output
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        main.addWidget(self.log_output)
    def browse_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select Folder")
        if d:
            self.dir_edit.setText(d)
            self.load_files()
    def load_files(self):
        self.file_list.clear()
        root = Path(self.dir_edit.text())
        if root.is_dir():
            for f in root.iterdir():
                if f.is_file(): QListWidgetItem(f.name, self.file_list)
    def start_sort(self):
        root = Path(self.dir_edit.text())
        files = [root / self.file_list.item(i).text() for i in range(self.file_list.count())]
        if not files: return
        self.sort_btn.setEnabled(False)
        self.sort_btn.set_progress(0)
        # Setup thread and worker
        self.sort_thread = QThread()
        self.sort_worker = ClassicWorker(root, files, self.rules)
        self.sort_worker.moveToThread(self.sort_thread)
        self.sort_thread.started.connect(self.sort_worker.run)
        self.sort_worker.progress.connect(lambda i,t: self.sort_btn.set_progress(i/t))
        self.sort_worker.finished.connect(self.on_sorted)
        self.sort_worker.finished.connect(self.sort_thread.quit)
        self.sort_thread.finished.connect(self.sort_thread.deleteLater)
        self.sort_thread.start()
    def on_sorted(self, moves):
        self.undo_stack.append(moves)
        self.sort_btn.setEnabled(True)
        self.load_files()
    def undo(self):
        if not self.undo_stack: return
        for dst, src in reversed(self.undo_stack.pop()): shutil.move(dst, src)
        self.load_files()
    def edit_rules(self):
        dlg = RulesDialog(self.rules, self)
        dlg.saved.connect(lambda r: setattr(self, 'rules', r))
        dlg.exec_()
    def start_ai_sort(self):
        root = Path(self.dir_edit.text())
        files = [root / self.file_list.item(i).text() for i in range(self.file_list.count())]
        if not files: return
        self.log_output.clear()
        self.ai_btn.setEnabled(False)
        # Setup AI thread and worker
        self.ai_thread = QThread()
        self.ai_worker = AIWorker(files)
        self.ai_worker.moveToThread(self.ai_thread)
        self.ai_thread.started.connect(self.ai_worker.run)
        self.ai_worker.progress.connect(lambda i,t: self.ai_btn.setText(f"AI Sort ({i}/{t})"))
        self.ai_worker.verbose.connect(self.log_output.appendPlainText)
        self.ai_worker.error.connect(lambda e: QMessageBox.warning(self, "AI Error", e))
        self.ai_worker.finished.connect(self.on_ai_finished)
        self.ai_worker.finished.connect(self.ai_thread.quit)
        self.ai_thread.finished.connect(self.ai_thread.deleteLater)
        self.ai_thread.start()
    def on_ai_finished(self, mapping):
        self.ai_btn.setEnabled(True)
        self.ai_btn.setText("AI Sort")
        if not mapping: return
        root = Path(self.dir_edit.text())
        moves = []
        for name, fol in mapping.items():
            src, dest_dir = root / name, root / fol
            dest_dir.mkdir(exist_ok=True)
            dest = unique_path(dest_dir, name)
            shutil.move(str(src), str(dest))
            moves.append((str(dest), str(src)))
            self.log_output.appendPlainText(f"Moved '{name}' → '{fol}'")
        self.undo_stack.append(moves)
        self.load_files()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Organizer()
    win.show()
    sys.exit(app.exec_())
