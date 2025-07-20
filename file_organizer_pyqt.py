import sys
import os
import shutil
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QFileDialog,
    QTextEdit, QHBoxLayout, QProgressBar
)
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt, QTimer

FILE_CATEGORIES = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
    "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx"],
    "Videos": [".mp4", ".mov", ".avi", ".mkv"],
    "Audio": [".mp3", ".wav", ".aac"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Code": [".py", ".js", ".html", ".css", ".cpp", ".java", ".c"],
    "Others": []
}


def categorize_file(file_name):
    _, ext = os.path.splitext(file_name)
    ext = ext.lower()
    for category, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            return category
    return "Others"


class FileOrganizer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Organizer")
        self.setWindowIcon(QIcon("icon.png"))
        self.resize(600, 400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        self.label = QLabel("Select a folder to organize")
        self.label.setFont(QFont("Arial", 14))
        self.label.setAlignment(Qt.AlignCenter)

        self.select_button = QPushButton("Select Folder")
        self.select_button.setFont(QFont("Arial", 12))
        self.select_button.clicked.connect(self.select_folder)

        self.organize_button = QPushButton("Sort Now")
        self.organize_button.setFont(QFont("Arial", 12))
        self.organize_button.clicked.connect(self.organize_files)
        self.organize_button.setEnabled(False)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setVisible(False)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Courier", 10))

        layout.addWidget(self.label)
        layout.addWidget(self.select_button)
        layout.addWidget(self.organize_button)
        layout.addWidget(self.progress)
        layout.addWidget(self.log)

        self.setLayout(layout)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.folder = folder
            self.label.setText(f"Selected: {folder}")
            self.organize_button.setEnabled(True)

    def organize_files(self):
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.log.clear()

        files = [f for f in os.listdir(self.folder) if os.path.isfile(os.path.join(self.folder, f))]
        total_files = len(files)
        moved_files = 0

        for i, item in enumerate(files):
            src_path = os.path.join(self.folder, item)
            category = categorize_file(item)
            dest_dir = os.path.join(self.folder, category)
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, item)
            try:
                shutil.move(src_path, dest_path)
                self.log.append(f"Moved '{item}' → '{category}/'")
                moved_files += 1
            except Exception as e:
                self.log.append(f"Error moving '{item}': {e}")
            self.progress.setValue(int(((i + 1) / total_files) * 100))

        self.log.append(f"\n✅ Sorted {moved_files} files.")
        self.progress.setValue(100)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileOrganizer()
    window.show()
    sys.exit(app.exec_())