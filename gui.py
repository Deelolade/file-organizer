import queue
import threading

import tkinter as tk
from tkinter import filedialog

import ttkbootstrap as ttk

import organizer

# ---------------------------------------------------------------------------
# App state
# ---------------------------------------------------------------------------
root = ttk.Window(themename="darkly")
root.title("File Organizer")
root.geometry("780x660")
root.minsize(620, 540)

# The worker thread only pushes messages here; the main thread drains it, so
# widgets are never touched off the main thread.
ui_queue = queue.Queue()
cancel_event = threading.Event()
worker = None


# ---------------------------------------------------------------------------
# Helpers (widgets they reference are created further down)
# ---------------------------------------------------------------------------
def log_write(message):
    log.configure(state="normal")
    log.insert("end", message + "\n")
    log.see("end")
    log.configure(state="disabled")


def log_clear():
    log.configure(state="normal")
    log.delete("1.0", "end")
    log.configure(state="disabled")


def set_status(message):
    status.set(message)


def set_running(is_running):
    btn_state = "disabled" if is_running else "normal"
    organize_btn.configure(state=btn_state)
    revert_btn.configure(state=btn_state)
    browse_btn.configure(state=btn_state)
    cancel_btn.configure(state="normal" if is_running else "disabled")
    if is_running:
        progress.start(12)
    else:
        progress.stop()


def browse_folder():
    if worker is not None and worker.is_alive():
        return
    path = filedialog.askdirectory(title="Choose a folder")
    if path:
        folder_path.set(path)
        set_status("Folder selected. Ready to organize.")


def start_job(kind):
    global worker
    if worker is not None and worker.is_alive():
        return  # a job is already running

    path = folder_path.get()
    if kind == "organize" and not path:
        set_status("Please select a folder first.")
        return

    cancel_event.clear()
    log_clear()
    set_running(True)
    set_status("Working...")

    def push(message):
        ui_queue.put(("log", message))

    def run():
        try:
            if kind == "organize":
                organizer.organize_files(
                    path, on_log=push, should_stop=cancel_event.is_set
                )
            else:
                organizer.revert_moves(
                    organizer.load_moves(),
                    on_log=push,
                    should_stop=cancel_event.is_set,
                )
        except Exception as exc:  # keep the window alive on unexpected errors
            ui_queue.put(("log", f"ERROR: {exc}"))
        finally:
            ui_queue.put(("done", kind))

    worker = threading.Thread(target=run, daemon=True)
    worker.start()


def cancel_job():
    if worker is not None and worker.is_alive():
        cancel_event.set()
        set_status("Cancelling...")


def poll_queue():
    try:
        while True:
            kind, payload = ui_queue.get_nowait()
            if kind == "log":
                log_write(payload)
            elif kind == "done":
                set_running(False)
                set_status("Cancelled." if cancel_event.is_set() else "Finished.")
    except queue.Empty:
        pass
    root.after(100, poll_queue)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
main = ttk.Frame(root, padding=25)
main.pack(fill="both", expand=True)

ttk.Label(
    main,
    text="File Organizer",
    font=("Segoe UI", 22, "bold"),
    bootstyle="info",
).pack(anchor="w")

ttk.Label(
    main,
    text="Organize your files into folders automatically.",
    font=("Segoe UI", 10),
    bootstyle="secondary",
).pack(anchor="w", pady=(4, 24))

# Folder selection
folder_card = ttk.Labelframe(
    main, text="  Select folder  ", padding=15, bootstyle="info"
)
folder_card.pack(fill="x", pady=(0, 20))

folder_path = tk.StringVar()

folder_row = ttk.Frame(folder_card)
folder_row.pack(fill="x")

folder_entry = ttk.Entry(folder_row, textvariable=folder_path, state="readonly")
folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

browse_btn = ttk.Button(
    folder_row, text="Browse", bootstyle="info-outline", command=browse_folder
)
browse_btn.pack(side="right")

# Actions
action_row = ttk.Frame(main)
action_row.pack(fill="x", pady=(0, 12))

organize_btn = ttk.Button(
    action_row,
    text="Organize Files",
    bootstyle="success",
    command=lambda: start_job("organize"),
    padding=(15, 10),
)
organize_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))

revert_btn = ttk.Button(
    action_row,
    text="Revert",
    bootstyle="warning",
    command=lambda: start_job("revert"),
    padding=(15, 10),
)
revert_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))

cancel_btn = ttk.Button(
    action_row,
    text="Cancel",
    bootstyle="danger-outline",
    command=cancel_job,
    padding=(15, 10),
    state="disabled",
)
cancel_btn.pack(side="left", expand=True, fill="x")

progress = ttk.Progressbar(main, mode="indeterminate", bootstyle="info-striped")
progress.pack(fill="x", pady=(0, 20))

# Status
status_card = ttk.Labelframe(
    main, text="  Status  ", padding=15, bootstyle="secondary"
)
status_card.pack(fill="x", pady=(0, 20))

status = tk.StringVar(value="Select a folder to get started.")
ttk.Label(status_card, textvariable=status, font=("Segoe UI", 10)).pack(anchor="w")

# Activity log
log_card = ttk.Labelframe(
    main, text="  Activity  ", padding=10, bootstyle="secondary"
)
log_card.pack(fill="both", expand=True)

log = tk.Text(
    log_card,
    height=8,
    wrap="word",
    font=("Consolas", 10),
    bg="#222222",
    fg="#eeeeee",
    insertbackground="white",
    relief="flat",
    padx=10,
    pady=10,
)
log.pack(fill="both", expand=True)
log.insert("end", "Your file activity will appear here.\n")
log.configure(state="disabled")

root.after(100, poll_queue)
root.mainloop()
