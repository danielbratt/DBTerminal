# DBTerminal shell configuration

# --- History ---
HISTSIZE=10000
SAVEHIST=10000
HISTFILE=~/.zsh_history
setopt HIST_IGNORE_DUPS
setopt SHARE_HISTORY

# --- Options ---
setopt AUTO_CD
setopt INTERACTIVE_COMMENTS

# --- History substring search ---
autoload -U up-line-or-beginning-search down-line-or-beginning-search
zle -N up-line-or-beginning-search
zle -N down-line-or-beginning-search
bindkey "^[[A" up-line-or-beginning-search
bindkey "^[[B" down-line-or-beginning-search

# --- Completion ---
autoload -U compinit && compinit
zstyle ':completion:*' menu select
zstyle ':completion:*' matcher-list 'm:{a-z}={A-Z}'

# --- Prompt (dir + git branch) ---
autoload -Uz vcs_info
zstyle ':vcs_info:git:*' formats ' (%b)'
precmd() { vcs_info }
setopt PROMPT_SUBST
PROMPT='%B%F{white}%1~%f%b%F{magenta}${vcs_info_msg_0_}%f %F{white}❯%f '

# --- Git helper functions (used by the aliases below) ---
function git_current_branch() {
  local ref
  ref=$(command git symbolic-ref --quiet HEAD 2>/dev/null)
  local ret=$?
  if [[ $ret != 0 ]]; then
    [[ $ret == 128 ]] && return
    ref=$(command git rev-parse --short HEAD 2>/dev/null) || return
  fi
  echo ${ref#refs/heads/}
}

function git_main_branch() {
  command git rev-parse --git-dir &>/dev/null || return
  local ref
  for ref in refs/heads/main refs/heads/master refs/remotes/origin/main refs/remotes/origin/master; do
    if command git show-ref -q --verify $ref; then
      echo ${ref:t}
      return 0
    fi
  done
  echo main
}

# --- Git aliases (lean core; OMZ naming kept for muscle memory) ---
alias g='git'

# status / staging
alias gst='git status'
alias gss='git status --short --branch'
alias ga='git add'
alias gaa='git add --all'
alias gap='git add --patch'

# commit
alias gc='git commit --verbose'
alias gca='git commit --verbose --all'
alias gcmsg='git commit --message'
alias gcam='git commit --all --message'

# branch / checkout / switch
alias gb='git branch'
alias gbd='git branch --delete'
alias gco='git checkout'
alias gcb='git checkout -b'
alias gcm='git checkout $(git_main_branch)'
alias gsw='git switch'
alias gswc='git switch --create'

# diff / log / show
alias gd='git diff'
alias gds='git diff --staged'
alias glo='git log --oneline --decorate --graph'
alias gloa='git log --oneline --decorate --graph --all'
alias gsh='git show'

# fetch / pull / push
alias gf='git fetch'
alias gl='git pull'
alias gp='git push'
alias gpf='git push --force-with-lease'
alias ggpush='git push origin "$(git_current_branch)"'
alias ggpull='git pull origin "$(git_current_branch)"'

# rebase / merge / reset / restore
alias grb='git rebase'
alias grbi='git rebase --interactive'
alias gm='git merge'
alias grh='git reset'
alias grhh='git reset --hard'
alias grs='git restore'
alias grst='git restore --staged'

# stash
alias gsta='git stash push'
alias gstp='git stash pop'
alias gstl='git stash list'
