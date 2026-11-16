import tkinter as tk
from tkinter import filedialog
import subprocess
import threading
import os
from urllib.parse import urlparse, quote

current_file = None
heading_lines = []


def new_file():
    global current_file
    text.delete("1.0", tk.END)
    current_file = None
    root.title("New File - My Editor")
    refresh_outline()


def open_file():
    global current_file
    path = filedialog.askopenfilename()
    if not path:
        return
    with open(path, "r", encoding="utf-8") as file:
        text.delete("1.0", tk.END)
        text.insert("1.0", file.read())
    current_file = path
    root.title(path)
    refresh_outline()


def save_file():
    global current_file
    if current_file is None:
        current_file = filedialog.asksaveasfilename(defaultextension=".txt")
    if not current_file:
        return
    merged = merge_sections(text.get("1.0", "end-1c"))
    with open(current_file, "w", encoding="utf-8") as file:
        file.write(merged)
    text.delete("1.0", tk.END)
    text.insert("1.0", merged.rstrip("\n"))
    refresh_outline()



def merge_sections(content):
    lines = content.split("\n")
    preamble = []
    h1_order = []            # סדר שמות ה-#
    h1_direct = {}           # שם # -> תוכן ישיר (לפני תת-כותרות)
    h1_sub_order = {}        # שם # -> סדר שמות ה-## שלו
    h1_sub = {}              # שם # -> {שם ## -> תוכן}
    h1_raw = {}              # שם # -> שורת כותרת מקורית
    sub_raw = {}             # (שם #, שם ##) -> שורת כותרת מקורית
    cur_h1 = None
    cur_h2 = None

    for line in lines:
        stripped = line.lstrip()
        level = len(stripped) - len(stripped.lstrip("#"))
        is_h1 = level == 1 and stripped[1:2] == " "
        is_h2 = level == 2 and stripped[2:3] == " "

        if is_h1:
            title = stripped[2:].strip()
            if title not in h1_direct:
                h1_order.append(title)
                h1_direct[title] = []
                h1_sub_order[title] = []
                h1_sub[title] = {}
                h1_raw[title] = line.rstrip()
            cur_h1 = title
            cur_h2 = None
        elif is_h2 and cur_h1 is not None:
            title = stripped[3:].strip()
            if title not in h1_sub[cur_h1]:
                h1_sub_order[cur_h1].append(title)
                h1_sub[cur_h1][title] = []
                sub_raw[(cur_h1, title)] = line.rstrip()
            cur_h2 = title
        else:
            if cur_h1 is None:
                preamble.append(line)
            elif cur_h2 is None:
                h1_direct[cur_h1].append(line)
            else:
                h1_sub[cur_h1][cur_h2].append(line)

    def trim(body):
        while body and not body[0].strip():
            body.pop(0)
        while body and not body[-1].strip():
            body.pop()
        return body

    out = []
    if any(p.strip() for p in preamble):
        out.extend(trim(preamble))
        out.append("")
    for h1 in h1_order:
        out.append(h1_raw[h1])
        direct = trim(h1_direct[h1][:])
        out.extend(direct)
        out.append("")
        for h2 in h1_sub_order[h1]:
            out.append(sub_raw[(h1, h2)])
            body = trim(h1_sub[h1][h2][:])
            out.extend(body)
            out.append("")
    return "\n".join(out).rstrip("\n") + "\n"



def refresh_outline(event=None):
    global heading_lines
    heading_lines = []
    outline.delete(0, tk.END)
    content = text.get("1.0", "end-1c").split("\n")
    for i, line in enumerate(content, start=1):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            hashes = len(stripped) - len(stripped.lstrip("#"))
            if stripped[hashes:hashes+1] == " ":
                title = stripped[hashes:].strip()
                indent = "  " * (hashes - 1)
                outline.insert(tk.END, indent + title)
                heading_lines.append(i)


def jump_to_heading(event=None):
    sel = outline.curselection()
    if not sel:
        return
    line = heading_lines[sel[0]]
    text.mark_set("insert", f"{line}.0")
    text.see(f"{line}.0")
    text.focus_set()

import json

CONFIG_PATH = os.path.expanduser("~/.editor_git.json")


def load_git_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        repo_entry.insert(0, data.get("repo", ""))
        token_entry.insert(0, data.get("token", ""))
    except Exception:
        pass


def save_git_config():
    try:
        data = {"repo": repo_entry.get().strip(), "token": token_entry.get().strip()}
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.chmod(CONFIG_PATH, 0o600)
    except Exception:
        pass


def git_sync():
    token = token_entry.get().strip()
    repo_url = repo_entry.get().strip()
    if not token or not repo_url:
        status_var.set("need token + url")
        return
    save_git_config() 
    p = urlparse(repo_url)
    auth_url = f"{p.scheme}://{quote(token, safe='')}@{p.netloc}{p.path}"
    repo_dir = os.path.dirname(os.path.abspath(current_file)) if current_file else os.getcwd()

    def run():
        try:
            status_var.set("syncing...")
            steps = (
                ["pull", "--rebase", "--autostash", auth_url],
                ["add", "-A"],
                ["commit", "-m", "auto"],
                ["push", auth_url, "HEAD"],
            )
            for args in steps:
                r = subprocess.run(["git", "-C", repo_dir] + args,
                                   capture_output=True, text=True, timeout=60)
                if r.returncode != 0 and args[0] != "commit":
                    status_var.set(f"{args[0]} fail: {r.stderr.strip()[:50]}")
                    return
            status_var.set("synced ok")
        except Exception as e:
            status_var.set(f"error: {e}")
    threading.Thread(target=run, daemon=True).start()


# root
root = tk.Tk()
root.title("My Text Editor")
root.geometry("900x600")

# git bar (נארז ראשון כדי שיופיע למטה)
git_bar = tk.Frame(root, bg="#1e1e1e")
git_bar.pack(side="bottom", fill="x")

tk.Label(git_bar, text="token", bg="#1e1e1e", fg="#d4d4d4").pack(side="left")
token_entry = tk.Entry(git_bar, show="*", width=20, bg="#2a2a2a", fg="#d4d4d4", insertbackground="#d4d4d4")
token_entry.pack(side="left", padx=4)

tk.Label(git_bar, text="repo", bg="#1e1e1e", fg="#d4d4d4").pack(side="left")
repo_entry = tk.Entry(git_bar, width=40, bg="#2a2a2a", fg="#d4d4d4", insertbackground="#d4d4d4")
repo_entry.pack(side="left", padx=4)

status_var = tk.StringVar(value="")
tk.Button(git_bar, text="Pull+Push", command=git_sync).pack(side="left", padx=4)
tk.Label(git_bar, textvariable=status_var, bg="#1e1e1e", fg="#9cdcfe").pack(side="left", padx=4)

# outline + text
paned = tk.PanedWindow(root, orient="horizontal", sashwidth=5)
paned.pack(expand=True, fill="both")

outline = tk.Listbox(paned, font=("Consolas", 12), activestyle="none", bg="#1e1e1e", fg="#d4d4d4", borderwidth=0)
text = tk.Text(paned, font=("Consolas", 14), undo=True, wrap="word", bg="#1e1e1e", fg="#d4d4d4", insertbackground="#d4d4d4")
paned.add(outline)
paned.add(text)

outline.bind("<<ListboxSelect>>", jump_to_heading)
text.bind("<Control-z>", lambda e: text.edit_undo())
text.bind("<Control-y>", lambda e: text.edit_redo())
text.bind("<KeyRelease>", refresh_outline)

# menu
menu = tk.Menu(root)
file_menu = tk.Menu(menu, tearoff=0)
file_menu.add_command(label="New", command=new_file)
file_menu.add_command(label="Open", command=open_file)
file_menu.add_command(label="Save", command=save_file)
menu.add_cascade(label="File", menu=file_menu)
root.config(menu=menu)

load_git_config()
root.mainloop()
