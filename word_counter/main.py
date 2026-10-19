import sys
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from collections import Counter


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
root.title("Word CoUnter v1.2")
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


root.option_add("*TCombobox*Listbox.background", PANEL)
root.option_add("*TCombobox*Listbox.foreground", TEXT)
root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
root.option_add("*TCombobox*Listbox.selectForeground", "white")


# =========================
# HELPERS
# =========================

def safe_int(var):
    try:
        return int(var.get())
    except (tk.TclError, ValueError):
        return None


def only_digits(proposed):
    # разрешаем пустую строку (пока человек стирает/печатает) и только цифры до 6 знаков
    return proposed == "" or (proposed.isdigit() and len(proposed) <= 6)


vcmd = (root.register(only_digits), "%P")


def get_limits():
    mode = mode_var.get()
    if mode in PRESETS:
        return PRESETS[mode]

    minimum = safe_int(min_var)
    maximum = safe_int(max_var)

    if minimum is None or maximum is None or minimum > maximum:
        return None
    return minimum, maximum


def count_words(text):
    # слово = кусок текста между пробелами, в котором есть хотя бы одна буква или цифра
    return sum(1 for token in text.split() if any(ch.isalnum() for ch in token))

ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc",
    "e.g", "i.e", "no", "inc", "ltd", "co", "u.s", "a.m", "p.m",
}

# конец предложения: .!? (можно несколько подряд, плюс закрывающая кавычка/скобка) и пробел
SENTENCE_END = re.compile(r'([.!?]+["\')\]]*)\s+')


def split_sentences(text):
    sentences = []

    # перенос строки всегда завершает предложение (заголовки, списки, абзацы)
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        start = 0
        for match in SENTENCE_END.finditer(line):
            rest = line[match.end():]
            if not rest:
                break

            # после точки идёт строчная буква: предложение продолжается
            if rest[0].islower():
                continue

            # одиночная точка после сокращения (Mr. Dr. e.g.) или инициала (J. Smith)
            if match.group(1) == ".":
                chunk = line[start:match.start(1)]
                if chunk.split():
                    last = chunk.split()[-1].strip("\"'([").lower()
                    if last in ABBREVIATIONS:
                        continue
                    if len(last) == 1 and last.isalpha() and last not in ("i", "a"):
                        continue

            sentences.append(line[start:match.end(1)])
            start = match.end()

        sentences.append(line[start:])

    # выкидываем «предложения» без единой буквы или цифры
    return [s for s in sentences if count_words(s) > 0]


def sentence_stats(text):
    sentences = split_sentences(text)
    if not sentences:
        return 0, 0.0, 0

    lengths = [count_words(s) for s in sentences]
    return len(sentences), sum(lengths) / len(lengths), max(lengths)


def count_syllables(word):
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 0
    if len(word) <= 3:
        return 1
    # тихие окончания: -es, -ed, -e
    word = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", word)
    word = re.sub(r"^y", "", word)
    return max(1, len(re.findall(r"[aeiouy]{1,2}", word)))


def readability_label(score):
    if score >= 90: return "Very easy"
    if score >= 80: return "Easy"
    if score >= 70: return "Fairly easy"
    if score >= 60: return "Standard"
    if score >= 50: return "Fairly difficult"
    if score >= 30: return "Difficult"
    return "Very difficult"


def readability(text):
    """Возвращает (score, grade, label) или None, если считать нечего."""
    # формула рассчитана на английский: без латиницы цифра бессмысленна
    if not re.search(r"[A-Za-z]", text):
        return None

    sentences = split_sentences(text)
    words = [t for t in text.split() if any(ch.isalnum() for ch in t)]
    if not sentences or not words:
        return None

    syllables = sum(max(1, count_syllables(w)) for w in words)
    words_per_sentence = len(words) / len(sentences)
    syllables_per_word = syllables / len(words)

    score = 206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word
    grade = 0.39 * words_per_sentence + 11.8 * syllables_per_word - 15.59

    score = max(0, min(100, score))
    grade = max(0, grade)
    return score, grade, readability_label(score)


STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "any", "can",
    "had", "her", "was", "one", "our", "out", "has", "his", "how", "its",
    "who", "did", "get", "she", "him", "that", "this", "with", "have",
    "from", "they", "will", "would", "there", "their", "what", "about",
    "which", "when", "your", "than", "them", "then", "were", "been",
    "into", "also", "just", "more", "some", "such", "only", "very",
}
# "very" в списке нет намеренно: повторы "very" как раз нужно ловить
STOPWORDS.discard("very")


def format_time(seconds):
    seconds = round(seconds)
    if seconds < 60:
        return f"{seconds} sec"
    return f"{seconds // 60} min {seconds % 60} s"


def writing_stats(text):
    """Возвращает словарь с показателями или None, если слов нет."""
    tokens = [re.sub(r"^\W+|\W+$", "", t).lower() for t in text.split()]
    tokens = [t for t in tokens if any(ch.isalnum() for ch in t)]
    if not tokens:
        return None

    total = len(tokens)
    unique = len(set(tokens))
    counts = Counter(t for t in tokens if len(t) >= 3 and t not in STOPWORDS)

    return {
        "unique": unique,
        "unique_pct": unique / total * 100,
        "avg_word": sum(len(t) for t in tokens) / total,
        "read": format_time(total / 200 * 60),
        "speak": format_time(total / 130 * 60),
        "repeats": [(w, c) for w, c in counts.most_common(3) if c >= 2],
    }


def get_statistics():
    text = text_input.get("1.0", "end-1c")
    words = count_words(text)
    chars = len(text)
    paragraphs = sum(1 for line in text.splitlines() if line.strip())
    return words, chars, paragraphs


def update_verdict(word_count):
    limits = get_limits()

    if limits is None:
        result_details.config(
            text="Min and Max must be numbers, and Min can't be bigger than Max."
        )
        return

    minimum, maximum = limits
    progress = f"{word_count} / {minimum}–{maximum} words"

    if word_count == 0:
        result_label.config(text="NO TEXT", fg=MUTED)
        result_details.config(text=progress)
    elif word_count < minimum:
        percent = word_count / minimum * 100
        result_label.config(text="TOO SHORT", fg=YELLOW)
        result_details.config(
            text=f"{progress} ({percent:.0f}%)  -  add at least {minimum - word_count} words"
        )
    elif word_count > maximum:
        result_label.config(text="TOO LONG", fg=RED)
        result_details.config(
            text=f"{progress}  -  remove at least {word_count - maximum} words"
        )
    else:
        result_label.config(text="PASS", fg=GREEN)
        result_details.config(text=f"{progress}  -  within the limit")


def update_statistics(event=None):
    word_count, char_count, paragraph_count = get_statistics()

    if stats_visible:
        text = text_input.get("1.0", "end-1c")
        sentence_count, avg_len, longest = sentence_stats(text)
        update_stats_panel(
            word_count, char_count, paragraph_count,
            sentence_count, avg_len, longest,
            readability(text),
            writing_stats(text)
        )

    update_verdict(word_count)


def update_statistics_later(event=None):
    # даём Tk сначала выполнить вставку/вырезание, потом считаем
    root.after_idle(update_statistics)


def update_limits(*args):
    mode = mode_var.get()
    if mode in PRESETS:
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


def do_undo(event=None):
    try:
        text_input.edit_undo()
    except tk.TclError:
        pass  # нечего отменять
    update_statistics_later()
    return "break"


def do_redo(event=None):
    try:
        text_input.edit_redo()
    except tk.TclError:
        pass  # нечего повторять
    update_statistics_later()
    return "break"


def select_all(event=None):
    text_input.tag_add("sel", "1.0", "end-1c")
    return "break"

def show_context_menu(event):
    try:
        context_menu.tk_popup(event.x_root, event.y_root)
    finally:
        context_menu.grab_release()

# =========================
# FILE HANDLING
# =========================

current_file = None


def is_dirty():
    return text_input.edit_modified()


def update_title():
    name = current_file.split("/")[-1].split("\\")[-1] if current_file else "Untitled"
    mark = "*" if is_dirty() else ""
    root.title(f"{mark}{name} - Word CoUnter v1.2")


def on_modified(event=None):
    update_title()


def confirm_discard():
    """True = можно продолжать, False = пользователь нажал Cancel (или сохранение не удалось)."""
    if not is_dirty():
        return True

    answer = messagebox.askyesnocancel(
        "Unsaved changes",
        "Save changes before continuing?",
        parent=root,
    )

    if answer is None:      # Cancel
        return False
    if answer:              # Yes, сохраняем
        save_file()
        return not is_dirty()   # если сохранение отменили или оно упало, остаёмся
    return True             # No, продолжаем без сохранения


def open_file(event=None):
    global current_file

    if not confirm_discard():
        return "break"

    path = filedialog.askopenfilename(
        parent=root,
        title="Open text file",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
    )
    if not path:
        return "break"

    try:
        with open(path, "rb") as f:
            raw = f.read()

        try:
            content = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            content = raw.decode("cp1251")

    except OSError as error:
        messagebox.showerror("Open failed", str(error), parent=root)
        return "break"

    text_input.delete("1.0", tk.END)
    text_input.insert("1.0", content)
    text_input.edit_reset()
    text_input.edit_modified(False)   # свежеоткрытый файл не «изменён»

    current_file = path
    update_title()
    update_statistics()
    return "break"

def save_file_as(event=None):
    global current_file

    path = filedialog.asksaveasfilename(
        parent=root,
        title="Save text file",
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
    )
    if not path:
        return "break"

    if write_file(path):
        current_file = path
        update_title()
    return "break"


def save_file(event=None):
    if current_file is None:
        return save_file_as()

    write_file(current_file)
    return "break"


def write_file(path):
    try:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text_input.get("1.0", "end-1c"))
        text_input.edit_modified(False)
        update_title()
        return True
    except OSError as error:
        messagebox.showerror("Save failed", str(error), parent=root)
        return False

# A=65, C=67, O=79, S=83, V=86, X=88, Y=89, Z=90
CTRL_KEYCODES = {
    65: select_all,
    67: do_copy,
    79: open_file,
    83: save_file,
    86: do_paste,
    88: do_cut,
    89: do_redo,
    90: do_undo,
}


def on_ctrl_key(event):
    if sys.platform.startswith("win"):
        # Ctrl+Shift+Z = Redo (флаг Shift = 0x1)
        if event.keycode == 90 and event.state & 0x1:
            return do_redo()

        handler = CTRL_KEYCODES.get(event.keycode)
        if handler:
            return handler()

# =========================
# CHECK / CLEAR
# =========================


def clear_text():
    global current_file

    if not text_input.get("1.0", "end-1c").strip():
        return

    if is_dirty():
        if not confirm_discard():
            return
    elif not messagebox.askyesno(
        "Clear editor",
        "Are you sure you want to clear the text?",
        parent=root,
    ):
        return

    text_input.delete("1.0", tk.END)
    text_input.edit_modified(False)
    current_file = None
    update_title()
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
min_spin = tk.Spinbox(
    custom_frame, from_=0, to=100000, textvariable=min_var, width=6,
    bg=EDITOR_BG, fg=TEXT, insertbackground=TEXT,
    buttonbackground=PANEL, relief=tk.FLAT,
    validate="key", validatecommand=vcmd,
    command=update_statistics
)
min_spin.pack(side=tk.LEFT, padx=(0, 10))
min_spin.bind("<KeyRelease>", update_statistics)

tk.Label(custom_frame, text="Max:", bg=PANEL, fg=MUTED).pack(
    side=tk.LEFT, padx=(0, 4)
)
max_var = tk.IntVar(value=259)
max_spin = tk.Spinbox(
    custom_frame, from_=0, to=100000, textvariable=max_var, width=6,
    bg=EDITOR_BG, fg=TEXT, insertbackground=TEXT,
    buttonbackground=PANEL, relief=tk.FLAT,
    validate="key", validatecommand=vcmd,
    command=update_statistics
)
max_spin.pack(side=tk.LEFT)
max_spin.bind("<KeyRelease>", update_statistics)

mode_box.bind("<<ComboboxSelected>>", update_limits)


# =========================
# EDITOR
# =========================

# строка, в которой лежат редактор и (по желанию) панель Stats
editor_row = tk.Frame(root, bg=BG)
editor_row.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 12))

editor_frame = tk.Frame(
    editor_row, bg=EDITOR_BG, highlightbackground=BORDER, highlightthickness=1
)
editor_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

text_input = tk.Text(
    editor_frame, wrap=tk.WORD, font=("Consolas", 11),
    height=8,
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
# STATS PANEL
# =========================

STATS_W = 230
stats_visible = False

stats_panel = tk.Frame(
    editor_row, bg=PANEL,
    highlightbackground=BORDER, highlightthickness=1
)
# распорка задаёт ширину, а высота теперь считается по содержимому
tk.Frame(stats_panel, width=STATS_W, height=1, bg=PANEL).pack()

tk.Label(
    stats_panel, text="STATS", bg=PANEL, fg=MUTED,
    font=("Consolas", 9, "bold")
).pack(anchor=tk.W, padx=12, pady=(10, 6))


stat_values = {}
stat_names = {}


def add_stat(label, key):
    row = tk.Frame(stats_panel, bg=PANEL)
    row.pack(fill=tk.X, padx=12, pady=2)
    name = tk.Label(
        row, text=label, bg=PANEL, fg=MUTED, font=("Consolas", 9)
    )
    name.pack(side=tk.LEFT)
    value = tk.Label(
        row, text="0", bg=PANEL, fg=TEXT, font=("Consolas", 10, "bold")
    )
    value.pack(side=tk.RIGHT)
    stat_values[key] = value
    stat_names[key] = name


add_stat("Words", "words")
add_stat("Characters", "chars")
add_stat("Paragraphs", "paragraphs")
add_stat("Sentences", "sentences")
add_stat("Avg sentence", "avg")
add_stat("Longest sentence", "longest")
add_stat("Readability", "readability")
add_stat("Level", "level")
add_stat("Grade", "grade")
add_stat("Unique words", "unique")
add_stat("Avg word", "avg_word")
add_stat("Read time", "read")
add_stat("Speak time", "speak")


tk.Label(
    stats_panel, text="TOP REPEATS", bg=PANEL, fg=MUTED,
    font=("Consolas", 9, "bold")
).pack(anchor=tk.W, padx=12, pady=(8, 2))

add_stat("-", "rep1")
add_stat("-", "rep2")
add_stat("-", "rep3")


def update_stats_panel(words, chars, paragraphs, sentences, avg, longest, read, extra):
    stat_values["words"].config(text=str(words))
    stat_values["chars"].config(text=str(chars))
    stat_values["paragraphs"].config(text=str(paragraphs))
    stat_values["sentences"].config(text=str(sentences))
    stat_values["avg"].config(text=f"{avg:.1f} w" if sentences else "-")
    stat_values["longest"].config(text=f"{longest} w" if sentences else "-")

    if read:
        score, grade, label = read
        stat_values["readability"].config(text=f"{score:.0f}")
        stat_values["level"].config(text=label)
        stat_values["grade"].config(text=f"{grade:.1f}")
    else:
        for key in ("readability", "level", "grade"):
            stat_values[key].config(text="-")

    if extra:
        stat_values["unique"].config(
            text=f"{extra['unique']} ({extra['unique_pct']:.0f}%)"
        )
        stat_values["avg_word"].config(text=f"{extra['avg_word']:.1f} ch")
        stat_values["read"].config(text=f"~{extra['read']}")
        stat_values["speak"].config(text=f"~{extra['speak']}")
        repeats = extra["repeats"]
    else:
        for key in ("unique", "avg_word", "read", "speak"):
            stat_values[key].config(text="-")
        repeats = []

    for i in range(3):
        key = f"rep{i + 1}"
        if i < len(repeats):
            word, count = repeats[i]
            stat_names[key].config(text=word)
            stat_values[key].config(text=f"x{count}")
        else:
            stat_names[key].config(text="-")
            stat_values[key].config(text="")

    if read:
        score, grade, label = read
        stat_values["readability"].config(text=f"{score:.0f}")
        stat_values["level"].config(text=label)
        stat_values["grade"].config(text=f"{grade:.1f}")
    else:
        for key in ("readability", "level", "grade"):
            stat_values[key].config(text="-")


def toggle_stats():
    global stats_visible
    stats_visible = not stats_visible

    root.update_idletasks()
    width, height = root.winfo_width(), root.winfo_height()
    extra = STATS_W + 10
    screen_w = root.winfo_screenwidth()

    if stats_visible:
        stats_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0), before=editor_frame)
        update_statistics()
        root.update_idletasks()
        screen_h = root.winfo_screenheight()
        need_h = min(root.winfo_reqheight(), screen_h - 100)
        root.minsize(root.winfo_reqwidth(), need_h)
        if root.state() == "normal":
            root.geometry(f"{min(width + extra, screen_w - 40)}x{max(height, need_h)}")
    else:
        stats_panel.pack_forget()
        root.update_idletasks()
        root.minsize(root.winfo_reqwidth(), root.winfo_reqheight())
        if root.state() == "normal":
            root.geometry(f"{max(width - extra, 1)}x{height}")


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
text_input.bind("<<Modified>>", on_modified)
text_input.bind("<FocusIn>", lambda e: editor_frame.config(highlightbackground=ACCENT))
text_input.bind("<FocusOut>", lambda e: editor_frame.config(highlightbackground=BORDER))


# =========================
# ACTION BUTTONS
# =========================

def make_button(parent, text, command, primary=False):
    normal = ACCENT if primary else PANEL
    hover = "#1683c7" if primary else BORDER
    fg = "white" if primary else TEXT

    btn = tk.Button(
        parent, text=text, command=command,
        bg=normal, fg=fg,
        activebackground=hover, activeforeground=fg,
        font=("Consolas", 10, "bold" if primary else "normal"),
        relief=tk.FLAT, bd=0, cursor="hand2",
        padx=14 if primary else 12, pady=9
    )
    btn.bind("<Enter>", lambda e: btn.config(bg=hover))
    btn.bind("<Leave>", lambda e: btn.config(bg=normal))
    return btn


actions = tk.Frame(root, bg=BG)
actions.pack(fill=tk.X, padx=20, pady=(0, 12))

make_button(actions, "Clear", clear_text).pack(side=tk.LEFT)
make_button(actions, "Stats", toggle_stats).pack(side=tk.LEFT, padx=8)

# справа налево: Save As, Save, Open
make_button(actions, "Save As", save_file_as).pack(side=tk.RIGHT)
make_button(actions, "Save", save_file).pack(side=tk.RIGHT, padx=8)
make_button(actions, "Open", open_file).pack(side=tk.RIGHT)


# =========================
# RESULT PANEL (live verdict)
# =========================

result_frame = tk.Frame(
    root, bg=PANEL, highlightbackground=BORDER, highlightthickness=1
)
result_frame.pack(fill=tk.X, padx=20, pady=(0, 12))

result_label = tk.Label(
    result_frame, text="NO TEXT", bg=PANEL, fg=MUTED,
    font=("Consolas", 14, "bold")
)
result_label.pack(anchor=tk.W, padx=12, pady=(10, 2))

result_details = tk.Label(
    result_frame, text="", bg=PANEL, fg=TEXT,
    font=("Consolas", 10), justify=tk.LEFT, anchor=tk.W
)
result_details.pack(anchor=tk.W, padx=12, pady=(0, 10))


# =========================
# START
# =========================

update_limits()
update_title()
text_input.focus_set()
def on_close():
    if confirm_discard():
        root.destroy()


root.protocol("WM_DELETE_WINDOW", on_close)

def fit_window():
    root.update_idletasks()

    # сколько места реально нужно содержимому
    need_w = root.winfo_reqwidth()
    need_h = root.winfo_reqheight()

    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()

    # желаемый размер, но не больше экрана (с запасом под панель задач)
    width = min(max(850, need_w), screen_w - 40)
    height = min(max(650, need_h), screen_h - 100)

    # по центру экрана
    x = (screen_w - width) // 2
    y = max((screen_h - height) // 2 - 20, 0)

    root.geometry(f"{width}x{height}+{x}+{y}")
    root.minsize(min(need_w, screen_w - 40), min(need_h, screen_h - 100))


fit_window()

root.mainloop()