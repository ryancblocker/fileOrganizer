# File Organizer

A Python-based file organization tool that helps you keep your directories clean and organized by automatically sorting files into categorized folders based on their file types. The tool comes with both a command-line interface (CLI) and a graphical user interface (GUI).

## Features

- Automatically organizes files into categorized folders
- Supports multiple file categories (Images, Documents, Videos, Audio, Archives, Code, etc.)
- Provides both CLI and GUI interfaces
- Includes preview mode to see changes before making them
- Supports undo functionality for reverting the last organization
- Maintains a detailed log of all operations
- macOS-friendly GUI design

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

## Usage

### Command Line Interface (CLI)

The CLI version offers several options:

```bash
python file_organizer.py [--folder PATH] [--preview] [--undo]
```

Options:
- `--folder`: Specify the folder to organize (defaults to ~/Downloads)
- `--preview`: Preview changes without actually moving files
- `--undo`: Revert the last organization operation

Examples:
```bash
# Organize downloads folder
python file_organizer.py

# Organize a specific folder
python file_organizer.py --folder /path/to/folder

# Preview changes without moving files
python file_organizer.py --preview

# Undo last organization
python file_organizer.py --undo
```

### Graphical User Interface (GUI)

To launch the GUI version:

```bash
python file_organizer_gui.py
```

The GUI provides a user-friendly interface with:
- Folder selection via browse button
- One-click organization
- Real-time operation logging
- macOS-optimized design

## Logging

The tool maintains two types of logs:
- `file_organizer_log.txt`: Detailed log of all file operations
- `undo_log.json`: Information needed to undo the last operation

## Contributing

Feel free to fork the repository and submit pull requests. You can also open issues for bugs or feature requests.

## License

This project is open source and available under the MIT License.
