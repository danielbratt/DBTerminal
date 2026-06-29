#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
SRC_DIR="$ROOT_DIR/src"
ZSHRC="$HOME/.zshrc"

echo "Installing DBTerminal..."
echo ""

# --- Make scripts executable ---
chmod +x "$SRC_DIR/db.py" "$SRC_DIR/todo.py" "$SRC_DIR/note.py"
echo "✓ Scripts marked executable"

# --- Hook into .zshrc (idempotent; never overwrites existing config) ---
MARKER="# >>> DBTerminal >>>"
if grep -qF "$MARKER" "$ZSHRC" 2>/dev/null; then
    echo "✓ ~/.zshrc already configured"
else
    echo "Appending DBTerminal block to ~/.zshrc..."
    cat >> "$ZSHRC" << EOF

$MARKER
export PATH="\$HOME/.local/bin:\$PATH"
source "$SCRIPT_DIR/shell.zsh"
alias db='$SRC_DIR/db.py'
# <<< DBTerminal <<<
EOF
    echo "✓ ~/.zshrc updated"
fi

echo ""
echo "Done! Run 'source ~/.zshrc' to apply changes."
echo ""
echo "Shell features:"
echo "  • Prompt shows current dir + git branch"
echo "  • Type directory names without cd"
echo "  • Git aliases: gs, ga, gco, gp, gl, gd ..."
echo ""
echo "DBTerminal commands:"
echo "  db todo add <task>"
echo "  db note add <path> [text]"
