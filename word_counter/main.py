import sys
import tkinter as tk
from tkinter import ttk, messagebox


# =========================
# CONFIGURATION
# =========================

BG = "#1e1e1e"
PANEL = "#252526"
EDITOR_BG = "#181818"
BORDER = "#3c3c3c"
TEXT = "#d4d4d4"
MUTED = "#858585"
ACCENT = "#007acc"
GREEN = "#4ec9b0"
RED = "#f48771"
YELLOW = "#dcdcaa"

PRESETS = {
    "Essay": (191, 259),
    "Email": (91, 153),
}


# =========================
# MAIN WINDOW
# =========================

root = tk.Tk()
root.title("Word CoUnter v1")
root.geometry("850x650")
root.minsize(600, 480)
root.configure(bg=BG)

style = ttk.Style()
style.theme_use("clam")
style.configure(
    "TCombobox",
    fieldbackground=PANEL,
    background=PANEL,
    foreground=TEXT,
    arrowcolor=TEXT,
    bordercolor=BORDER,
    padding=5,
)
style.map(
    "TCombobox",
    fieldbackground=[("readonly", PANEL)],
    foreground=[("readonly", TEXT)],
    selectbackground=[("readonly", PANEL)],
    selectforeground=[("readonly", TEXT)],
)

# Статус-бар упаковываем ПЕРВЫМ, чтобы он никогда не обрезался
status_bar = tk.Frame(root, bg=ACCENT)
status_bar.pack(fill=tk.X, side=tk.BOTTOM)


# =========================
# HELPERS
# =========================

def safe_int(var, default):
    """Безопасно читает значение Spinbox (пустое/неверное поле не ломает код)."""
    try:
        return int(var.get())
    except (tk.TclError, ValueError):
        return default


def get_limits():
    mode = mode_var.get()
    if mode in PRESETS:
        return PRESETS[mode]
    return safe_int(min_var, 0), safe_int(max_var, 0)


def get_statistics():
    text = text_input.get("1.0", "end-1c")
    words = len(text.split())
    chars = len(text)
    paragraphs = sum(1 for line in text.splitlines() if line.strip())
    return words, chars, paragraphs


def update_statistics(event=None):
    word_count, char_count, paragraph_count = get_statistics()

    words_label.config(text=f"Words: {word_count}")
    chars_label.config(text=f"Characters: {char_count}")
    paragraphs_label.config(text=f"Paragraphs: {paragraph_count}")

    minimum, maximum = get_limits()

    if word_count == 0:
        status_label.config(text="Ready", fg="white")
    elif minimum <= word_count <= maximum:
        status_label.config(text="Within word limit", fg=GREEN)
    elif word_count < minimum:
        status_label.config(
            text=f"{minimum - word_count} more words needed", fg=YELLOW
        )
    else:
        status_label.config(
            text=f"{word_count - maximum} words over limit", fg=RED
        )


def update_statistics_later(event=None):
    # даём Tk сначала выполнить вставку/вырезание, потом считаем
    root.after_idle(update_statistics)


def update_limits(*args):
    mode = mode_var.get()
    if mode in PRESETS:
        minimum, maximum = PRESETS[mode]
        min_var.set(minimum)
        max_var.set(maximum)
        custom_frame.pack_forget()
    else:
        custom_frame.pack(side=tk.LEFT, padx=(12, 0))
    update_statistics()


# =========================
# CLIPBOARD (работает на любой раскладке)
# =========================

def do_paste(event=None):
    text_input.event_generate("<<Paste>>")
    update_statistics_later()
    return "break"


def do_copy(event=None):
    text_input.event_generate("<<Copy>>")
    return "break"


def do_cut(event=None):
    text_input.event_generate("<<Cut>>")
    update_statistics_later()
    return "break"


def select_all(event=None):
    text_input.tag_add("sel", "1.0", "end-1c")
    return "break"


# Коды физических клавиш (Windows): A=65, C=67, V=86, X=88
CTRL_KEYCODES = {
    65: select_all,
    67: do_copy,
    86: do_paste,
    88: do_cut,
}


def on_ctrl_key(event):
    if sys.platform.startswith("win"):
        handler = CTRL_KEYCODES.get(event.keycode)
        if handler:
            return handler()
    # на других ОС работают стандартные привязки Tk


def show_context_menu(event):
    try:
        context_menu.tk_popup(event.x_root, event.y_root)
    finally:
        context_menu.grab_release()


# =========================
# CHECK / CLEAR
# =========================

def check_text():
    try:
        text = text_input.get("1.0", "end-1c").strip()

        if not text:
            result_label.config(text="NO TEXT", fg=YELLOW)
            result_details.config(text="Paste or type your text first!")
            return

        minimum, maximum = get_limits()

        if minimum < 0 or maximum < minimum:
            result_label.config(text="INVALID LIMITS", fg=RED)
            result_details.config(
                text="Check your minimum and maximum word counts."
            )
            return

        word_count = len(text.split())

        if word_count < minimum:
            status, color = "TOO SHORT", YELLOW
            details = (
                f"Total words: {word_count}\n"
                f"Required: {minimum}-{maximum}\n"
                f"Add at least {minimum - word_count} words."
            )
        elif word_count > maximum:
            status, color = "TOO LONG", RED
            details = (
                f"Total words: {word_count}\n"
                f"Required: {minimum}-{maximum}\n"
                f"Remove at least {word_count - maximum} words."
            )
        else:
            status, color = "PASS", GREEN
            details = (
                f"Total words: {word_count}\n"
                "Nice work! Your text is within the word limit."
            )

        result_label.config(text=status, fg=color)
        result_details.config(text=details)
        update_statistics()

    except Exception as error:
        print("CHECK ERROR:", repr(error))
        result_label.config(text="ERROR", fg=RED)
        result_details.config(text=str(error))


def clear_text():
    if not text_input.get("1.0", "end-1c").strip():
        return

    if messagebox.askyesno(
        "Clear editor",
        "Are you sure you want to clear the text?",
        parent=root,
    ):
        text_input.delete("1.0", tk.END)
        result_label.config(text="Not checked", fg=MUTED)
        result_details.config(text="Your check results will appear here.")
        update_statistics()


# =========================
# HEADER
# =========================

header = tk.Frame(root, bg=BG)
header.pack(fill=tk.X, padx=20, pady=(16, 12))

tk.Label(
    header, text="WORD COUNTER",
    font=("Consolas", 19, "bold"), bg=BG, fg=TEXT
).pack(side=tk.LEFT)

tk.Label(
    header, text="ENGLISH WRITING",
    font=("Consolas", 9), bg=BG, fg=ACCENT
).pack(side=tk.RIGHT, pady=8)


# =========================
# SETTINGS BAR
# =========================

settings = tk.Frame(
    root, bg=PANEL, highlightbackground=BORDER, highlightthickness=1
)
settings.pack(fill=tk.X, padx=20, pady=(0, 12))

tk.Label(
    settings, text="MODE", bg=PANEL, fg=MUTED,
    font=("Consolas", 9, "bold")
).pack(side=tk.LEFT, padx=(12, 8), pady=10)

mode_var = tk.StringVar(value="Essay")

mode_box = ttk.Combobox(
    settings, textvariable=mode_var,
    values=["Essay", "Email", "Custom"],
    state="readonly", width=10
)
mode_box.pack(side=tk.LEFT, pady=8)

custom_frame = tk.Frame(settings, bg=PANEL)

tk.Label(custom_frame, text="Min:", bg=PANEL, fg=MUTED).pack(
    side=tk.LEFT, padx=(0, 4)
)
min_var = tk.IntVar(value=191)
tk.Spinbox(
    custom_frame, from_=0, to=100000, textvariable=min_var, width=6,
    bg=EDITOR_BG, fg=TEXT, insertbackground=TEXT,
    buttonbackground=PANEL, relief=tk.FLAT,
    command=update_statistics
).pack(side=tk.LEFT, padx=(0, 10))

tk.Label(custom_frame, text="Max:", bg=PANEL, fg=MUTED).pack(
    side=tk.LEFT, padx=(0, 4)
)
max_var = tk.IntVar(value=259)
tk.Spinbox(
    custom_frame, from_=0, to=100000, textvariable=max_var, width=6,
    bg=EDITOR_BG, fg=TEXT, insertbackground=TEXT,
    buttonbackground=PANEL, relief=tk.FLAT,
    command=update_statistics
).pack(side=tk.LEFT)

mode_box.bind("<<ComboboxSelected>>", update_limits)


# =========================
# EDITOR
# =========================

editor_header = tk.Frame(root, bg=BG)
editor_header.pack(fill=tk.X, padx=22)

tk.Label(
    editor_header, text="EDITOR", bg=BG, fg=MUTED,
    font=("Consolas", 9, "bold")
).pack(side=tk.LEFT)

editor_frame = tk.Frame(
    root, bg=EDITOR_BG, highlightbackground=BORDER, highlightthickness=1
)
editor_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(6, 12))

text_input = tk.Text(
    editor_frame, wrap=tk.WORD, font=("Consolas", 11),
    bg=EDITOR_BG, fg=TEXT, insertbackground=TEXT,
    selectbackground="#264f78", selectforeground="#ffffff",
    padx=14, pady=12, undo=True, maxundo=-1,
    relief=tk.FLAT, borderwidth=0
)

scrollbar = tk.Scrollbar(
    editor_frame, command=text_input.yview,
    bg=PANEL, troughcolor=EDITOR_BG
)
text_input.configure(yscrollcommand=scrollbar.set)

scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
text_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)


# =========================
# CONTEXT MENU + BINDINGS
# =========================

context_menu = tk.Menu(
    root, tearoff=0, bg=PANEL, fg=TEXT,
    activebackground=ACCENT, activeforeground="white"
)
context_menu.add_command(label="Cut", command=do_cut)
context_menu.add_command(label="Copy", command=do_copy)
context_menu.add_command(label="Paste", command=do_paste)
context_menu.add_separator()
context_menu.add_command(label="Select all", command=select_all)

text_input.bind("<Button-3>", show_context_menu)
text_input.bind("<Control-KeyPress>", on_ctrl_key)
text_input.bind("<KeyRelease>", update_statistics)
text_input.bind("<<Paste>>", update_statistics_later)
text_input.bind("<<Cut>>", update_statistics_later)


# =========================
# ACTION BUTTONS
# =========================

actions = tk.Frame(root, bg=BG)
actions.pack(fill=tk.X, padx=20, pady=(0, 12))

tk.Button(
    actions, text="  CHECK TEXT  ", command=check_text,
    bg=ACCENT, fg="white",
    activebackground="#1683c7", activeforeground="white",
    font=("Consolas", 10, "bold"), relief=tk.FLAT,
    cursor="hand2", padx=8, pady=9
).pack(side=tk.LEFT)

tk.Button(
    actions, text="Clear", command=clear_text,
    bg=PANEL, fg=TEXT,
    activebackground=BORDER, activeforeground=TEXT,
    font=("Consolas", 10), relief=tk.FLAT,
    cursor="hand2", padx=12, pady=9
).pack(side=tk.LEFT, padx=8)


# =========================
# RESULT PANEL
# =========================

result_frame = tk.Frame(
    root, bg=PANEL, highlightbackground=BORDER, highlightthickness=1
)
result_frame.pack(fill=tk.X, padx=20, pady=(0, 12))

result_label = tk.Label(
    result_frame, text="Not checked", bg=PANEL, fg=MUTED,
    font=("Consolas", 11, "bold")
)
result_label.pack(anchor=tk.W, padx=12, pady=(10, 2))

result_details = tk.Label(
    result_frame, text="Your check results will appear here.",
    bg=PANEL, fg=TEXT, font=("Consolas", 10),
    justify=tk.LEFT, anchor=tk.W
)
result_details.pack(anchor=tk.W, padx=12, pady=(0, 10))


# =========================
# STATUS BAR CONTENT
# =========================

status_label = tk.Label(
    status_bar, text="Ready", bg=ACCENT, fg="white",
    font=("Consolas", 9), anchor=tk.W
)
status_label.pack(side=tk.LEFT, padx=10, pady=5)

words_label = tk.Label(
    status_bar, text="Words: 0", bg=ACCENT, fg="white",
    font=("Consolas", 9)
)
words_label.pack(side=tk.RIGHT, padx=(8, 12), pady=5)

chars_label = tk.Label(
    status_bar, text="Characters: 0", bg=ACCENT, fg="white",
    font=("Consolas", 9)
)
chars_label.pack(side=tk.RIGHT, padx=8, pady=5)

paragraphs_label = tk.Label(
    status_bar, text="Paragraphs: 0", bg=ACCENT, fg="white",
    font=("Consolas", 9)
)
paragraphs_label.pack(side=tk.RIGHT, padx=8, pady=5)


# =========================
# START
# =========================

update_limits()
text_input.focus_set()
root.mainloop()