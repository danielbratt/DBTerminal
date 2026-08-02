#!/usr/bin/env python3
import json
import os
import sys

TODO_FILE = os.path.expanduser("~/.terminal_todos.json")

HELP = """
DBTerminal - Command-line task manager

Usage:
  db todo add <task>              Add a new todo (goes in TODO)
  db todo add -p <task>           Add a task and pin it as the priority
  db todo add -n <task>           Add a task to the Park section
  db todo list                    Show all todos
  db todo done <target>           Mark a todo as done
  db todo undone <target>         Mark a todo as not done
  db todo remove <target>         Remove a specific todo
  db todo move <number> <position>  Move a TODO task to a new position
  db todo priority <target>       Pin a task to the top (only one at a time)
  db todo priority clear          Remove priority from current pinned todo
  db todo park <target>           Move a task into the Park section
  db todo unpark <letter>         Move a Park task back into TODO
  db todo hide <tasks|park>       Collapse a section in the list
  db todo show <tasks|park>       Reveal a hidden section
  db todo clear                   Remove only completed todos
  db todo clear all               Clear all todos
  db todo edit <target> <new text>  Edit a todo's text
  db todo help                    Show this help message

<target> addresses a task:
  <number>       the task's position in the TODO section
  *              the Priority task
  <letter>       the task's position in the Park section (a, b, c, ...)

Examples:
  db todo add Buy groceries
  db todo add -p Fix production bug
  db todo add -n Read that article someday
  db todo done 1
  db todo done *
  db todo done a
  db todo remove 2
  db todo edit 1 Buy organic groceries
  db todo priority b      Promote Park task b straight to Priority
  db todo park 3          Move TODO task 3 into Park
  db todo park *          Move the Priority task into Park
  db todo unpark a        Move Park task a back into TODO
  db todo hide park       Collapse the Park section
  db todo show park       Bring the Park section back
"""


def read_file():
    """Read the todo file as {"todos": [...], "hidden": [...]}, accepting the
    older format where the file was a bare list of todos."""
    if not os.path.exists(TODO_FILE):
        return {"todos": [], "hidden": []}
    with open(TODO_FILE) as f:
        data = json.load(f)
    if isinstance(data, list):
        return {"todos": data, "hidden": []}
    return {"todos": data.get("todos", []), "hidden": data.get("hidden", [])}


def load():
    return read_file()["todos"]


def save(todos):
    data = read_file()
    data["todos"] = todos
    with open(TODO_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_hidden():
    return read_file()["hidden"]


def save_hidden(hidden):
    data = read_file()
    data["hidden"] = hidden
    with open(TODO_FILE, "w") as f:
        json.dump(data, f, indent=2)


def italic(text):
    """Wrap text in ANSI italics, or leave it bare when piped to a file."""
    if sys.stdout.isatty():
        return f"\033[3m{text}\033[0m"
    return text


def print_section(title, lines, hidden):
    print(title)
    print("-" * 50)
    if hidden:
        print(f"  {italic('This section is hidden')}")
    else:
        for line in lines:
            print(line)
    print("-" * 50)


def list_todos():
    todos = load()
    hidden = load_hidden()
    if not todos:
        print("No todos yet! Add one with: db todo add <your task>")
        return
    priority = [t for t in todos if t.get("priority")]
    park = [t for t in todos if t.get("park")]
    normal = [t for t in todos if not t.get("priority") and not t.get("park")]
    print()
    if priority:
        print_section(
            "Priority",
            [f"*  [{'✓' if t['done'] else ' '}] {t['text']}" for t in priority],
            False,
        )
    if normal or "tasks" in hidden:
        if priority:
            print()
        print_section(
            "Tasks",
            [
                f"{i}. [{'✓' if t['done'] else ' '}] {t['text']}"
                for i, t in enumerate(normal, 1)
            ],
            "tasks" in hidden,
        )
    if park or "park" in hidden:
        if priority or normal or "tasks" in hidden:
            print()
        print_section(
            "Parked",
            [
                f"{park_label(i)}. [{'✓' if t['done'] else ' '}] {t['text']}"
                for i, t in enumerate(park, 1)
            ],
            "park" in hidden,
        )
    print()


def add(text, priority=False, park=False):
    todos = load()
    todo = {"text": text, "done": False}
    if priority:
        for t in todos:
            t["priority"] = False
        todo["priority"] = True
        todos.insert(0, todo)
        print(f"✓ Added priority task: {text}")
    elif park:
        todo["park"] = True
        todos.append(todo)
        print(f"✓ Added to Park: {text}")
    else:
        todos.append(todo)
        print(f"✓ Added: {text}")
    save(todos)


def priority_index(todos):
    """Return the 1-based raw index of the priority todo, or None."""
    for i, t in enumerate(todos, 1):
        if t.get("priority"):
            return i
    return None


def normal_index(todos, display_number):
    """Map a 1-based number from the TODO section to its raw 1-based index."""
    if display_number < 1:
        return None
    count = 0
    for i, t in enumerate(todos, 1):
        if t.get("priority") or t.get("park"):
            continue
        count += 1
        if count == display_number:
            return i
    return None


def park_index(todos, display_number):
    """Map a 1-based number from the Park section to its raw 1-based index."""
    if display_number < 1:
        return None
    count = 0
    for i, t in enumerate(todos, 1):
        if not t.get("park"):
            continue
        count += 1
        if count == display_number:
            return i
    return None


def park_label(display_number):
    """Render a 1-based Park position as its display letter (a, b, c, ...)."""
    if 1 <= display_number <= 26:
        return chr(ord("a") + display_number - 1)
    return str(display_number)


def park_letter_to_number(letter):
    """Convert a lowercase Park letter (a, b, c, ...) to its 1-based number."""
    return ord(letter) - ord("a") + 1


def resolve(todos, target):
    """Resolve a parsed (kind, value) target to a raw 1-based index into
    todos, printing an error and returning None if it doesn't match anything."""
    kind, value = target
    if kind == "priority":
        idx = priority_index(todos)
        if idx is None:
            print("No priority todo set.")
        return idx
    if kind == "park":
        idx = park_index(todos, value)
        if idx is None:
            print(f"Invalid Park todo letter: {park_label(value)}")
        return idx
    idx = normal_index(todos, value)
    if idx is None:
        print(f"Invalid todo number: {value}")
    return idx


def insert_position(todos, display_position):
    """0-based index at which to insert so the item lands at
    display_position among the non-priority, non-park todos already in the
    list."""
    count = 0
    for i, t in enumerate(todos):
        if not t.get("priority") and not t.get("park"):
            count += 1
            if count == display_position:
                return i
    return len(todos)


def done(target):
    todos = load()
    idx = resolve(todos, target)
    if idx is None:
        return
    todo = todos[idx - 1]
    todo["done"] = True
    if todo.get("priority"):
        todo["priority"] = False
        save(todos)
        print(f"✓ Marked as done: {todo['text']} (priority cleared)")
        return
    save(todos)
    print(f"✓ Marked as done: {todo['text']}")


def undone(target):
    todos = load()
    idx = resolve(todos, target)
    if idx is None:
        return
    todo = todos[idx - 1]
    todo["done"] = False
    save(todos)
    print(f"✓ Marked as not done: {todo['text']}")


def remove(target):
    todos = load()
    idx = resolve(todos, target)
    if idx is None:
        return
    print(f"✓ Removed: {todos.pop(idx - 1)['text']}")
    save(todos)


def move(from_display, to_display):
    todos = load()
    from_idx = normal_index(todos, from_display)
    if from_idx is None:
        print(f"Invalid todo number: {from_display}")
        return
    normal_count = sum(
        1 for t in todos if not t.get("priority") and not t.get("park")
    )
    if not (1 <= to_display <= normal_count):
        print(f"Invalid position: {to_display}")
        return
    todo = todos.pop(from_idx - 1)
    todos.insert(insert_position(todos, to_display), todo)
    save(todos)
    print(f"✓ Moved '{todo['text']}' to position {to_display}")


def set_priority(target):
    todos = load()
    kind, _ = target
    if kind == "priority":
        print("That task is already the priority.")
        return
    idx = resolve(todos, target)
    if idx is None:
        return
    for t in todos:
        t["priority"] = False
    todo = todos.pop(idx - 1)
    todo["priority"] = True
    todo["park"] = False
    todos.insert(0, todo)
    save(todos)
    print(f"✓ Prioritised: {todo['text']}")


def clear_priority():
    todos = load()
    cleared = any(t.get("priority") for t in todos)
    for t in todos:
        t["priority"] = False
    save(todos)
    print("✓ Priority cleared." if cleared else "No priority set.")


def set_park(target):
    todos = load()
    kind, _ = target
    if kind == "park":
        print("That task is already parked.")
        return
    idx = resolve(todos, target)
    if idx is None:
        return
    todo = todos.pop(idx - 1)
    todo["priority"] = False
    todo["park"] = True
    todos.append(todo)
    save(todos)
    print(f"✓ Parked: {todo['text']}")


def unpark(display_number):
    todos = load()
    idx = park_index(todos, display_number)
    if idx is None:
        print(f"Invalid Park todo letter: {park_label(display_number)}")
        return
    todo = todos[idx - 1]
    todo["park"] = False
    save(todos)
    print(f"✓ Moved to TODO: {todo['text']}")


def edit(target, text):
    todos = load()
    idx = resolve(todos, target)
    if idx is None:
        return
    todo = todos[idx - 1]
    old = todo["text"]
    todo["text"] = text
    save(todos)
    print(f"✓ Updated: {old} → {text}")


SECTION_NAMES = {
    "tasks": "tasks",
    "task": "tasks",
    "todo": "tasks",
    "todos": "tasks",
    "list": "tasks",
    "park": "park",
    "parked": "park",
}


def section(name):
    """Resolve a section argument to its key, or None if it isn't one."""
    key = SECTION_NAMES.get(name.lower())
    if key is None:
        print(f"Unknown section: {name}. Use 'tasks' or 'park'.")
    return key


def hide(name):
    key = section(name)
    if key is None:
        return
    hidden = load_hidden()
    if key in hidden:
        print(f"The {key} section is already hidden.")
        return
    hidden.append(key)
    save_hidden(hidden)
    print(f"✓ Hid the {key} section.")


def show(name):
    key = section(name)
    if key is None:
        return
    hidden = load_hidden()
    if key not in hidden:
        print(f"The {key} section is not hidden.")
        return
    hidden.remove(key)
    save_hidden(hidden)
    print(f"✓ Showing the {key} section again.")


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
    """Parse a single 1-based number argument, or None on bad/missing input."""
    if not args:
        print(usage)
    elif not args[0].lstrip("-").isdigit():
        print("Please provide a valid number")
    else:
        return int(args[0])
    return None


def is_park_letter(arg):
    return len(arg) == 1 and arg.isalpha() and arg.islower()


def letter(args, usage):
    """Parse a single lowercase Park letter argument, or None on bad/missing input."""
    if not args:
        print(usage)
    elif not is_park_letter(args[0]):
        print("Please provide a valid Park letter (a, b, c, ...)")
    else:
        return park_letter_to_number(args[0])
    return None


def parse_target(args, usage):
    """Parse a leading target argument into a (kind, value) tuple:
    ("priority", None), ("park", n), or ("todo", n). Returns
    (None, args) on bad/missing input, having already printed a message.
    Otherwise returns (target, remaining_args)."""
    if not args:
        print(usage)
        return None, args
    if args[0] == "*":
        return ("priority", None), args[1:]
    if is_park_letter(args[0]):
        return ("park", park_letter_to_number(args[0])), args[1:]
    if not args[0].lstrip("-").isdigit():
        print("Please provide a valid number, *, or a Park letter (a, b, c, ...)")
        return None, args
    return ("todo", int(args[0])), args[1:]


def main():
    cmd, *args = sys.argv[1:] or [""]
    cmd = cmd.lower()

    if cmd in ("", "list"):
        list_todos()
    elif cmd == "add":
        if args and args[0] in ("-p", "--priority"):
            text = " ".join(args[1:])
            add(text, priority=True) if text else print("Usage: db todo add -p <task>")
        elif args and args[0] in ("-n", "--park"):
            text = " ".join(args[1:])
            add(text, park=True) if text else print("Usage: db todo add -n <task>")
        elif args:
            add(" ".join(args))
        else:
            print("Usage: db todo add <task>")
    elif cmd == "done":
        t, _ = parse_target(args, "Usage: db todo done <number|*|letter>")
        if t is not None:
            done(t)
    elif cmd == "undone":
        t, _ = parse_target(args, "Usage: db todo undone <number|*|letter>")
        if t is not None:
            undone(t)
    elif cmd == "remove":
        t, _ = parse_target(args, "Usage: db todo remove <number|*|letter>")
        if t is not None:
            remove(t)
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
            t, _ = parse_target(args, "Usage: db todo priority <number|*|letter>")
            if t is not None:
                set_priority(t)
    elif cmd == "park":
        t, _ = parse_target(args, "Usage: db todo park <number|*>")
        if t is not None:
            set_park(t)
    elif cmd == "unpark":
        n = letter(args, "Usage: db todo unpark <letter>")
        if n is not None:
            unpark(n)
    elif cmd == "edit":
        t, rest = parse_target(args, "Usage: db todo edit <number|*|letter> <new text>")
        if t is not None:
            new_text = " ".join(rest)
            if new_text:
                edit(t, new_text)
            else:
                print("Usage: db todo edit <number|*|letter> <new text>")
    elif cmd == "hide":
        hide(args[0]) if args else print("Usage: db todo hide <tasks|park>")
    elif cmd == "show":
        show(args[0]) if args else print("Usage: db todo show <tasks|park>")
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
