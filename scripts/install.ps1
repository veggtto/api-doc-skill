# 把仓库挂到 ~/.claude/skills/api-doc
# 优先符号链接（改仓库即生效）；没权限就退回复制。
#
# 注意：本文件必须存成 UTF-8 with BOM。
# Windows PowerShell 5.1 对无 BOM 的 UTF-8 按 ANSI 解码，中文注释会乱码，
# 乱码后引号配对错乱，整个脚本直接解析失败。
$ErrorActionPreference = 'Stop'

$repo      = Split-Path -Parent $PSScriptRoot
$claudeDir = Join-Path $env:USERPROFILE '.claude'
$skillsDir = Join-Path $claudeDir 'skills'
$target    = Join-Path $skillsDir 'api-doc'

if (-not (Test-Path $skillsDir)) {
    New-Item -ItemType Directory -Path $skillsDir -Force | Out-Null
}

if (Test-Path $target) {
    $item = Get-Item $target -Force
    if ($item.LinkType -eq 'SymbolicLink') {
        Write-Host "已存在符号链接，先移除：$target"
        $item.Delete()
    } else {
        # 备份必须挪出 skills/：留在里面的目录带着 SKILL.md，
        # 会被 Claude Code 当成第二个同名技能注册。
        $backupDir = Join-Path $claudeDir 'skills-backup'
        $stamp     = Get-Date -Format 'yyyyMMddHHmmss'
        $backup    = Join-Path $backupDir ('api-doc-' + $stamp)
        New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
        Write-Host "已存在实体目录，备份到：$backup"
        Move-Item $target $backup
    }
}

try {
    New-Item -ItemType SymbolicLink -Path $target -Target $repo -ErrorAction Stop | Out-Null
    Write-Host "OK 已建符号链接：$target -> $repo"
    Write-Host "   改仓库即生效，不用重装。"
} catch {
    Write-Host "建符号链接失败（需要管理员或开发者模式），改用复制。"
    New-Item -ItemType Directory -Path $target -Force | Out-Null
    Copy-Item (Join-Path $repo 'SKILL.md') $target -Force
    Copy-Item (Join-Path $repo 'assets')   $target -Recurse -Force
    Write-Host "OK 已复制到：$target"
    Write-Host "   注意：改完仓库要重新跑一次本脚本。"
}

Write-Host ""
Write-Host "在 Claude Code 里用 /api-doc 调用。"
