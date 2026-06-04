# g-skills

Claude Code skills collection.

## Skills

| Skill | Description |
|-------|-------------|
| [hr-backlog-updater](hr-backlog-updater/) | Mirror Jira (CAB + linked FI) state into an Excel HR backlog file and publish it to Confluence — skip-statuses, FI changelog history, planned vs actual dates |
| [jira-create-task](jira-create-task/) | Create Jira issues from free-form input via MCP tools |
| [send-to-confluence](send-to-confluence/) | Create Confluence articles from files or text, with PDF image extraction |
| [daily-news-digest](daily-news-digest/) | Daily news digest for Russia & world with fact-checking — compact Telegram-friendly format |
| [chestny-znak-monitoring-report](chestny-znak-monitoring-report/) | Регулярный мониторинг новостей и нормативных изменений по маркировке «Честный ЗНАК» в России с подготовкой PDF-отчета |

## Installation

### Option 1: Copy skill to your user directory

Download the skill and place it into `~/.claude/skills/` — it will be available in all your projects:

```bash
# Example: install send-to-confluence
SKILL=send-to-confluence
mkdir -p ~/.claude/skills/$SKILL
curl -fsSL https://raw.githubusercontent.com/gihar/g-skills/main/$SKILL/SKILL.md \
  -o ~/.claude/skills/$SKILL/SKILL.md
```

Usage: `/<skill-name>` in any Claude Code session (e.g. `/send-to-confluence`).

### Option 2: Add to a specific project

Clone into your project's `.claude/skills/` directory — the skill will be available only in that project and can be shared with your team via git:

```bash
SKILL=send-to-confluence
mkdir -p .claude/skills/$SKILL
curl -fsSL https://raw.githubusercontent.com/gihar/g-skills/main/$SKILL/SKILL.md \
  -o .claude/skills/$SKILL/SKILL.md
```

### Option 3: Clone the whole repo

```bash
git clone https://github.com/gihar/g-skills.git
```

Then symlink or copy the skills you need:

```bash
# User-level (all projects)
ln -s "$(pwd)/g-skills/send-to-confluence" ~/.claude/skills/send-to-confluence

# Project-level (this project only)
ln -s "$(pwd)/g-skills/send-to-confluence" .claude/skills/send-to-confluence
```

## Prerequisites

Each skill lists its own prerequisites in `SKILL.md`. Common requirements:

- [mcp-atlassian](https://github.com/sooperset/mcp-atlassian) MCP server configured
- Atlassian (Claude AI connector) MCP server enabled in Claude Code
- `send-to-confluence` also requires `pdfimages` (part of [poppler](https://poppler.freedesktop.org/)) for PDF image extraction: `brew install poppler`
- `hr-backlog-updater` requires Python 3.10+ and [openpyxl](https://openpyxl.readthedocs.io/): `pip install openpyxl`. The skill bundles helper scripts under `hr-backlog-updater/scripts/` — copy the whole directory (not just `SKILL.md`) when installing this one.

## Structure

```
g-skills/
├── README.md
└── <skill-name>/
    └── SKILL.md
```

Each skill is a directory containing a `SKILL.md` file with frontmatter and instructions that Claude Code loads automatically.
