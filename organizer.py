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


def _log(message, on_log=None):
    """Send a message to a callback when provided, otherwise print it."""
    if on_log is not None:
        on_log(message)
    else:
        print(message, flush=True)


def move_files(file, destination_dir, moves, on_log=None):
    if not file.is_file():
        _log(f"Skipping {file.name}: source no longer exists", on_log)
        return False

    destination = destination_dir / file.name

    try:
        destination_dir.mkdir(parents=True, exist_ok=True)

        if destination.exists():
            _log(f"Skipping {file.name}: already exists", on_log)
            return False

        shutil.move(str(file), str(destination))

    except OSError as exc:
        _log(f"Failed to move {file.name}: {exc}", on_log)
        return False

    source = str(file)
    dest = str(destination)

    # Reuse an existing entry for this file (same source → destination) and
    # reset it to not-reverted, so a previously-reverted file can be organized
    # and reverted again instead of piling up duplicate log entries.
    for existing in moves:
        if existing.get("source") == source and existing.get("destination") == dest:
            existing["reverted"] = False
            break
    else:
        moves.append({
            "id": max((m.get("id", 0) for m in moves), default=0) + 1,
            "source": source,
            "destination": dest,
            "reverted": False,
        })

    _log(f"Moved {file.name} to {destination}", on_log)
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


def sanitize_folder_name(name):
    """Remove characters that are invalid in Windows folder names and trim
    trailing dots/spaces, which Windows also rejects."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name)
    return name.strip(" .")


def organize_files(path, on_log=None, should_stop=None):
    directory = Path(path).expanduser()

    if not directory.is_dir():
        _log(f"{path} is not a directory", on_log)
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
    cancelled = False
    for file in list(directory.iterdir()):
        if should_stop is not None and should_stop():
            cancelled = True
            break

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
                title = sanitize_folder_name(title)

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

        _log(f"{file.name} → {destination.name}", on_log)

        if move_files(file, destination, moves, on_log):
            pending += 1
            moved_count += 1

            # Best-effort checkpoint every 20 moves (crash safety). The
            # authoritative save happens once at the end, so a failed
            # checkpoint is never fatal.
            if pending >= 20:
                save_moves(moves)
                pending = 0

    # Final authoritative save; retries are handled inside save_moves.
    if moved_count and not save_moves(moves):
        _log(
            "Warning: the move log could not be saved — re-run `revert` "
            "after fixing file access to moves.json.",
            on_log,
        )

    if cancelled:
        _log(f"Cancelled. {moved_count} file(s) moved.", on_log)
    elif moved_count:
        _log(f"Organization complete. {moved_count} files moved.", on_log)

def revert_moves(moves, on_log=None, should_stop=None):
    if not moves:
        _log("No moves to revert", on_log)
        return

    updated = False
    for move in reversed(moves):
        if should_stop is not None and should_stop():
            _log("Cancelled.", on_log)
            break

        if move.get("reverted"):
            continue

        destination = Path(move["destination"])
        source = Path(move["source"])

        if not destination.exists():
            _log(f"Skipping {destination.name}: not found at {destination}", on_log)
            continue

        # Older logs store `source` as a directory; newer logs store the full
        # original file path. Handle both.
        if source.is_dir():
            target = source / destination.name
        else:
            target = source

        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists():
            _log(f"Skipping {destination.name}: already exists at {target}", on_log)
            continue

        try:
            shutil.move(str(destination), str(target))
        except OSError as exc:
            _log(f"Failed to revert {destination.name}: {exc}", on_log)
            continue

        move["reverted"] = True
        updated = True
        _log(f"Reverted {destination.name} to {target}", on_log)

        # Clean up the category folder if it is now empty.
        try:
            dest_dir = destination.parent
            if dest_dir.is_dir() and not any(dest_dir.iterdir()):
                dest_dir.rmdir()
                _log(f"Removed empty directory: {dest_dir}", on_log)
        except OSError:
            pass

    if updated:
        save_moves(moves)

def parse_ids(text):
    """Parse an id spec like '1, 3, 7-9' into a de-duplicated list of ints."""
    ids = []
    for part in re.split(r"[,\s]+", text.strip()):
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            start, end = int(lo), int(hi)
            if end < start:
                start, end = end, start
            ids.extend(range(start, end + 1))
        else:
            ids.append(int(part))

    seen = set()
    unique = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            unique.append(i)
    return unique


def revert_file(file_id, moves, on_log=None):
    """Revert a single move (by its id) back to its original location.

    Returns True if the file was moved back, False otherwise.
    """
    move = None
    for entry in moves:
        if entry.get("id") == file_id:
            move = entry
            break

    if move is None:
        _log(f"No move found with id {file_id}.", on_log)
        return False

    if move.get("reverted"):
        _log(f"File with id {file_id} has already been reverted.", on_log)
        return False

    destination = Path(move["destination"])
    source = Path(move["source"])

    if not destination.exists():
        _log(f"{destination.name} was not found at {destination}.", on_log)
        return False

    # Older logs store `source` as a directory; newer logs store the full
    # original file path. Handle both.
    if source.is_dir():
        target = source / destination.name
    else:
        target = source

    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        _log(f"{target.name} already exists at {target}.", on_log)
        return False

    try:
        shutil.move(str(destination), str(target))
    except OSError as exc:
        _log(f"Failed to revert {destination.name}: {exc}", on_log)
        return False

    move["reverted"] = True
    save_moves(moves)

    _log(f"Reverted #{file_id}: {destination.name} → {target}", on_log)

    # Clean up the category folder if it is now empty.
    try:
        dest_dir = destination.parent
        if dest_dir.is_dir() and not any(dest_dir.iterdir()):
            dest_dir.rmdir()
            _log(f"Removed empty directory: {dest_dir}", on_log)
    except OSError:
        pass

    return True


def revert_files(ids, moves, on_log=None, should_stop=None):
    """Revert a specific set of move ids (not the whole log)."""
    ids = list(ids)
    if not ids:
        _log("No ids given.", on_log)
        return

    reverted = 0
    for file_id in ids:
        if should_stop is not None and should_stop():
            _log("Cancelled.", on_log)
            break
        if revert_file(file_id, moves, on_log):
            reverted += 1

    _log(f"Done. Reverted {reverted} of {len(ids)} requested id(s).", on_log)

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
        print("Usage: python organizer.py <organize|revert|revert_file|history|clear> [path]")
        sys.exit(1)

    command = args[0].lower()
    if command == "organize":
        path = args[1] if len(args) > 1 else "~/Downloads/telegram_desktop"
        organize_files(path)
    elif command == "revert":
        revert_moves(load_moves())
        
    elif command in ("revert_file", "revert-file"):
        if len(args) < 2:
            print("Usage: py organizer.py revert_file <id> [id ...]   e.g. 1,3,7-9")
            sys.exit(1)
        try:
            ids = parse_ids(" ".join(args[1:]))
        except ValueError:
            print(f"Invalid id list: {' '.join(args[1:])}")
            sys.exit(1)
        revert_files(ids, load_moves())
        
    elif command == "history":
        history(load_moves())
    elif command == "clear":
        clear_history()
    else:
        print(f"Unknown command: {command}")
