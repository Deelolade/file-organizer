from pathlib import Path
import shutil
import json
import os
import re
import sys
import time

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
    """Write the move log atomically, retrying on transient file locks.

    Windows can briefly hold a lock on moves.json (editor file watchers,
    OneDrive sync, antivirus), which surfaces as OSError [Errno 22/13].
    Writing to a temp file and replacing avoids partial writes and reduces
    the window for those locks. Returns True on success.
    """
    tmp = moves_file.with_name(moves_file.name + ".tmp")
    last_exc = None

    for attempt in range(5):
        try:
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(moves, f, indent=4)
            os.replace(tmp, moves_file)
            return True
        except OSError as exc:
            last_exc = exc
            time.sleep(0.2 * (attempt + 1))

    # Fallback: some locks only block replace(), not an in-place rewrite.
    try:
        with moves_file.open("w", encoding="utf-8") as f:
            json.dump(moves, f, indent=4)
        return True
    except OSError as exc:
        last_exc = exc

    print(f"Error: could not save moves.json: {last_exc}")
    return False


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
    program_extensions = {".exe", ".msi"}

    moves = load_moves()
    pending = 0
    moved_count = 0

    # Take a snapshot of the files before moving anything.
    for file in list(directory.iterdir()):
        if not file.is_file():
            continue

        if file.resolve() == moves_file.resolve():
            continue

        extension = file.suffix.lower()

        if extension in code_extensions:
            destination = directory / "Code"
        elif extension in image_extensions:
            destination = directory / "Images"
        elif extension in audio_extensions:
            destination = directory / "Audio"
        elif extension in program_extensions:
            destination = directory / "Programs"
        elif extension in video_extensions:
            title = extract_title(file.name)

            if title and title.lower() != file.stem.lower():
                # Remove characters that are invalid in Windows folder names.
                title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", title)
                title = title.strip(" .")

            if title:
                destination = directory / title
            else:
                destination = directory / "Video"
        elif extension in archive_extensions:
            destination = directory / "Archive"
        elif extension in doc_extensions:
            destination = directory / "Documents"
        else:
            destination = directory / "Unknown"

        print(f"{file.name} → {destination.name}", flush=True)

        if move_files(file, destination, moves):
            pending += 1
            moved_count += 1

            # Best-effort checkpoint every 20 moves (crash safety). The
            # authoritative save happens once at the end, so a failed
            # checkpoint is never fatal.
            if pending >= 20:
                save_moves(moves)
                pending = 0

    # Final authoritative save; retries are handled inside save_moves.
    if moved_count:
        if save_moves(moves):
            print(f"\nOrganization complete. {moved_count} files moved.")
        else:
            print(
                f"\nOrganization complete. {moved_count} files moved, "
                "but the move log could not be saved — re-run `revert` "
                "after fixing file access to moves.json."
            )

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

def revert_file(file_id, moves):
    # this will be the function to revert one file to it original source
    for move in moves:
       if move.get("id") == file_id
            break
    else : 
        print(f"File with Id {file_id} does not exist.")
        return
    if move.get("reverted"):
        print(f"File with id {file_id} has already been reverted.")
        return
    destination = Path(move["destination"])
    source = Path(move["source"])
        
    if not destination.exists():
        print(f"{destination.name} was not found at its destination.")
        return
    if source.is_dir():
        target = source / destination.name
    else:
        target = source
        
        target.parent.mkdir(parents=True, exist_ok=True)
        
    if target.exists():
        print(f"{target.name} already exists at {target}.")
        return
        
    try:
        shutil.move(str(destination), str(target))
    except OSError as exc:
        print(f"Failed to revert {destination.name}: {exc}")
        return
        
    move["reverted"] = True
    save_moves(moves)  
    
    print(f"Reverted #{file_id}: {destination.name} → {target}")

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
    if save_moves([]):
        print("=== History cleared ===")
    else:
        print("=== Failed to clear history ===")


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
    elif command == "revert-file":
        if len(args) < 2:
            print("Usage: py organizer.py revert-file <id>")
            sys.exit(1)
        file_id = int(args[1])
        revert_file(file_id,load_moves())
    elif command == "history":
        history(load_moves())
    elif command == "clear":
        clear_history()
    else:
        print(f"Unknown command: {command}")
