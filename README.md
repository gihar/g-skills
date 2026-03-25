# g-skills

Claude Code skills collection.

## Skills

| Skill | Description |
|-------|-------------|
| [jira-create-task](jira-create-task/) | Create Jira issues from free-form input via MCP tools |

## Installation

### Option 1: Copy skill to your user directory

Download the skill and place it into `~/.claude/skills/` — it will be available in all your projects:

```bash
mkdir -p ~/.claude/skills/jira-create-task
curl -fsSL https://raw.githubusercontent.com/gihar/g-skills/main/jira-create-task/SKILL.md \
  -o ~/.claude/skills/jira-create-task/SKILL.md
```

Usage: `/jira-create-task` in any Claude Code session.

### Option 2: Add to a specific project

Clone into your project's `.claude/skills/` directory — the skill will be available only in that project and can be shared with your team via git:

```bash
mkdir -p .claude/skills/jira-create-task
curl -fsSL https://raw.githubusercontent.com/gihar/g-skills/main/jira-create-task/SKILL.md \
  -o .claude/skills/jira-create-task/SKILL.md
```

### Option 3: Clone the whole repo

```bash
git clone https://github.com/gihar/g-skills.git
```

Then symlink or copy the skills you need:

```bash
# User-level (all projects)
ln -s "$(pwd)/g-skills/jira-create-task" ~/.claude/skills/jira-create-task

# Project-level (this project only)
ln -s "$(pwd)/g-skills/jira-create-task" .claude/skills/jira-create-task
```

## Prerequisites

Each skill lists its own prerequisites in `SKILL.md`. For `jira-create-task` you need:

- [mcp-atlassian](https://github.com/sooperset/mcp-atlassian) MCP server configured
- Atlassian (Claude AI connector) MCP server enabled in Claude Code

## Structure

```
g-skills/
├── README.md
└── <skill-name>/
    └── SKILL.md
```

Each skill is a directory containing a `SKILL.md` file with frontmatter and instructions that Claude Code loads automatically.
