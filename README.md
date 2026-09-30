# File Organizer

File Organizer helps users automatically sort cluttered directories into categorized folders based on file types. It takes a messy target folder, groups files into specific categories like images or code, and moves them into clean subdirectories. This provides a straightforward way to keep file systems tidy without complex configurations.

## System Architecture

```mermaid
flowchart LR
  CLI["Command Line Interface"]
  GUI["Desktop GUI"]
  Script["Organizer Core"]
  FS["File System"]
  Log[("moves.json Log")]

  CLI --> Script
  GUI --> Script
  Script --> FS
  Script --> Log

  style CLI fill:#1e1b4b,stroke:#6366f1,stroke-width:2px,color:#fff
  style GUI fill:#042f2e,stroke:#14b8a6,stroke-width:2px,color:#fff
  style Script fill:#2e1065,stroke:#8b5cf6,stroke-width:2px,color:#fff
  style FS fill:#0f172a,stroke:#3b82f6,stroke-width:2px,color:#fff
  style Log fill:#4c0519,stroke:#ef4444,stroke-width:2px,color:#fff
```

## Installation

```bash
pip install -r requirements.txt
```

Requires Python 3.10+.

## Usage (CLI)

Run the script with a command and, for `organize`, an optional target path:

```bash
py organizer.py organize [path]       # sort a directory into category folders
py organizer.py revert                 # undo all file moves from the last organize run
py organizer.py revert_file <id...>    # undo specific moves by ID, e.g. 4  or  1,3,7-9
py organizer.py history                # print the move log with IDs
py organizer.py clear                  # wipe the move log
```

`organize` defaults to `~/Downloads/telegram_desktop` when no path is given, so you can pass an absolute path or a valid home-relative path to target any directory.

When organizing, the script iterates through the target directory, prints each file it finds, and shows exactly which folder it is being moved to. It generates an atomic `moves.json` file next to the script (or next to the executable when packaged) to log the original and new locations of every moved file, assigning each an ID so `revert` or `revert_file` can restore files to their original locations.

## Usage (GUI)

```bash
py gui.py
```

If you built the standalone executable, just run `FileOrganizer.exe`.

The window lets you:

* **Browse** to a folder and click **Organize Files** to sort it into category folders.
* **Revert All** to undo every logged move.
* **Revert specific files by ID** — type one id or many (`4`, or `1, 3, 7-9`) and click **Revert IDs**. Click **History** to list the ids.
* **Cancel** a running job at any time.

Long jobs run on a background thread, so the window never freezes, and **Cancel** stops the run between files.

## Features

* Automatically sorts files by their extensions.
* Creates destination folders automatically if they do not exist.
* Groups common files into Code, Images, Audio, Video, Archive, Documents, and Programs.
* Intelligently parses video filenames using Guessit to group TV shows and movies into specific dedicated folders.

```mermaid
sequenceDiagram
  actor User
  participant Script
  participant FS as "File System"
  participant Log as "moves.json"

  User->>Script: Run organize command
  Script->>FS: Scan target directory
  FS->>Script: Return file list
  Script->>Script: Extract media titles and determine target folders
  Script->>FS: Move files to categorized destinations
  Script->>Log: Save move history atomically
```

* Catches unrecognized extensions and moves them safely to an isolated Unknown folder.
* Safely skips directories to avoid breaking nested folder structures.
* Tracks all file movements with unique IDs in an atomic, crash-proof JSON log that automatically retries if files are locked.
* Includes global (`revert`), selected-by-ID (`revert_file`), and single-file revert functions to safely undo the organization process.

```mermaid
sequenceDiagram
  actor User
  participant Script
  participant Log as "moves.json"
  participant FS as "File System"

  User->>Script: Run revert_file <id...>
  Script->>Log: Read move history
  Log->>Script: Return move records
  Script->>FS: Move specific file back to original source path
  Script->>Log: Mark history entry as reverted
```

* Ships with a desktop GUI (ttkbootstrap) that runs every job on a background thread, so the window stays responsive and long runs can be cancelled.
* Builds into a standalone Windows executable, so it can run on a machine without Python installed.

## Building the executable

Package the GUI into a single `FileOrganizer.exe` with PyInstaller:

```bash
pip install pyinstaller
py -m PyInstaller gui.spec
```

The result lands in `dist/FileOrganizer.exe`. The committed `gui.spec` already:

* bundles the data files and dynamic modules that `guessit`/`babelfish` need (neither ships a PyInstaller hook),
* disables UPX, since compressed executables frequently trip antivirus false positives,
* embeds the app icon (`app.ico`, regenerated with `make_icon.py`).

When packaged, `moves.json` is written **next to the executable**, so keep the `.exe` in a writable folder (not, for example, `C:\Program Files`).

## Technologies Used

| Technology | Purpose |
| :--- | :--- |
| [Python](https://www.python.org/) | Core language environment |
| [Pathlib](https://docs.python.org/3/library/pathlib.html) | Object-oriented filesystem path handling |
| [Shutil](https://docs.python.org/3/library/shutil.html) | High-level file operations and moving |
| [JSON](https://docs.python.org/3/library/json.html) | State tracking and move history logging |
| [Guessit](https://guessit.readthedocs.io/en/latest/) | Extracts clean media titles from video file names |
| [Tkinter / ttkbootstrap](https://ttkbootstrap.readthedocs.io/) | Desktop GUI and dark theming |
| [PyInstaller](https://pyinstaller.org/) | Packages the app into a standalone Windows executable |

## Author Info

* LinkedIn: https://linkedin.com/in/deelolade
* X (Twitter): https://x.com/deelolade

## Built With

[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

[![Readme was generated by Dokugen](https://img.shields.io/badge/Readme%20was%20generated%20by-Dokugen-brightgreen)](https://dokugen.samueltuoyo.com)