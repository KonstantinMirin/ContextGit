# Watch Mode Example

This example demonstrates how to use the `contextgit watch` command for real-time requirements traceability during active development.

## Prerequisites

Install contextgit with watch mode support:

```bash
pip install contextgit[watch]
```

Or if you have contextgit installed already:

```bash
pip install watchdog>=3.0.0
```

## Basic Usage

### Watch the Entire Repository

Navigate to your contextgit repository and run:

```bash
contextgit watch
```

Output:
```
🔍 Watching: .
Press Ctrl+C to stop
```

Now when you modify any supported file (.md, .py, .js, .ts, etc.), it will automatically be scanned:

```
[14:23:45] Modified: docs/requirements.md
           Scanned 1 files
           Added: 0 nodes
           Updated: 1 nodes

[14:24:10] Modified: src/api.py
           Scanned 1 files
           Added: 1 nodes
           Updated: 0 nodes
```

### Watch Specific Directories

Watch only certain directories:

```bash
contextgit watch docs/ src/
```

Output:
```
🔍 Watching: docs/, src/
Press Ctrl+C to stop
```

## Advanced Usage

### Adjust Debounce Delay

If your editor saves files rapidly or your system is slow, increase the debounce delay:

```bash
contextgit watch --debounce 1000
```

This groups file changes within a 1-second window into a single scan operation.

### JSON Output

For programmatic consumption or integration with other tools:

```bash
contextgit watch --format json
```

Output:
```json
{"status": "watching", "paths": ["/path/to/repo"], "debounce_ms": 500}

{
  "timestamp": "14:23:45",
  "files": ["docs/requirements.md"],
  "scan_result": {
    "files_scanned": 1,
    "nodes_added": 0,
    "nodes_updated": 1,
    "errors": []
  }
}
```

## Use Cases

### 1. Active Development

Keep watch mode running in a terminal while you work. Every time you save a file with contextgit metadata, the index is automatically updated.

```bash
# Terminal 1: Watch mode
contextgit watch

# Terminal 2: Your editor/IDE
# Edit files, save changes
# Watch mode automatically picks them up
```

### 2. Documentation Writing

When writing requirements documents, keep watch mode running to ensure all changes are immediately reflected:

```bash
# Watch only docs directory
contextgit watch docs/ --debounce 1000

# Now edit your Markdown files
# Each save updates the requirements index
```

### 3. Code and Requirements Sync

Watch both code and documentation directories to maintain synchronization:

```bash
contextgit watch docs/ src/ tests/
```

### 4. CI/CD Integration

While less common, you could use watch mode in a development container:

```bash
# In docker-compose.yml or dev container
contextgit watch --format json | tee watch.log
```

## Ignored Files

The following patterns are automatically ignored:

- `*.pyc`, `*.pyo` - Python bytecode
- `__pycache__/*` - Python cache directories
- `.git/*` - Git directory
- `.contextgit/*` - ContextGit directory
- `node_modules/*` - Node.js dependencies
- `.venv/*`, `venv/*` - Python virtual environments
- `*.egg-info/*` - Python package metadata
- `.pytest_cache/*` - Pytest cache
- `*.swp`, `*.swo`, `*~` - Editor temporary files

## Error Handling

If a file has invalid metadata or scanning fails, watch mode continues:

```
[14:25:30] Modified: docs/bad_file.md
           Error scanning files: Invalid metadata format

[14:25:45] Modified: docs/good_file.md
           Scanned 1 files
           Added: 0 nodes
           Updated: 1 nodes
```

## Performance Tips

1. **Watch Specific Directories**: Instead of watching the entire repo, watch only relevant directories
2. **Increase Debounce**: If you have a slow system or aggressive auto-save, increase debounce delay
3. **Check File System Limits**: On Linux, you may need to increase `fs.inotify.max_user_watches`:
   ```bash
   sudo sysctl fs.inotify.max_user_watches=524288
   ```

## Stopping Watch Mode

Press `Ctrl+C` to gracefully stop watching:

```
^C
Stopping watch mode...
```

## Troubleshooting

### "Watch mode requires the 'watchdog' package"

Install the watchdog package:

```bash
pip install contextgit[watch]
# or
pip install watchdog>=3.0.0
```

### "Path does not exist: /some/path"

Make sure the path you're trying to watch exists:

```bash
ls -la /some/path
```

### Files Not Being Detected

1. Check the file extension is supported (.md, .py, .js, .ts, etc.)
2. Verify the file is not in an ignored directory
3. Make sure the file is within the repository

### High CPU Usage

1. Reduce the number of directories being watched
2. Increase the debounce delay
3. Check for recursive directory structures or symlink loops

## Integration with Your Workflow

### VS Code

Add a task to `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "ContextGit Watch",
      "type": "shell",
      "command": "contextgit watch",
      "isBackground": true,
      "problemMatcher": []
    }
  ]
}
```

Then run with `Ctrl+Shift+P` → "Tasks: Run Task" → "ContextGit Watch"

### Tmux/Screen

Create a dedicated pane for watch mode:

```bash
# In tmux
tmux split-window -h 'contextgit watch'

# Or create a session
tmux new-session -d -s contextgit-watch 'contextgit watch'
```

## Example Session

```bash
# Initialize a new project
mkdir my-project && cd my-project
contextgit init

# Start watch mode
contextgit watch &

# Create a requirements file
cat > docs/requirements.md << 'EOF'
---
id: BR-001
type: business
title: User Authentication
status: active
---

Users must be able to log in with email and password.
EOF

# Watch mode automatically detects the change:
# [14:30:15] Modified: docs/requirements.md
#            Scanned 1 files
#            Added: 1 nodes
#            Updated: 0 nodes

# Check the status
contextgit status

# Output shows BR-001 is now in the index
```

## Conclusion

Watch mode is a powerful feature for maintaining real-time requirements traceability. It eliminates the need to manually run `contextgit scan` after every change, making it ideal for active development workflows.
