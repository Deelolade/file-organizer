from pathlib import Path
import shutil
import json


moves_file = Path("moves.json")

def load_moves():
    if  not moves_file.exists():
        return []
    if moves_file.stat().st_size == 0:
        return []
    try:
       with moves_file.open("r") as f:
          return json.load(f) 
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {moves_file}")
        return []
    
def save_moves(destination, source):
    moves = load_moves()
    
    moves.append({"destination": str(destination), "source": str(source)})
    with moves_file.open("w") as f:
        json.dump(moves, f, indent=4)

def move_files(file, destination_dir):
    destination_dir.mkdir(exist_ok=True)
    destination = destination_dir / file.name
    shutil.move(file, destination)
    save_moves(destination, file.parent)
    print(f"Moved {file.name} to {destination}")
    

def organize_files(path):
    directory = Path(path).expanduser() # expands the user's home directory and converts the path to a Path object
    if not directory.is_dir(): # checks if the path is a directory
        print(f"{path} is not a directory")
        return

    # print(f"Organizing files in {path}")
    code_extensions ={".py", ".js", ".jsx", ".ts", ".tsx"}
    doc_extensions = {".txt", ".docx", ".pdf"}
    image_extensions ={".png", ".jpeg", ".jpg", ".gif", ".webp"}
    audio_extensions = {".mp3", ".wav"}
    video_extensions = {".mp4", ".mov"}
    archive_extensions = {".zip", ".tar", ".gz"}
    # this temporarily stores the files to be moved, it contains tuples of (original source, new destination)
    
    for file in  directory.iterdir(): #iterdir() short for "iterate directory", used to iterate over files in a directory
        # print(file.name) # prints the file name
        if(file.is_file()):
            print(file.name)

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
                print(f"{file.name} → Video")
                move_files(file, directory / "Video")

            elif file.suffix in archive_extensions:
                print(f"{file.name} → Archive")
                move_files(file, directory / "Archive")

            elif file.suffix in doc_extensions:
                print(f"{file.name} → Document")
                move_files(file, directory / "Documents")
            else:
                print(f"{file.suffix} -> unknown")
                move_files(file, directory / "Unknown")
            # this version will be overkill for this implementation
            # if(re.match(r"\.(py|js|jsx|ts|tsx)$", file.suffix)):
            #     print(f"{file.name} is a code file")
            # elif(re.match(r"\.txt$", file.suffix)):
            #     print(f"{file.name} is a text file")
            # elif(re.match(r"\.(png|mp3|mp4|jpeg)$", file.suffix)):
            #     print(f"{file.name} is a media file")
            # else:
            #     print(f"{file.suffix} has not been acknowledged yet!!")



def revert_moves(moves):
    for move in reversed(moves):
        destination = Path(move["destination"])
        source = Path(move["source"])

        if not destination.exists():
            print(f"Skipping {destination.name}: not found at {destination}")
            continue
        source.mkdir(parents=True, exist_ok=True)
        shutil.move(destination, source)
        print(f"Reverted {destination.name} to {source}")

def history(moves):
    if not moves:
        print("No file moves recorded")
        return  
    print(f"\n === File Move History ===")
    print(f"\n === You have {len(moves)} file moves recorded ===")
    for i, move in enumerate(moves): 
        print(f"\n{i+1}.")
        print(f" \t From: {move['source']}")
        print(f" \t To: {move['destination']}")

# organize_files("~/Documents/desktop-project/python/assets")
# revert_moves(load_moves())
history(load_moves())