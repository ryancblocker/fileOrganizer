import sys
import os
import shutil
import random
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QFileDialog,
    QTextEdit, QProgressBar, QDialog, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
)
from PyQt5.QtGui import QFont, QIcon, QPixmap
from PyQt5.QtCore import Qt, QTimer, QPointF, QVariantAnimation

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


class SummaryDialog(QDialog):
    def __init__(self, total, category_counts):
        super().__init__()
        self.setWindowTitle("Sorting Complete")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout()

        image = QLabel()
        image.setPixmap(QPixmap("success.png").scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        image.setAlignment(Qt.AlignCenter)

        text = QLabel(f"✅ Sorted {total} file(s)\n")
        text.setFont(QFont("Arial", 12))
        text.setAlignment(Qt.AlignCenter)

        breakdown = QLabel("\n".join([f"• {cat}: {count}" for cat, count in category_counts.items()]))
        breakdown.setFont(QFont("Arial", 11))
        breakdown.setAlignment(Qt.AlignCenter)

        layout.addWidget(image)
        layout.addWidget(text)
        layout.addWidget(breakdown)
        self.setLayout(layout)


class FileOrganizer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Organizer")
        self.setWindowIcon(QIcon("icon.png"))
        self.resize(600, 400)
        self.sort_animation_step = 0
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
        self.log.setFont(QFont("Menlo", 10))

        layout.addWidget(self.label)
        layout.addWidget(self.select_button)
        layout.addWidget(self.organize_button)
        layout.addWidget(self.progress)
        layout.addWidget(self.log)

        self.setLayout(layout)

        self.sort_timer = QTimer()
        self.sort_timer.timeout.connect(self.animate_sorting)

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene, self)
        self.view.setStyleSheet("background: transparent;")
        self.view.setGeometry(0, 0, self.width(), self.height())
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setFrameShape(QGraphicsView.NoFrame)
        self.view.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.view.setVisible(False)

    def resizeEvent(self, event):
        self.view.setGeometry(0, 0, self.width(), self.height())

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.folder = folder
            self.label.setText(f"Selected: {folder}")
            self.organize_button.setEnabled(True)

    def animate_sorting(self):
        dots = "." * (self.sort_animation_step % 4)
        self.organize_button.setText(f"Sorting{dots}")
        self.sort_animation_step += 1

    def launch_flying_thumbnails(self, count):
        self.scene.clear()
        self.view.setVisible(True)
        for i in range(count):
            pixmap = QPixmap("icon.png").scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            item = QGraphicsPixmapItem(pixmap)
            start_x = random.randint(50, self.width() - 50)
            start_y = random.randint(50, self.height() - 200)
            item.setPos(start_x, start_y)
            self.scene.addItem(item)

            end_pos = QPointF(self.width() / 2, self.height() - 40)

            anim = QVariantAnimation()
            anim.setDuration(800)
            anim.setStartValue(QPointF(start_x, start_y))
            anim.setEndValue(end_pos)
            anim.valueChanged.connect(lambda value, itm=item: itm.setPos(value))
            anim.finished.connect(lambda itm=item: self.scene.removeItem(itm))
            anim.start()

    def organize_files(self):
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.log.clear()
        self.sort_animation_step = 0
        self.sort_timer.start(300)

        files = [f for f in os.listdir(self.folder) if os.path.isfile(os.path.join(self.folder, f))]
        total_files = len(files)
        moved_files = 0
        category_counts = {}

        self.launch_flying_thumbnails(min(8, total_files))

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
                category_counts[category] = category_counts.get(category, 0) + 1
            except Exception as e:
                self.log.append(f"Error moving '{item}': {e}")
            self.progress.setValue(int(((i + 1) / total_files) * 100))

        self.sort_timer.stop()
        self.organize_button.setText("Sort Now")
        self.log.append(f"\n✅ Sorted {moved_files} files.")
        self.progress.setValue(100)

        QTimer.singleShot(1000, lambda: self.view.setVisible(False))

        summary = SummaryDialog(moved_files, category_counts)
        summary.exec_()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileOrganizer()
    window.show()
    sys.exit(app.exec_())
