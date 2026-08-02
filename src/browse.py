#!/usr/bin/env python3
"""Full-screen curses browser for the notes directory.

Imported lazily by note.py so `curses` is only loaded when actually browsing.
"""
import curses
import os
import time

HEADER_ROWS = 2  # path + separator
FOOTER_ROWS = 2  # separator + key hints
KEYS = "↵ open  n new  d dir  r rename  x del  q quit"

ESCAPE = 27
ENTER = (10, 13, curses.KEY_ENTER)
BACKSPACE = (curses.KEY_BACKSPACE, 127, 8)


def ago(seconds):
    """Human-readable age, e.g. '2h ago'."""
    for size, unit in ((60, "s"), (60, "m"), (24, "h"), (7, "d"), (52, "w")):
        if seconds < size:
            return f"{int(seconds)}{unit} ago"
        seconds /= size
    return f"{int(seconds)}y ago"


def entries(directory):
    """Directories then notes, each sorted by name, with '..' first if nested."""
    dirs, files = [], []
    for name in sorted(os.listdir(directory)):
        if name.startswith("."):
            continue
        (dirs if os.path.isdir(os.path.join(directory, name)) else files).append(name)
    return dirs + files


def valid_name(name):
    """Reject anything that would escape the current directory."""
    return name not in ("", ".", "..") and "/" not in name and os.sep not in name


class Browser:
    def __init__(self, stdscr, root, editor):
        self.stdscr = stdscr
        self.root = root
        self.editor = editor
        self.cwd = root
        self.index = 0
        self.offset = 0
        self.status = ""
        self.items = []

    # --- drawing -----------------------------------------------------------

    @property
    def rows(self):
        """Number of list rows that fit on screen."""
        return max(1, self.stdscr.getmaxyx()[0] - HEADER_ROWS - FOOTER_ROWS)

    def refresh_items(self):
        self.items = entries(self.cwd)
        if self.cwd != self.root:
            self.items.insert(0, "..")
        self.index = max(0, min(self.index, len(self.items) - 1))
        self.scroll()

    def scroll(self):
        """Keep the selection inside the visible window."""
        self.offset = min(self.offset, self.index)
        self.offset = max(self.offset, self.index - self.rows + 1)
        self.offset = max(0, min(self.offset, max(0, len(self.items) - self.rows)))

    def draw(self):
        self.stdscr.erase()
        height, width = self.stdscr.getmaxyx()
        rel = os.path.relpath(self.cwd, self.root)
        self.write(0, f"  ~/.dbterminal/notes{'' if rel == '.' else '/' + rel}",
                   curses.A_BOLD)
        self.write(1, " " + "─" * max(0, width - 2))

        if not self.items:
            self.write(HEADER_ROWS, "   (empty — press n for a new note)",
                       curses.A_DIM)
        for row in range(min(self.rows, len(self.items) - self.offset)):
            self.draw_entry(HEADER_ROWS + row, self.items[self.offset + row],
                            self.offset + row == self.index)

        self.write(height - 2, " " + "─" * max(0, width - 2))
        self.write(height - 1, " " + (self.status or KEYS),
                   curses.A_BOLD if self.status else curses.A_DIM)
        self.stdscr.refresh()

    def draw_entry(self, row, name, selected):
        width = self.stdscr.getmaxyx()[1]
        path = os.path.join(self.cwd, name)
        is_dir = os.path.isdir(path)
        label = f" {'▸' if selected else ' '} {name}{'/' if is_dir else ''}"

        stamp = "" if name == ".." else ago(max(0, time.time() - os.path.getmtime(path)))
        pad = max(1, width - len(label) - len(stamp) - 2)
        attr = curses.A_REVERSE if selected else (curses.A_BOLD if is_dir else 0)
        self.write(row, f"{label}{' ' * pad}{stamp}", attr)

    def write(self, row, text, attr=0):
        """Write a line, clipped to the window (curses errors on the last cell)."""
        height, width = self.stdscr.getmaxyx()
        if 0 <= row < height:
            try:
                self.stdscr.addnstr(row, 0, text, width - 1, attr)
            except curses.error:
                pass

    # --- input -------------------------------------------------------------

    def prompt(self, label, initial=""):
        """Read a line at the footer. Returns None if cancelled or empty."""
        height = self.stdscr.getmaxyx()[0]
        buffer = list(initial)
        self.cursor(True)
        try:
            while True:
                self.write(height - 1, " " + label + "".join(buffer) + " ")
                self.stdscr.clrtoeol()
                self.stdscr.refresh()
                key = self.stdscr.getch()
                if key == ESCAPE:
                    return None
                if key in ENTER:
                    return "".join(buffer).strip() or None
                if key in BACKSPACE:
                    if buffer:
                        buffer.pop()
                elif 32 <= key < 127:
                    buffer.append(chr(key))
        finally:
            self.cursor(False)

    def confirm(self, question):
        height = self.stdscr.getmaxyx()[0]
        self.write(height - 1, f" {question} [y/N] ")
        self.stdscr.clrtoeol()
        self.stdscr.refresh()
        return self.stdscr.getch() in (ord("y"), ord("Y"))

    def cursor(self, visible):
        try:
            curses.curs_set(1 if visible else 0)
        except curses.error:
            pass

    def suspend(self, path):
        """Drop out of curses, run $EDITOR, then restore the screen."""
        curses.def_prog_mode()
        curses.endwin()
        try:
            self.editor(path)
        finally:
            curses.reset_prog_mode()
            curses.flushinp()
            self.stdscr.clear()

    # --- actions -----------------------------------------------------------

    @property
    def selected(self):
        return self.items[self.index] if self.items else None

    def open(self):
        name = self.selected
        if name is None:
            return
        if name == "..":
            return self.leave()
        path = os.path.join(self.cwd, name)
        if os.path.isdir(path):
            self.enter(path)
        else:
            self.suspend(path)
            self.status = f"✓ Saved {name}"

    def enter(self, path):
        self.cwd = path
        self.index = self.offset = 0

    def leave(self):
        if self.cwd == self.root:
            return
        leaving = os.path.basename(self.cwd)
        self.cwd = os.path.dirname(self.cwd)
        self.refresh_items()
        if leaving in self.items:
            self.index = self.items.index(leaving)

    def new_note(self):
        name = self.prompt("New note: ")
        if not name:
            return
        if not valid_name(name):
            self.status = "Name cannot contain '/'"
            return
        if not name.endswith(".md"):
            name += ".md"
        path = os.path.join(self.cwd, name)
        if os.path.exists(path):
            self.status = f"'{name}' already exists"
            return
        self.suspend(path)
        if os.path.exists(path) and os.path.getsize(path):
            self.status = f"✓ Created {name}"
            self.select(name)
        else:
            if os.path.exists(path):
                os.remove(path)
            self.status = "Note discarded (empty or not saved)"

    def new_dir(self):
        name = self.prompt("New directory: ")
        if not name:
            return
        if not valid_name(name):
            self.status = "Name cannot contain '/'"
            return
        os.makedirs(os.path.join(self.cwd, name), exist_ok=True)
        self.status = f"✓ Created {name}/"
        self.select(name)

    def rename(self):
        name = self.selected
        if name is None or name == "..":
            return
        new = self.prompt("Rename to: ", name)
        if not new or new == name:
            return
        if not valid_name(new):
            self.status = "Name cannot contain '/'"
            return
        path = os.path.join(self.cwd, name)
        if os.path.isfile(path) and not new.endswith(".md"):
            new += ".md"
        target = os.path.join(self.cwd, new)
        if os.path.exists(target):
            self.status = f"'{new}' already exists"
            return
        os.rename(path, target)
        self.status = f"✓ Renamed to {new}"
        self.select(new)

    def delete(self):
        name = self.selected
        if name is None or name == "..":
            return
        path = os.path.join(self.cwd, name)
        if os.path.isdir(path):
            if os.listdir(path):
                self.status = f"'{name}/' is not empty"
                return
            if self.confirm(f"Delete directory '{name}'?"):
                os.rmdir(path)
                self.status = f"✓ Deleted {name}/"
        elif self.confirm(f"Delete note '{name}'?"):
            os.remove(path)
            self.status = f"✓ Deleted {name}"

    def select(self, name):
        """Move the cursor onto a named entry after the listing changes."""
        self.refresh_items()
        if name in self.items:
            self.index = self.items.index(name)

    def move(self, delta):
        if self.items:
            self.index = max(0, min(self.index + delta, len(self.items) - 1))

    # --- loop --------------------------------------------------------------

    def run(self):
        self.cursor(False)
        self.stdscr.keypad(True)
        while True:
            self.refresh_items()
            self.draw()
            self.status = ""
            key = self.stdscr.getch()

            if key in (ord("q"), ESCAPE):
                return
            elif key in (curses.KEY_UP, ord("k")):
                self.move(-1)
            elif key in (curses.KEY_DOWN, ord("j")):
                self.move(1)
            elif key == curses.KEY_PPAGE:
                self.move(-self.rows)
            elif key == curses.KEY_NPAGE:
                self.move(self.rows)
            elif key in (ord("g"), curses.KEY_HOME):
                self.index = 0
            elif key in (ord("G"), curses.KEY_END):
                self.index = len(self.items) - 1
            elif key in ENTER or key in (curses.KEY_RIGHT, ord("l")):
                self.open()
            elif key in (curses.KEY_LEFT, ord("h")) or key in BACKSPACE:
                self.leave()
            elif key == ord("n"):
                self.new_note()
            elif key == ord("d"):
                self.new_dir()
            elif key == ord("r"):
                self.rename()
            elif key == ord("x"):
                self.delete()


def browse(root, editor):
    """Entry point: run the browser rooted at `root`, editing via `editor`."""
    os.makedirs(root, exist_ok=True)
    curses.wrapper(lambda stdscr: Browser(stdscr, root, editor).run())
