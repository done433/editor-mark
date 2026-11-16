
import tkinter as tk
from tkinter import filedialog
import subprocess
import threading
import os
from urllib.parse import urlparse, quote
import json

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
    refresh_history()

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
    refresh_history()

def merge_sections(content):
    lines = content.split("\n")
    preamble = []
    h1_order = []            
    h1_direct = {}          
    h1_sub_order = {}        
    h1_sub = {}              
    h1_raw = {}              
    sub_raw = {}             
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



def _set_status(msg):
    root.after(0, status_var.set, msg)

def _git(repo_dir, args):
    return subprocess.run(["git", "-C", repo_dir] + args,
                          capture_output=True, text=True, timeout=120)

def _reload_current():
    if not current_file or not os.path.exists(current_file):
        return
    with open(current_file, "r", encoding="utf-8") as f:
        data = f.read()
    def apply():
        text.delete("1.0", tk.END)
        text.insert("1.0", data)
        refresh_outline()
    root.after(0, apply)

def _is_repo(repo_dir):
    r = _git(repo_dir, ["rev-parse", "--is-inside-work-tree"])
    return r.returncode == 0 and r.stdout.strip() == "true"

def _branch(repo_dir):
    b = _git(repo_dir, ["symbolic-ref", "--short", "-q", "HEAD"]).stdout.strip()
    return b or "main"



def _clone_into(parent_dir, auth_url, clean_url):
    # repo name from url, cloned into a fresh subfolder
    name = clean_url.rstrip("/").split("/")[-1]
    if name.endswith(".git"):
        name = name[:-4]
    dest = os.path.join(parent_dir, name or "repo")
    n = dest
    i = 1
    while os.path.exists(n):            # don't collide with existing path
        n = dest + "-" + str(i)
        i += 1
    dest = n
    r = _git(parent_dir, ["clone", auth_url, dest])
    if r.returncode != 0:
        return None, "clone fail: " + r.stderr.strip()[:80]
    # strip token from stored remote
    _git(dest, ["remote", "set-url", "origin", clean_url])
    return dest, "cloned into " + os.path.basename(dest)


def _git_ctx():
    global current_file
    token = token_entry.get().strip()
    repo_url = repo_entry.get().strip()
    if not token or not repo_url:
        _set_status("need token + url")
        return None
    save_git_config()
    p = urlparse(repo_url)
    auth_url = f"{p.scheme}://{quote(token, safe='')}@{p.netloc}{p.path}"

    # no file open -> clone into chosen folder, then open a file from it
    if not current_file:
        parent = filedialog.askdirectory(title="Where to clone the repo")
        if not parent:
            _set_status("cancelled")
            return None
        dest, msg = _clone_into(parent, auth_url, repo_url)
        _set_status(msg)
        if not dest:
            return None
        refresh_history()
        # auto-open first text-like file in the clone, if any
        for fn in sorted(os.listdir(dest)):
            full = os.path.join(dest, fn)
            if os.path.isfile(full):
                current_file = full
                with open(full, "r", encoding="utf-8", errors="replace") as f:
                    text.delete("1.0", tk.END)
                    text.insert("1.0", f.read())
                root.title(full)
                refresh_outline()
                refresh_history()
                break
        return auth_url, dest

    repo_dir = os.path.dirname(os.path.abspath(current_file))
    if not _is_repo(repo_dir):
        dest, msg = _clone_into(repo_dir, auth_url, repo_url)
        _set_status(msg)
        if not dest:
            return None
        base = os.path.basename(current_file)
        cand = os.path.join(dest, base)
        if os.path.exists(cand):
            current_file = cand
            root.title(current_file)
            _reload_current()
            refresh_history()
        repo_dir = dest
    return auth_url, repo_dir





def git_pull():
    ctx = _git_ctx()
    if not ctx:
        return
    auth_url, repo_dir = ctx
    _set_status("pulling...")
    def run():
        br = _branch(repo_dir)
        f = _git(repo_dir, ["fetch", auth_url, br])
        if f.returncode != 0:
            _set_status("fetch fail: " + f.stderr.strip())
            return
        m = _git(repo_dir, ["merge", "--no-edit", "FETCH_HEAD"])
        if m.returncode != 0:
            bad = _git(repo_dir, ["diff", "--name-only", "--diff-filter=U"]).stdout.strip()
            _git(repo_dir, ["merge", "--abort"])
            _set_status("conflict: " + bad.replace("\n", ", ")[:80])
            return
        _reload_current()
        refresh_history()
        _set_status("pulled " + br)
    threading.Thread(target=run, daemon=True).start()

def git_push():
    ctx = _git_ctx()
    if not ctx:
        return
    auth_url, repo_dir = ctx
    _set_status("pushing...")
    def run():
        br = _branch(repo_dir)
        _git(repo_dir, ["add", "-A"])
        staged = _git(repo_dir, ["diff", "--cached", "--name-only"]).stdout.strip()
        if staged:
            c = _git(repo_dir, ["commit", "-m", "auto"])
            if c.returncode != 0:
                _set_status("commit fail: " + (c.stderr or c.stdout).strip())
                return
        p = _git(repo_dir, ["push", auth_url, f"HEAD:refs/heads/{br}"])
        if p.returncode != 0:
            _set_status("rejected, pull first: " + p.stderr.strip()[:70])
            return
        refresh_history()
        _set_status("pushed " + br + ("" if staged else " (nothing new)"))
    threading.Thread(target=run, daemon=True).start()


history_hashes = []

def _file_repo():
    if not current_file:
        return None, None
    d = os.path.dirname(os.path.abspath(current_file))
    r = _git(d, ["rev-parse", "--show-toplevel"])
    if r.returncode != 0:
        return None, None
    top = r.stdout.strip()
    rel = os.path.relpath(os.path.abspath(current_file), top)
    return top, rel

def refresh_history(event=None):
    global history_hashes
    history_hashes = []
    history.delete(0, tk.END)
    top, rel = _file_repo()
    if not top:
        history.insert(tk.END, "no git")
        return
    r = _git(top, ["log", "--format=%h%x09%ad%x09%s", "--date=short", "--", rel])
    if r.returncode != 0 or not r.stdout.strip():
        history.insert(tk.END, "no history")
        return
    history.insert(tk.END, "● current")          # live file
    history_hashes.append(None)
    for ln in r.stdout.splitlines():
        parts = ln.split("\t", 2)
        if len(parts) < 2:
            continue
        h, date = parts[0], parts[1]
        msg = parts[2] if len(parts) > 2 else ""
        history_hashes.append(h)
        history.insert(tk.END, f"{date} {h} {msg[:15]}")

def show_version(event=None):
    sel = history.curselection()
    if not sel:
        return
    idx = sel[0]
    h = history_hashes[idx]
    if h is None:                                 # "current" -> reload live file
        _reload_current()
        root.title(current_file)
        _set_status("current")
        return
    top, rel = _file_repo()
    if not top:
        return
    r = _git(top, ["show", f"{h}:{rel}"])
    if r.returncode != 0:
        _set_status("show fail: " + r.stderr.strip())
        return
    text.delete("1.0", tk.END)
    text.insert("1.0", r.stdout)
    refresh_outline()
    root.title(f"[{h}] {current_file}  (old version — Save overwrites!)")
    _set_status("viewing " + h)


def do_edit(action):
    try:
        if action == "undo":
            text.edit_undo()
        else:
            text.edit_redo()
    except tk.TclError:
        pass
    refresh_outline()
    update_edit_buttons()

def update_edit_buttons(event=None):
    # canundo/canredo tell us if stack has anything
    can_undo = bool(text.edit("canundo"))
    can_redo = bool(text.edit("canredo"))
    btn_undo.config(state="normal" if can_undo else "disabled")
    btn_redo.config(state="normal" if can_redo else "disabled")


# --- יצירת החלון הראשי ---
root = tk.Tk()
root.title("My Text Editor")
root.geometry("900x600")

# 1. סרגל כפתורי קבצים עליון (מופיע ראשון)
top_toolbar = tk.Frame(root, bg="#1e1e1e")
top_toolbar.pack(side="top", fill="x", padx=5, pady=5)

btn_new = tk.Button(
    top_toolbar, text="New", command=new_file,
    bg="#2a2a2a", fg="#d4d4d4", bd=0, padx=10, pady=4, relief=tk.FLAT,
    activebackground="#3c3c3c", activeforeground="#ffffff"
)
btn_new.pack(side="left", padx=2)

btn_open = tk.Button(
    top_toolbar, text="Open", command=open_file,
    bg="#2a2a2a", fg="#d4d4d4", bd=0, padx=10, pady=4, relief=tk.FLAT,
    activebackground="#3c3c3c", activeforeground="#ffffff"
)
btn_open.pack(side="left", padx=2)

btn_save = tk.Button(
    top_toolbar, text="Save", command=save_file,
    bg="#2a2a2a", fg="#d4d4d4", bd=0, padx=10, pady=4, relief=tk.FLAT,
    activebackground="#3c3c3c", activeforeground="#ffffff"
)
btn_save.pack(side="left", padx=2)



btn_redo = tk.Button(
    top_toolbar, text="↷ Redo", command=lambda: do_edit("redo"),
    bg="#2a2a2a", fg="#d4d4d4", bd=0, padx=10, pady=4, relief=tk.FLAT,
    activebackground="#3c3c3c", activeforeground="#ffffff",
    disabledforeground="#555555"
)
btn_redo.pack(side="right", padx=2)

btn_undo = tk.Button(
    top_toolbar, text="↶ Undo", command=lambda: do_edit("undo"),
    bg="#2a2a2a", fg="#d4d4d4", bd=0, padx=10, pady=4, relief=tk.FLAT,
    activebackground="#3c3c3c", activeforeground="#ffffff",
    disabledforeground="#555555"
)
btn_undo.pack(side="right", padx=2)









# 2. סרגל ה־Git התחתון
git_bar = tk.Frame(root, bg="#1e1e1e")
git_bar.pack(side="bottom", fill="x")

tk.Label(git_bar, text="token", bg="#1e1e1e", fg="#d4d4d4").pack(side="left")
token_entry = tk.Entry(git_bar, show="*", width=20, bg="#2a2a2a", fg="#d4d4d4", insertbackground="#d4d4d4")
token_entry.pack(side="left", padx=4)

tk.Label(git_bar, text="repo", bg="#1e1e1e", fg="#d4d4d4").pack(side="left")
repo_entry = tk.Entry(git_bar, width=40, bg="#2a2a2a", fg="#d4d4d4", insertbackground="#d4d4d4")
repo_entry.pack(side="left", padx=4)

status_var = tk.StringVar(value="")
tk.Button(git_bar, text="Pull", command=git_pull).pack(side="left", padx=4)
tk.Button(git_bar, text="Push", command=git_push).pack(side="left", padx=4)
status_entry = tk.Entry(git_bar, textvariable=status_var, state="readonly",
                        width=60, bd=0, readonlybackground="#1e1e1e", fg="#9cdcfe",
                        font=("Consolas", 10))
status_entry.pack(side="left", fill="x", expand=True, padx=4)

# 3. אזור התוכן המרכזי (Outline + Text) - מופיע אחרון ותופס את שאר השטח
paned = tk.PanedWindow(root, orient="horizontal", sashwidth=5,
                       bg="#3c3c3c", opaqueresize=False)
paned.pack(expand=True, fill="both")

outline = tk.Listbox(paned, font=("Consolas", 12), activestyle="none",
                     bg="#1e1e1e", fg="#d4d4d4", borderwidth=0)
text = tk.Text(paned, font=("Consolas", 14), undo=True, wrap="word",
               bg="#1e1e1e", fg="#d4d4d4", insertbackground="#d4d4d4")
history = tk.Listbox(paned, font=("Consolas", 10), activestyle="none",
                     bg="#1e1e1e", fg="#d4d4d4", borderwidth=0)

paned.add(outline, minsize=120, width=160, stretch="never")
paned.add(text, minsize=200, stretch="always")
paned.add(history, minsize=120, width=200, stretch="never")

history.bind("<<ListboxSelect>>", show_version)



def find_text(event=None):
    find_bar.pack(side="top", fill="x", before=paned)
    find_entry.focus_set()
    find_entry.select_range(0, tk.END)
    return "break"

def do_search(event=None, forward=True):
    text.tag_remove("search", "1.0", tk.END)
    q = find_entry.get()
    if not q:
        return "break"
    start = text.index("insert")
    idx = text.search(q, start if forward else start + f"-{len(q)}c",
                      nocase=True, stopindex=tk.END if forward else "1.0",
                      backwards=not forward)
    if not idx:                                   # wrap around
        idx = text.search(q, "1.0" if forward else tk.END,
                          nocase=True, backwards=not forward)
    if idx:
        end = f"{idx}+{len(q)}c"
        text.tag_add("search", idx, end)
        text.tag_config("search", background="#515c6a", foreground="#ffffff")
        text.mark_set("insert", end if forward else idx)
        text.see(idx)
    return "break"

def close_find(event=None):
    text.tag_remove("search", "1.0", tk.END)
    find_bar.pack_forget()
    text.focus_set()
    return "break"

find_bar = tk.Frame(root, bg="#2a2a2a")
tk.Label(find_bar, text="find", bg="#2a2a2a", fg="#d4d4d4").pack(side="left", padx=4)
find_entry = tk.Entry(find_bar, width=30, bg="#1e1e1e", fg="#d4d4d4",
                      insertbackground="#d4d4d4")
find_entry.pack(side="left", padx=4, pady=3)
find_entry.bind("<Return>", lambda e: do_search(forward=True))
find_entry.bind("<Shift-Return>", lambda e: do_search(forward=False))
find_entry.bind("<Escape>", close_find)

text.bind("<<Modified>>", lambda e: (update_edit_buttons(), text.edit_modified(False)))




outline.bind("<<ListboxSelect>>", jump_to_heading)
text.bind("<Control-z>", lambda e: (do_edit("undo"), "break"))
text.bind("<Control-y>", lambda e: (do_edit("redo"), "break"))
text.bind("<Control-s>", lambda e: (save_file(), "break"))
text.bind("<Control-f>", find_text)
root.bind("<Control-f>", find_text)
text.bind("<KeyRelease>", refresh_outline)

load_git_config()
update_edit_buttons()
root.mainloop()



