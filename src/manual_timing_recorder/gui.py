"""Timing Capture GUI — procedural tkinter, state in g."""

import json
import time
import tkinter as tk
import uuid
from tkinter import filedialog, ttk

import lionscliapp as app

# ---------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------

IDLE      = "IDLE"
RECORDING = "RECORDING"
STOPPED   = "STOPPED"

# ---------------------------------------------------------------------------
# Allowed keys
# ---------------------------------------------------------------------------

LETTERS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
NUMBERS = set("0123456789")
FKEYS   = {f"F{i}" for i in range(1, 13)}

# ---------------------------------------------------------------------------
# Global state bundle
# ---------------------------------------------------------------------------

g = {}


def setup_globals():
    g["TK"]          = None   # root window
    g["W"]           = {}     # widget dictionary
    g["state"]       = IDLE
    g["timings"]     = []     # [[raw_elapsed_seconds, key], ...]
    g["rec_start"]   = None   # perf_counter value at recording start
    g["norm_offset"] = None   # first-key offset when normalize is active


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def launch():
    """Launch the Timing Capture window. Called by lionscliapp default command."""
    setup_globals()
    root = tk.Tk()
    g["TK"] = root
    g["W"]  = {}
    build_ui()
    root.mainloop()


# ---------------------------------------------------------------------------
# UI construction
# ---------------------------------------------------------------------------

def build_ui():
    root = g["TK"]
    root.title("Timing Capture")
    root.minsize(360, 240)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(1, weight=1)

    build_menubar()
    build_toolbar()    # row 0
    build_treeview()   # row 1

    root.bind("<KeyPress>", handle_keypress)
    root.bind("<Control-e>", lambda e: export_timings())
    root.bind("<Control-q>", lambda e: root.destroy())


def build_menubar():
    root = g["TK"]
    W    = g["W"]

    menubar = tk.Menu(root, tearoff=False)

    file_menu = tk.Menu(menubar, tearoff=False)
    file_menu.add_command(label="Export Timings", accelerator="Ctrl+E", command=export_timings)
    file_menu.add_separator()
    file_menu.add_command(label="Quit", accelerator="Ctrl+Q", command=root.destroy)
    menubar.add_cascade(label="File", menu=file_menu)

    W["normalize_var"] = tk.BooleanVar(value=False)
    edit_menu = tk.Menu(menubar, tearoff=False)
    edit_menu.add_checkbutton(label="Normalize On First Key", variable=W["normalize_var"])
    menubar.add_cascade(label="Edit", menu=edit_menu)

    root.config(menu=menubar)


def build_toolbar():
    root = g["TK"]
    W    = g["W"]

    frame = ttk.Frame(root, padding=4)
    frame.grid(row=0, column=0, sticky="ew")

    W["btn_record"] = ttk.Button(frame, text="Record", command=start_recording)
    W["btn_record"].grid(row=0, column=0, padx=(0, 4))

    W["btn_stop"] = ttk.Button(frame, text="Stop", command=stop_recording)
    W["btn_stop"].grid(row=0, column=1)


def build_treeview():
    root = g["TK"]
    W    = g["W"]

    frame = ttk.Frame(root)
    frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)

    tree = ttk.Treeview(frame, columns=("key", "timestamp"), show="headings")
    tree.heading("key",       text="Key")
    tree.heading("timestamp", text="Timestamp (mm:ss:ms)")
    tree.column("key",       width=80,  stretch=False)
    tree.column("timestamp", width=240, stretch=True)

    scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)

    tree.grid(row=0,  column=0, sticky="nsew")
    scroll.grid(row=0, column=1, sticky="ns")

    W["tree"] = tree


# ---------------------------------------------------------------------------
# Recording control
# ---------------------------------------------------------------------------

def start_recording():
    g["timings"].clear()
    g["norm_offset"] = None
    g["rec_start"]   = time.perf_counter()
    g["state"]       = RECORDING
    clear_tree()
    g["TK"].focus_set()


def stop_recording():
    if g["state"] == RECORDING:
        g["state"] = STOPPED


# ---------------------------------------------------------------------------
# Key capture
# ---------------------------------------------------------------------------

def handle_keypress(event):
    """Castle gate: validate key, then record timing."""
    if g["state"] != RECORDING:
        return
    key = classify_key(event.keysym)
    if key is None:
        return
    record_key(key)


def classify_key(keysym):
    """Return normalized key string, or None if not in allowed set."""
    upper = keysym.upper()
    if upper in LETTERS:
        return upper
    if upper in NUMBERS:
        return upper
    if keysym in FKEYS:
        return keysym
    if keysym == "space":
        return "SPACE"
    return None


def record_key(key):
    """Append timing entry and update the treeview."""
    elapsed = time.perf_counter() - g["rec_start"]

    normalize = g["W"]["normalize_var"].get()
    if normalize and g["norm_offset"] is None:
        g["norm_offset"] = elapsed
        g["timings"].append([elapsed, key])
        refresh_tree()
    else:
        g["timings"].append([elapsed, key])
        display = elapsed - (g["norm_offset"] or 0.0)
        append_tree_row(key, display)


# ---------------------------------------------------------------------------
# Treeview helpers
# ---------------------------------------------------------------------------

def format_timestamp(seconds):
    """Format seconds as MM:SS:MMM."""
    ms_total = max(0, int(round(seconds * 1000)))
    minutes  = ms_total // 60000
    ms_total %= 60000
    secs     = ms_total // 1000
    ms       = ms_total % 1000
    return f"{minutes:02d}:{secs:02d}:{ms:03d}"


def clear_tree():
    tree = g["W"]["tree"]
    for item in tree.get_children():
        tree.delete(item)


def append_tree_row(key, seconds):
    g["W"]["tree"].insert("", tk.END, values=(key, format_timestamp(seconds)))


def refresh_tree():
    """Rebuild treeview from g['timings'], applying current norm_offset."""
    clear_tree()
    offset = g["norm_offset"] or 0.0
    for raw, key in g["timings"]:
        append_tree_row(key, raw - offset)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_timings():
    out_dir    = app.ctx["path.output"]
    initialdir = str(out_dir) if out_dir.is_dir() else None

    path = filedialog.asksaveasfilename(
        initialdir=initialdir,
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        title="Export Timings",
    )
    if not path:
        return

    normalize = g["W"]["normalize_var"].get()
    offset    = (g["norm_offset"] or 0.0) if normalize else 0.0
    indent    = int(app.ctx["json.indent.timings"])

    data = {
        "document": {
            "document-id": f"generated-timings.{uuid.uuid4()}",
            "purpose": "blank",
            "title": "Untitled",
            "type": {
                "logical": {
                    "base": "file",
                    "format": "json",
                    "encoding": "utf-8",
                    "format_version": "timings.v1",
                }
            },
        },
        "timings": [[raw - offset, key] for raw, key in g["timings"]],
    }

    with open(path, "w", encoding="utf-8") as f:
        if indent == 0:
            json.dump(data, f, separators=(",", ":"))
        else:
            json.dump(data, f, indent=indent)
        f.write("\n")
