#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def show_help():
    print("""
DBTerminal - Your terminal companion

Usage:
  db todo <command>    Manage todos
  db note <command>    Manage notes

Run 'db todo help' or 'db note help' for command details.
""")

def main():
    if len(sys.argv) < 2:
        show_help()
        return

    module = sys.argv[1].lower()
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    if module == "todo":
        from todo import main as todo_main
        todo_main()
    elif module == "note":
        from note import main as note_main
        note_main()
    else:
        print(f"Unknown module: {module}")
        show_help()

if __name__ == "__main__":
    main()
