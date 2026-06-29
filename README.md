# DBTerminal

A personal terminal toolkit — small command-line tools behind a single `db`
command. Pure Python 3 standard library and a zsh config: no `pip install`, no
external downloads, no network access at install or runtime.

## Requirements

- **Python 3** (standard library only)
- **zsh** (shell integration and the `db` alias go in `~/.zshrc`)

## Install

```bash
./install/install.sh
source ~/.zshrc
```

Idempotent and non-destructive: it marks `src/` scripts executable and appends a
guarded `# >>> DBTerminal >>>` block to `~/.zshrc`.

## Usage

```bash
db <tool> <command> [args]
```

Run `db` for an overview or `db <tool> help` for any tool's details.

### `db todo` — tasks (stored in `~/.terminal_todos.json`)

```bash
db todo add <task>        db todo done <number>     db todo clear-done
db todo list              db todo remove <number>   db todo clear
```

### `db note` — markdown notes (stored in `~/.dbterminal/notes/`)

```bash
db note add <path> [text]   db note show <path>    db note mkdir <dir>
db note list [dir]          db note edit <path>    db note rmdir <dir>
db note remove <path>
```

## Shell features

Sourcing `install/shell.zsh` also adds a dir + git-branch prompt, `cd`-less
navigation, and git aliases (`gs`, `ga`, `gco`, `gp`, …).

## Layout

```
src/        db.py (dispatcher), todo.py, note.py
install/    install.sh, shell.zsh
```

Adding a tool: drop a module in `src/` and wire one line into `db.py`.
