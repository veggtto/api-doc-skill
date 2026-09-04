#!/usr/bin/env bash
# 把仓库挂到 ~/.claude/skills/api-doc
# 优先符号链接（改仓库即生效）；失败就退回复制。
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="$HOME/.claude/skills/api-doc"

mkdir -p "$(dirname "$target")"

if [ -L "$target" ]; then
    echo "已存在符号链接，先移除：$target"
    rm "$target"
elif [ -e "$target" ]; then
    backup="$target.bak-$(date +%Y%m%d%H%M%S)"
    echo "已存在实体目录，备份到：$backup"
    mv "$target" "$backup"
fi

if ln -s "$repo" "$target" 2>/dev/null; then
    echo "✔ 已建符号链接：$target -> $repo"
    echo "  改仓库即生效，不用重装。"
else
    echo "建符号链接失败，改用复制。"
    mkdir -p "$target"
    cp "$repo/SKILL.md" "$target/"
    cp -r "$repo/assets" "$target/"
    echo "✔ 已复制到：$target"
    echo "  注意：改完仓库要重新跑一次本脚本。"
fi

echo
echo "在 Claude Code 里用 /api-doc 调用。"
