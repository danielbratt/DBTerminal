#!/usr/bin/env python3
import json
import os
import re
import sys

TODO_FILE = os.path.expanduser("~/.terminal_todos.json")

HELP = """
DBTerminal - Command-line task manager

Usage:
  db todo add <task>              Add a new todo (goes in TODO)
  db todo add -p <task>           Add a task and pin it into the Priority stack
  db todo add -n <task>           Add a task to the Park section
  db todo add <number> <task>     Add a sub-item under TODO task <number>
  db todo list                    Show all todos
  db todo done <target>           Mark a todo as done
  db todo undone <target>         Mark a todo as not done
  db todo remove <target>         Remove a specific todo
  db todo move <number> <position>  Move a TODO task to a new position
  db todo swap <target1> <target2>  Swap two tasks in the same section
  db todo priority <target>       Push a task onto the Priority stack (max 3)
  db todo priority clear          Remove all Priority tasks
  db todo priority clear <1|2|3>  Remove a single Priority slot
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
  <number><letter>  a sub-item under a TODO task, e.g. 1a, 1b, 1c
  P1, P2, P3     a task's slot in the Priority stack (max 3 at a time)
  <letter>       the task's position in the Park section (a, b, c, ...)

Examples:
  db todo add Buy groceries
  db todo add -p Fix production bug
  db todo add -n Read that article someday
  db todo add 1 Write tests           Add sub-item 1a under task 1
  db todo done 1
  db todo done 1a
  db todo done P1
  db todo done a
  db todo remove 2
  db todo remove 1a
  db todo edit 1 Buy organic groceries
  db todo edit 1a Write more tests
  db todo swap 1 2         Swap TODO tasks 1 and 2
  db todo swap P1 P2       Swap Priority slots P1 and P2
  db todo priority b      Push Park task b onto the Priority stack
  db todo priority clear 2   Clear just slot P2
  db todo park 3          Move TODO task 3 into Park
  db todo park P1         Move Priority slot P1's task into Park
  db todo unpark a        Move Park task a back into TODO
  db todo hide park       Collapse the Park section
  db todo show park       Bring the Park section back
"""

SUB_TARGET_RE = re.compile(r"^(\d+)([a-z])$")


def read_file():
    """Read the todo file as {"todos": [...], "hidden": [...]}, accepting the
    older format where the file was a bare list of todos."""
    if not os.path.exists(TODO_FILE):
        return {"todos": [], "hidden": []}
    with open(TODO_FILE) as f:
        data = json.load(f)
    if isinstance(data, list):
        return {"todos": data, "hidden": []}
    todos = data.get("todos", [])
    for t in todos:
        if t.get("priority") is True:
            t["priority"] = 1
    return {"todos": todos, "hidden": data.get("hidden", [])}


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


def normal_lines(normal):
    """Render TODO section lines, including each task's sub-items indented
    underneath it (1, 1a, 1b, 2, ...)."""
    lines = []
    for i, t in enumerate(normal, 1):
        lines.append(f"{i}. [{'✓' if t['done'] else ' '}] {t['text']}")
        for j, sub in enumerate(t.get("sub", []), 1):
            lines.append(
                f"   {i}{park_label(j)}. [{'✓' if sub['done'] else ' '}] {sub['text']}"
            )
    return lines


def list_todos():
    todos = load()
    hidden = load_hidden()
    if not todos:
        print("No todos yet! Add one with: db todo add <your task>")
        return
    priority = sorted(
        (t for t in todos if t.get("priority")), key=lambda t: t["priority"]
    )
    park = [t for t in todos if t.get("park")]
    normal = [t for t in todos if not t.get("priority") and not t.get("park")]
    print()
    if priority:
        print_section(
            "Priority",
            [
                f"P{t['priority']}  [{'✓' if t['done'] else ' '}] {t['text']}"
                for t in priority
            ],
            False,
        )
    if normal or "tasks" in hidden:
        if priority:
            print()
        print_section("Tasks", normal_lines(normal), "tasks" in hidden)
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
        rank = first_free_priority_rank(todos)
        if rank is None:
            print("Priority stack is full (max 3). Clear one first.")
            return
        todo["priority"] = rank
        todos.insert(0, todo)
        print(f"✓ Added priority task: {text} (P{rank})")
    elif park:
        todo["park"] = True
        todos.append(todo)
        count = sum(1 for t in todos if t.get("park"))
        print(f"✓ Added to Park: {text} ({park_label(count)})")
    else:
        todos.append(todo)
        count = sum(1 for t in todos if not t.get("priority") and not t.get("park"))
        print(f"✓ Added: {text} ({count})")
    save(todos)


def add_sub(parent_number, text):
    todos = load()
    idx = normal_index(todos, parent_number)
    if idx is None:
        print(f"Invalid todo number: {parent_number}")
        return
    parent = todos[idx - 1]
    subs = parent.setdefault("sub", [])
    subs.append({"text": text, "done": False})
    save(todos)
    print(f"✓ Added {parent_number}{park_label(len(subs))}: {text}")


def resolve_sub(todos, parent_number, sub_number):
    """Return (parent_raw_index, sub_raw_index), or (None, None) after
    printing an error."""
    parent_idx = normal_index(todos, parent_number)
    if parent_idx is None:
        print(f"Invalid todo number: {parent_number}")
        return None, None
    subs = todos[parent_idx - 1].get("sub", [])
    if not (1 <= sub_number <= len(subs)):
        print(f"Invalid sub-item: {parent_number}{park_label(sub_number)}")
        return None, None
    return parent_idx, sub_number


def done_sub(value):
    parent_number, sub_number = value
    todos = load()
    parent_idx, sub_idx = resolve_sub(todos, parent_number, sub_number)
    if parent_idx is None:
        return
    sub = todos[parent_idx - 1]["sub"][sub_idx - 1]
    sub["done"] = True
    save(todos)
    print(f"✓ Marked as done: {sub['text']}")


def undone_sub(value):
    parent_number, sub_number = value
    todos = load()
    parent_idx, sub_idx = resolve_sub(todos, parent_number, sub_number)
    if parent_idx is None:
        return
    sub = todos[parent_idx - 1]["sub"][sub_idx - 1]
    sub["done"] = False
    save(todos)
    print(f"✓ Marked as not done: {sub['text']}")


def remove_sub(value):
    parent_number, sub_number = value
    todos = load()
    parent_idx, sub_idx = resolve_sub(todos, parent_number, sub_number)
    if parent_idx is None:
        return
    removed = todos[parent_idx - 1]["sub"].pop(sub_idx - 1)
    save(todos)
    print(f"✓ Removed: {removed['text']}")


def edit_sub(value, text):
    parent_number, sub_number = value
    todos = load()
    parent_idx, sub_idx = resolve_sub(todos, parent_number, sub_number)
    if parent_idx is None:
        return
    sub = todos[parent_idx - 1]["sub"][sub_idx - 1]
    old = sub["text"]
    sub["text"] = text
    save(todos)
    print(f"✓ Updated: {old} → {text}")


def priority_rank_index(todos, rank):
    """Return the 1-based raw index of the todo pinned to a Priority slot
    (1, 2, or 3), or None."""
    for i, t in enumerate(todos, 1):
        if t.get("priority") == rank:
            return i
    return None


def priority_ranks_used(todos):
    return {t["priority"] for t in todos if t.get("priority")}


def first_free_priority_rank(todos):
    """Return the lowest unused Priority slot (1, 2, or 3), or None if the
    stack is full."""
    used = priority_ranks_used(todos)
    for rank in (1, 2, 3):
        if rank not in used:
            return rank
    return None


def compact_priority_ranks(todos):
    """Re-number the remaining Priority tasks to close any gap left by a
    cleared or removed slot, so the stack stays contiguous from P1."""
    ranked = sorted((t for t in todos if t.get("priority")), key=lambda t: t["priority"])
    for new_rank, t in enumerate(ranked, 1):
        t["priority"] = new_rank


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
        idx = priority_rank_index(todos, value)
        if idx is None:
            print(f"No priority task in slot P{value}.")
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
    kind, value = target
    if kind == "sub":
        done_sub(value)
        return
    todos = load()
    idx = resolve(todos, target)
    if idx is None:
        return
    todo = todos[idx - 1]
    todo["done"] = True
    for sub in todo.get("sub", []):
        sub["done"] = True
    if todo.get("priority"):
        rank = todo["priority"]
        todo["priority"] = False
        compact_priority_ranks(todos)
        save(todos)
        print(f"✓ Marked as done: {todo['text']} (priority P{rank} cleared)")
        return
    save(todos)
    print(f"✓ Marked as done: {todo['text']}")


def undone(target):
    kind, value = target
    if kind == "sub":
        undone_sub(value)
        return
    todos = load()
    idx = resolve(todos, target)
    if idx is None:
        return
    todo = todos[idx - 1]
    todo["done"] = False
    save(todos)
    print(f"✓ Marked as not done: {todo['text']}")


def remove(target):
    kind, value = target
    if kind == "sub":
        remove_sub(value)
        return
    todos = load()
    idx = resolve(todos, target)
    if idx is None:
        return
    removed = todos.pop(idx - 1)
    compact_priority_ranks(todos)
    save(todos)
    print(f"✓ Removed: {removed['text']}")


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


def target_label(target):
    """Render a parsed target back into the form the user typed, for
    confirmation messages."""
    kind, value = target
    if kind == "priority":
        return f"P{value}"
    if kind == "park":
        return park_label(value)
    if kind == "sub":
        parent_number, sub_number = value
        return f"{parent_number}{park_label(sub_number)}"
    return str(value)


def swap(target1, target2):
    kind1, _ = target1
    kind2, _ = target2
    if kind1 != kind2 or kind1 == "sub":
        print("Can only swap two tasks within the same section (TODO, Priority, or Park).")
        return
    todos = load()
    idx1 = resolve(todos, target1)
    if idx1 is None:
        return
    idx2 = resolve(todos, target2)
    if idx2 is None:
        return
    if idx1 == idx2:
        print("Can't swap a task with itself.")
        return
    if kind1 == "priority":
        todos[idx1 - 1]["priority"], todos[idx2 - 1]["priority"] = (
            todos[idx2 - 1]["priority"],
            todos[idx1 - 1]["priority"],
        )
    else:
        todos[idx1 - 1], todos[idx2 - 1] = todos[idx2 - 1], todos[idx1 - 1]
    save(todos)
    print(f"✓ Swapped {target_label(target1)} and {target_label(target2)}")


def set_priority(target):
    todos = load()
    kind, value = target
    if kind == "priority":
        print(f"That task is already priority P{value}.")
        return
    rank = first_free_priority_rank(todos)
    if rank is None:
        print("Priority stack is full (max 3). Clear one first.")
        return
    idx = resolve(todos, target)
    if idx is None:
        return
    todo = todos.pop(idx - 1)
    todo["priority"] = rank
    todo["park"] = False
    todos.insert(0, todo)
    save(todos)
    print(f"✓ Prioritised (P{rank}): {todo['text']}")


def clear_priority(slot=None):
    todos = load()
    if slot is None:
        cleared = any(t.get("priority") for t in todos)
        for t in todos:
            t["priority"] = False
        save(todos)
        print("✓ Priority cleared." if cleared else "No priority set.")
        return
    idx = priority_rank_index(todos, slot)
    if idx is None:
        print(f"No priority task in slot P{slot}.")
        return
    todo = todos[idx - 1]
    todo["priority"] = False
    compact_priority_ranks(todos)
    save(todos)
    print(f"✓ Cleared priority P{slot}: {todo['text']}")


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
    compact_priority_ranks(todos)
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
    kind, value = target
    if kind == "sub":
        edit_sub(value, text)
        return
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
    ("priority", 1|2|3), ("park", n), ("sub", (parent_n, sub_n)), or
    ("todo", n). Returns (None, args) on bad/missing input, having already
    printed a message. Otherwise returns (target, remaining_args)."""
    if not args:
        print(usage)
        return None, args
    if args[0].upper() in ("P1", "P2", "P3"):
        return ("priority", int(args[0][1])), args[1:]
    if args[0] == "*" or args[0].upper() == "P":
        print("Please specify a priority slot: P1, P2, or P3")
        return None, args
    sub_match = SUB_TARGET_RE.match(args[0])
    if sub_match:
        parent_number = int(sub_match.group(1))
        sub_number = park_letter_to_number(sub_match.group(2))
        return ("sub", (parent_number, sub_number)), args[1:]
    if is_park_letter(args[0]):
        return ("park", park_letter_to_number(args[0])), args[1:]
    if not args[0].lstrip("-").isdigit():
        print(
            "Please provide a valid number, P1/P2/P3, a sub-item (1a, 1b, ...), "
            "or a Park letter (a, b, c, ...)"
        )
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
        elif args and args[0].isdigit():
            parent_number = int(args[0])
            text = " ".join(args[1:])
            add_sub(parent_number, text) if text else print(
                "Usage: db todo add <number> <task>"
            )
        elif args:
            add(" ".join(args))
        else:
            print("Usage: db todo add <task>")
    elif cmd == "done":
        t, _ = parse_target(args, "Usage: db todo done <number|1a|P1|P2|P3|letter>")
        if t is not None:
            done(t)
    elif cmd == "undone":
        t, _ = parse_target(args, "Usage: db todo undone <number|1a|P1|P2|P3|letter>")
        if t is not None:
            undone(t)
    elif cmd == "remove":
        t, _ = parse_target(args, "Usage: db todo remove <number|1a|P1|P2|P3|letter>")
        if t is not None:
            remove(t)
    elif cmd == "move":
        n = number(args, "Usage: db todo move <number> <position>")
        if n is not None:
            m = number(args[1:], "Usage: db todo move <number> <position>")
            if m is not None:
                move(n, m)
    elif cmd == "swap":
        t1, rest = parse_target(args, "Usage: db todo swap <target1> <target2>")
        if t1 is not None:
            t2, _ = parse_target(rest, "Usage: db todo swap <target1> <target2>")
            if t2 is not None:
                swap(t1, t2)
    elif cmd == "priority":
        if args and args[0].lower() == "clear":
            if len(args) > 1:
                n = number(args[1:], "Usage: db todo priority clear <1|2|3>")
                if n is not None:
                    if n in (1, 2, 3):
                        clear_priority(n)
                    else:
                        print("Priority slot must be 1, 2, or 3")
            else:
                clear_priority()
        else:
            t, _ = parse_target(args, "Usage: db todo priority <number|P1|P2|P3|letter>")
            if t is not None:
                set_priority(t)
    elif cmd == "park":
        t, _ = parse_target(args, "Usage: db todo park <number|P1|P2|P3>")
        if t is not None:
            set_park(t)
    elif cmd == "unpark":
        n = letter(args, "Usage: db todo unpark <letter>")
        if n is not None:
            unpark(n)
    elif cmd == "edit":
        t, rest = parse_target(
            args, "Usage: db todo edit <number|1a|P1|P2|P3|letter> <new text>"
        )
        if t is not None:
            new_text = " ".join(rest)
            if new_text:
                edit(t, new_text)
            else:
                print("Usage: db todo edit <number|1a|P1|P2|P3|letter> <new text>")
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
