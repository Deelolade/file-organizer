from pathlib import Path
import shutil

def organize_files(path):
    directory = Path(path).expanduser() # expands the user's home directory and converts the path to a Path object
    if not directory.is_dir(): # checks if the path is a directory
        print(f"{path} is not a directory")
        return
    
    # print(f"Organizing files in {path}")
    code_extensions ={".py", ".js", ".jsx", ".ts", ".tsx"}
    doc_extensions = {".txt", ".docx", ".pdf"}
    image_extensions ={".png", ".jpeg", ".jpg", ".gif"}
    audio_extensions = {".mp3", ".wav"}
    video_extensions = {".mp4", ".mov"}
    archive_extensions = {".zip", ".tar", ".gz"}

    for file in  directory.iterdir(): #iterdir() short for "iterate directory", used to iterate over files in a directory
        # print(file.name) # prints the file name 
        if(file.is_file()):
            print(file.name)
            
            if file.suffix in code_extensions:
                print(f"{file.name} → Code")
                code_dir = directory / "Code"
                code_dir.mkdir(exist_ok=True)
                shutil.move(file, code_dir)
                
                
            elif file.suffix in image_extensions:
                print(f"{file.name} → Image")
                image_dir = directory / "Images"
                image_dir.mkdir(exist_ok=True)
                shutil.move(file, image_dir)
                
            elif file.suffix in audio_extensions:
                print(f"{file.name} → Audio")
                audio_dir = directory / "Audio"
                audio_dir.mkdir(exist_ok=True)
                shutil.move(file, audio_dir)
                
            elif file.suffix in video_extensions:
                print(f"{file.name} → Video")
                video_dir = directory / "Video"
                video_dir.mkdir(exist_ok=True)
                shutil.move(file, video_dir)
                
            elif file.suffix in archive_extensions:
                print(f"{file.name} → Archive")
                archive_dir = directory / "Archive"
                archive_dir.mkdir(exist_ok=True)
                shutil.move(file, archive_dir)
                
            elif file.suffix in doc_extensions:
                print(f"{file.name} → Document")
                doc_dir = directory / "Documents"
                doc_dir.mkdir(exist_ok=True)
                shutil.move(file, doc_dir)
            else:
                print(f"{file.suffix} -> unknown")
                unknown_dir = directory / "Unknown"
                unknown_dir.mkdir(exist_ok=True)
                shutil.move(file, unknown_dir)
            # this version will be overkill for this implementation
            # if(re.match(r"\.(py|js|jsx|ts|tsx)$", file.suffix)):
            #     print(f"{file.name} is a code file")
            # elif(re.match(r"\.txt$", file.suffix)):
            #     print(f"{file.name} is a text file")
            # elif(re.match(r"\.(png|mp3|mp4|jpeg)$", file.suffix)):
            #     print(f"{file.name} is a media file")
            # else:
            #     print(f"{file.suffix} has not been acknowledged yet!!")

organize_files("~/Documents/desktop-project/python/assets")