#!/usr/bin/env python3
import json
import os
import sys

TODO_FILE = os.path.expanduser("~/.terminal_todos.json")

HELP = """
DBTerminal - Command-line task manager

Usage:
  db todo add <task>       Add a new todo
  db todo list             Show all todos
  db todo done <number>    Mark a todo as done
  db todo remove <number>  Remove a specific todo
  db todo move <number> <position>  Move a todo to a new position
  db todo priority <number>  Pin a todo to the top (only one at a time)
  db todo priority clear     Remove priority from current pinned todo
  db todo clear            Remove only completed todos
  db todo clear all        Clear all todos
  db todo edit <number> <new text>  Edit a todo's text
  db todo help             Show this help message

Examples:
  db todo add Buy groceries
  db todo done 1
  db todo remove 2
  db todo edit 1 Buy organic groceries
"""


def load():
    if os.path.exists(TODO_FILE):
        with open(TODO_FILE) as f:
            return json.load(f)
    return []


def save(todos):
    with open(TODO_FILE, "w") as f:
        json.dump(todos, f, indent=2)


def list_todos():
    todos = load()
    if not todos:
        print("No todos yet! Add one with: db todo add <your task>")
        return
    print("\nYour TODOs:")
    print("-" * 50)
    for i, todo in enumerate(todos, 1):
        status = "✓" if todo["done"] else " "
        if todo.get("priority"):
            print(f"*  [{status}] {todo['text']}")
            print("-" * 50)
        else:
            print(f"{i}. [{status}] {todo['text']}")
    print("-" * 50)
    print()


def add(text):
    todos = load()
    todos.append({"text": text, "done": False})
    save(todos)
    print(f"✓ Added: {text}")


def at(todos, index):
    """Return the 0-based todo for a 1-based index, or None if out of range."""
    if 1 <= index <= len(todos):
        return todos[index - 1]
    print(f"Invalid todo number: {index}")
    return None


def done(index):
    todos = load()
    todo = at(todos, index)
    if todo:
        todo["done"] = True
        save(todos)
        print(f"✓ Marked as done: {todo['text']}")


def remove(index):
    todos = load()
    if at(todos, index):
        print(f"✓ Removed: {todos.pop(index - 1)['text']}")
        save(todos)


def move(from_index, to_index):
    todos = load()
    if not at(todos, from_index):
        return
    if not (1 <= to_index <= len(todos)):
        print(f"Invalid position: {to_index}")
        return
    todo = todos.pop(from_index - 1)
    todos.insert(to_index - 1, todo)
    save(todos)
    print(f"✓ Moved '{todo['text']}' to position {to_index}")


def set_priority(index):
    todos = load()
    todo = at(todos, index)
    if not todo:
        return
    for t in todos:
        t["priority"] = False
    todo["priority"] = True
    todos.insert(0, todos.pop(index - 1))
    save(todos)
    print(f"✓ Prioritised: {todo['text']}")


def clear_priority():
    todos = load()
    cleared = any(t.get("priority") for t in todos)
    for t in todos:
        t["priority"] = False
    save(todos)
    print("✓ Priority cleared." if cleared else "No priority set.")


def edit(index, text):
    todos = load()
    todo = at(todos, index)
    if todo:
        old = todo["text"]
        todo["text"] = text
        save(todos)
        print(f"✓ Updated: {old} → {text}")


def clear_all():
    if os.path.exists(TODO_FILE):
        os.remove(TODO_FILE)
        print("✓ All todos cleared!")
    else:
        print("No todos to clear.")


def clear_done():
    todos = load()
    remaining = [t for t in todos if not t["done"]]
    save(remaining)
    print(f"✓ Removed {len(todos) - len(remaining)} completed todo(s)")


def number(args, usage):
    """Parse a single 1-based index argument, or None on bad/missing input."""
    if not args:
        print(usage)
    elif not args[0].lstrip("-").isdigit():
        print("Please provide a valid number")
    else:
        return int(args[0])
    return None


def main():
    cmd, *args = sys.argv[1:] or [""]
    cmd = cmd.lower()

    if cmd in ("", "list"):
        list_todos()
    elif cmd == "add":
        add(" ".join(args)) if args else print("Usage: db todo add <task>")
    elif cmd == "done":
        n = number(args, "Usage: db todo done <number>")
        if n is not None:
            done(n)
    elif cmd == "remove":
        n = number(args, "Usage: db todo remove <number>")
        if n is not None:
            remove(n)
    elif cmd == "move":
        n = number(args, "Usage: db todo move <number> <position>")
        if n is not None:
            m = number(args[1:], "Usage: db todo move <number> <position>")
            if m is not None:
                move(n, m)
    elif cmd == "priority":
        if args and args[0].lower() == "clear":
            clear_priority()
        else:
            n = number(args, "Usage: db todo priority <number>")
            if n is not None:
                set_priority(n)
    elif cmd == "edit":
        n = number(args, "Usage: db todo edit <number> <new text>")
        if n is not None:
            new_text = " ".join(args[1:])
            if new_text:
                edit(n, new_text)
            else:
                print("Usage: db todo edit <number> <new text>")
    elif cmd == "clear":
        if args and args[0].lower() == "all":
            clear_all()
        else:
            clear_done()
    elif cmd == "help":
        print(HELP)
    else:
        print(f"Unknown command: {cmd}")
        print("Run 'db todo help' for usage information")


if __name__ == "__main__":
    main()
