from pathlib import Path
import shutil
import json
import re
import sys

from guessit import guessit

moves_file = Path(__file__).resolve().parent / "moves.json"


def load_moves():
    """Load the move log, returning an empty list if it is missing or corrupt."""
    if not moves_file.exists() or moves_file.stat().st_size == 0:
        return []
    try:
        with moves_file.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        print(f"Error decoding JSON from {moves_file}")
        return []


def save_moves(moves):
    """Write the full move log back to disk."""
    with moves_file.open("w", encoding="utf-8") as f:
        json.dump(moves, f, indent=4)


def move_files(file, destination_dir, moves):
    if not file.is_file():
        print(f"Skipping {file.name}: source no longer exists")
        return False

    destination = destination_dir / file.name

    try:
        destination_dir.mkdir(parents=True, exist_ok=True)

        if destination.exists():
            print(f"Skipping {file.name}: already exists")
            return False

        shutil.move(str(file), str(destination))

    except OSError as exc:
        print(f"Failed to move {file.name}: {exc}")
        return False

    moves.append({
        "id": len(moves) + 1,
        "source": str(file),
        "destination": str(destination),
        "reverted": False,
    })

    print(f"Moved {file.name} to {destination}", flush=True)
    return True

def extract_title(file_name):
    # Try guessit first to extract series title
    try:
        guess = guessit(file_name)
        if isinstance(guess, dict) and guess.get("title"):
            title_str = str(guess["title"]).strip()
            if title_str:
                return title_str
    except Exception:
        pass

    # Fallback regex extraction
    stem = Path(file_name).stem
    title = re.sub(r"\[.*?\]", "", stem)
    title = re.sub(r"@\S+", "", title)
    title = re.sub(r"S\d+\s*[-_.]?\s*E?\d+", "", title, flags=re.IGNORECASE)
    title = re.sub(r"^\s*\d+\s*[-_.]\s*", "", title)
    title = re.sub(r"[-_.]\s*\d+\s*$", "", title)
    title = re.sub(r"[-_.]\s*\d{1,4}\b", "", title)
    title = title.strip(" -_.")
    return title


def organize_files(path):
    directory = Path(path).expanduser()
    if not directory.is_dir():
        print(f"{path} is not a directory")
        return

    code_extensions = {".py", ".js", ".jsx", ".ts", ".tsx"}
    doc_extensions = {".txt", ".docx", ".pdf"}
    image_extensions = {".png", ".jpeg", ".jpg", ".gif", ".webp"}
    audio_extensions = {".mp3", ".wav"}
    video_extensions = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
    archive_extensions = {".zip", ".tar", ".gz"}

    for file in directory.iterdir():
        if not file.is_file():
            continue
        if file.resolve() == moves_file.resolve():
            continue

        if file.suffix in code_extensions:
            print(f"{file.name} → Code")
            move_files(file, directory / "Code")
        elif file.suffix in image_extensions:
            print(f"{file.name} → Image")
            move_files(file, directory / "Images")
        elif file.suffix in audio_extensions:
            print(f"{file.name} → Audio")
            move_files(file, directory / "Audio")
        elif file.suffix in video_extensions:
            title = extract_title(file.name)
            if title and title.lower() != file.stem.lower():
                print(f"{file.name} → Series Title: {title}")
                move_files(file, directory / title)
            else:
                print(f"{file.name} → Video")
                move_files(file, directory / "Video")
        elif file.suffix in archive_extensions:
            print(f"{file.name} → Archive")
            move_files(file, directory / "Archive")
        elif file.suffix in doc_extensions:
            print(f"{file.name} → Document")
            move_files(file, directory / "Documents")
        else:
            print(f"{file.suffix} -> Unknown")
            move_files(file, directory / "Unknown")


def revert_moves(moves):
    if not moves:
        print("No moves to revert")
        return

    updated = False
    for move in reversed(moves):
        if move.get("reverted"):
            continue

        destination = Path(move["destination"])
        source = Path(move["source"])

        if not destination.exists():
            print(f"Skipping {destination.name}: not found at {destination}")
            continue

        # Older logs store `source` as a directory; newer logs store the full
        # original file path. Handle both.
        if source.is_dir():
            target = source / destination.name
        else:
            target = source

        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists():
            print(f"Skipping {destination.name}: already exists at {target}")
            continue

        try:
            shutil.move(str(destination), str(target))
        except OSError as exc:
            print(f"Failed to revert {destination.name}: {exc}")
            continue

        move["reverted"] = True
        updated = True
        print(f"Reverted {destination.name} to {target}")

        # Clean up the category folder if it is now empty.
        try:
            dest_dir = destination.parent
            if dest_dir.is_dir() and not any(dest_dir.iterdir()):
                dest_dir.rmdir()
                print(f"Removed empty directory: {dest_dir}")
        except OSError:
            pass

    if updated:
        save_moves(moves)


def history(moves):
    if not moves:
        print("No file moves recorded")
        return
    print("\n === File Move History ===")
    for i, move in enumerate(moves):
        status = " (Reverted)" if move.get("reverted") else ""
        print(f"\n{i+1}.{status}")
        print(f" \t From: {move['source']}")
        print(f" \t To: {move['destination']}")
    print(f"\n === You have {len(moves)} file moves recorded ===")


def clear_history():
    save_moves([])
    print("=== History cleared ===")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("Usage: python organizer.py <organize|revert|history|clear> [path]")
        sys.exit(1)

    command = args[0].lower()
    if command == "organize":
        path = args[1] if len(args) > 1 else "~/Downloads/telegram_desktop"
        organize_files(path)
    elif command == "revert":
        revert_moves(load_moves())
    elif command == "history":
        history(load_moves())
    elif command == "clear":
        clear_history()
    else:
        print(f"Unknown command: {command}")
