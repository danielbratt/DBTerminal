#!/usr/bin/env python3
import os
import sys
import subprocess

NOTES_DIR = os.path.expanduser("~/.dbterminal/notes")

HELP = """
DBTerminal Notes - Filesystem-based note manager

Notes are stored as markdown files in ~/.dbterminal/notes/

Usage:
  db note add <path> [text]   Create a note (opens editor if no text given)
  db note list [dir]          List notes and subdirectories
  db note show <path>         Print a note's content
  db note edit <path>         Open a note in $EDITOR
  db note remove <path>       Delete a note
  db note mkdir <dir>         Create a directory
  db note rmdir <dir>         Remove an empty directory
  db note help                Show this help message

Examples:
  db note add work/standup "Team sync at 9am"
  db note add ideas/project-x
  db note list work
  db note show work/standup
  db note mkdir personal
  db note remove work/standup
"""


def resolve(path, md=False):
    """Absolute path within NOTES_DIR (adds .md if md=True), rejecting traversal."""
    if md and not path.endswith(".md"):
        path += ".md"
    full = os.path.normpath(os.path.join(NOTES_DIR, path))
    if full != NOTES_DIR and not full.startswith(NOTES_DIR + os.sep):
        sys.exit("Error: invalid path")
    return full


def editor(path):
    subprocess.call([os.environ.get("EDITOR", "nano"), path])


def add_note(path, inline_text=None):
    full = resolve(path, md=True)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    if inline_text:
        with open(full, "w") as f:
            f.write(inline_text + "\n")
    else:
        editor(full)
        if not (os.path.exists(full) and os.path.getsize(full) > 0):
            print("Note discarded (empty or not saved).")
            return
    print(f"✓ Note saved: {path}")


def list_notes(directory="."):
    full = resolve(directory)
    if not os.path.isdir(full):
        print(f"Directory not found: {directory}")
        return

    entries = sorted(os.listdir(full))
    rel = os.path.relpath(full, NOTES_DIR)
    if not entries:
        print(f"No notes in {'notes root' if rel == '.' else rel}.")
        return

    print(f"\nNotes in {'/' if rel == '.' else '/' + rel}:")
    print("-" * 40)
    for entry in entries:
        if os.path.isdir(os.path.join(full, entry)):
            print(f"  {entry}/")
        else:
            print(f"  {entry[:-3] if entry.endswith('.md') else entry}")
    print("-" * 40)


def show_note(path):
    full = resolve(path, md=True)
    if not os.path.exists(full):
        print(f"Note not found: {path}")
        return
    with open(full) as f:
        print(f"\n--- {os.path.basename(full)[:-3]} ---")
        print(f.read())


def edit_note(path):
    full = resolve(path, md=True)
    if not os.path.exists(full):
        print(f"Note not found: {path}")
        return
    editor(full)
    print(f"✓ Note updated: {path}")


def remove_note(path):
    full = resolve(path, md=True)
    if not os.path.exists(full):
        print(f"Note not found: {path}")
        return
    os.remove(full)
    print(f"✓ Removed note: {path}")


def make_dir(directory):
    os.makedirs(resolve(directory), exist_ok=True)
    print(f"✓ Created directory: {directory}")


def remove_dir(directory):
    full = resolve(directory)
    if not os.path.isdir(full):
        print(f"Directory not found: {directory}")
    elif os.listdir(full):
        print(f"Directory '{directory}' is not empty. Remove its contents first.")
    else:
        os.rmdir(full)
        print(f"✓ Removed directory: {directory}")


def main():
    os.makedirs(NOTES_DIR, exist_ok=True)
    cmd, *args = sys.argv[1:] or [""]
    cmd = cmd.lower()

    if cmd in ("", "list"):
        list_notes(args[0] if args else ".")
    elif cmd == "add" and args:
        add_note(args[0], " ".join(args[1:]) or None)
    elif cmd == "show" and args:
        show_note(args[0])
    elif cmd == "edit" and args:
        edit_note(args[0])
    elif cmd == "remove" and args:
        remove_note(args[0])
    elif cmd == "mkdir" and args:
        make_dir(args[0])
    elif cmd == "rmdir" and args:
        remove_dir(args[0])
    elif cmd == "help":
        print(HELP)
    elif cmd in ("add", "show", "edit", "remove", "mkdir", "rmdir"):
        print(f"Usage: db note {cmd} <path>")
    else:
        print(f"Unknown command: {cmd}")
        print("Run 'db note help' for usage information")


if __name__ == "__main__":
    main()
