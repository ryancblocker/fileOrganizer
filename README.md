# File Organizer

A Python-based file organization tool that helps you keep your directories clean and organized by automatically sorting files into categorized folders based on their file types. The tool uses a modern PyQt6-based GUI with enhanced features and sleek aesthetics.

## Features

### Core Features
- Automatically organizes files into categorized folders
- Supports multiple file categories (Images, Documents, Videos, Audio, Archives, Code, etc.)
- Includes preview mode to see changes before making them
- Supports undo functionality for reverting the last organization
- Maintains a detailed log of all operations

### Interface Features
- Modern and polished PyQt6-based user interface
- Enhanced visual feedback with progress tracking
- Drag and drop support for easy file organization
- Custom styling and icons
- Real-time operation logging
- Folder selection via browse button

## File Categories

The organizer sorts files into the following categories:
- **Images**: .jpg, .jpeg, .png, .gif, .bmp
- **Documents**: .pdf, .docx, .doc, .txt, .xlsx, .pptx
- **Videos**: .mp4, .mov, .avi, .mkv
- **Audio**: .mp3, .wav, .aac
- **Archives**: .zip, .rar, .7z, .tar, .gz
- **Code**: .py, .js, .html, .css, .cpp, .java, .c
- **Others**: Any file type not listed above

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/ryancblocker/fileOrganizer.git
   cd fileOrganizer
   ```

2. Set up a virtual environment (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```

3. Install required packages:
   ```bash
# Install required packages
   pip install PyQt6 pyinstaller pillow
   ```

## Usage

### Running the Application

You can run the application in two ways:

1. **Run from Source**
```bash
python file_organizer_pyqt.py
```

2. **Use the macOS App**
- Download the latest release
- Move the `File Organizer.app` to your Applications folder
- Launch it like any other macOS application

### Features
- Modern and polished interface
- Drag and drop support for easy file organization
- Progress tracking with visual feedback
- Enhanced logging with success indicators
- Customizable themes and icons
- One-click organization

## Logging

The tool maintains two types of logs:
- `file_organizer_log.txt`: Detailed log of all file operations
- `undo_log.json`: Information needed to undo the last operation

## Contributing

Feel free to fork the repository and submit pull requests. You can also open issues for bugs or feature requests.

## License

This project is open source and available under the MIT License.
