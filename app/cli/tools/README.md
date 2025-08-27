# LocalAgent CLI Tools

Modern search and file manipulation utilities with rich interfaces, fuzzy matching, and batch operations.

## Features

### 🔍 Advanced Search (`search.py`)

- **Fuzzy Matching**: Intelligent fuzzy search similar to fzf
- **Ripgrep Integration**: High-performance content search using ripgrep
- **Multiple Search Types**: Content, file names, directories, or mixed
- **Rich Display**: Beautiful results with syntax highlighting
- **Interactive Mode**: InquirerPy-powered interactive search
- **Pattern Filtering**: Include/exclude patterns with glob support
- **Context Lines**: Show surrounding lines for content matches

### 📁 Batch File Operations (`file_ops.py`)

- **Copy/Move/Rename**: Batch file operations with progress bars
- **Smart Organization**: Organize by extension, date, size, or MIME type
- **Compression**: ZIP, TAR, GZIP support with multiple formats
- **Batch Rename**: Pattern-based renaming with placeholders
- **Duplicate Detection**: Find and remove duplicate files
- **Dry Run Mode**: Preview changes before execution
- **Rich Progress**: Beautiful progress bars and summaries

### 🎯 CLI Integration (`commands.py`)

- **Typer Integration**: Modern CLI with rich help and validation
- **Interactive Commands**: Full interactive mode for complex operations
- **Direct Commands**: Quick command-line access for scripting
- **History Tracking**: Operation history and repeat functionality

## Installation

The tools are part of the LocalAgent CLI and require these dependencies:

```bash
# Core dependencies (already in requirements.txt)
pip install typer[all] rich inquirerpy aiofiles

# Optional but recommended
sudo apt install ripgrep  # or: brew install ripgrep
```

## Usage

### Search Commands

```bash
# Interactive search mode
localagent tools search

# Direct content search with fuzzy matching
localagent tools search "function" --content --fuzzy

# Search file names
localagent tools search "*.py" --files --include="src/**"

# Search with exclusions and limits
localagent tools search "TODO" --exclude="node_modules,*.log" --max=50

# Regex search with context
localagent tools search "def \w+\(" --regex --context=3
```

### File Operations

```bash
# Interactive file operations
localagent tools file-ops

# Copy files with pattern
localagent tools file-ops copy --source="*.py" --dest="backup/"

# Organize files by extension
localagent tools organize "downloads/*" --strategy=extension --dest="sorted/"

# Batch rename with patterns
localagent tools batch-rename "*.jpg" --pattern="photo_{counter}_{date}"

# Compress files
localagent tools compress "documents/*.pdf" --format=zip --output="docs.zip"

# Dry run mode (preview changes)
localagent tools file-ops move --source="*.log" --dest="logs/" --dry-run
```

### Organization Strategies

```bash
# Organize by file extension
localagent tools organize "messy_folder/*" --strategy=extension

# Organize by modification date (YYYY/MM structure)
localagent tools organize "photos/*" --strategy=date

# Organize by file size (small/medium/large)
localagent tools organize "downloads/*" --strategy=size

# Organize by MIME type (image/document/video etc.)
localagent tools organize "files/*" --strategy=mime_type
```

## Interactive Mode Examples

### Search Interactive Mode

When you run `localagent tools search` without arguments, you'll get:

```
🔍 LocalAgent Advanced Search

? Enter search query: function
? Select search type: Search in file contents
? Select matching algorithm: Fuzzy matching (recommended)
? Search paths (comma-separated, empty for current dir): src/
? Include patterns (comma-separated, e.g., "*.py,*.js"): *.py,*.js
? Exclude patterns (comma-separated): __pycache__,*.pyc,node_modules
? Maximum results: 100

Searching content with ripgrep...
Found 15 matches for 'function'

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ File                         ┃ Match                          ┃ Confidence ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ src/utils.py                 │ def helper_function():         │ 1.00       │
│ src/main.py                  │ function process_data():       │ 0.95       │
└──────────────────────────────┴────────────────────────────────┴────────────┘
```

### File Operations Interactive Mode

When you run `localagent tools file-ops` without arguments:

```
🗂️  LocalAgent File Operations

? Select file operation: Organize files
? Source patterns: downloads/*
? Perform dry run first? Yes

? Organization strategy: By file extension
? Base organization directory: organized

Dry run: Would process 156 files

Files that would be processed:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ File                      ┃ Size     ┃ Modified         ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ downloads/document.pdf    │ 2.3 MB   │ 2024-01-15 14:30 │
│ downloads/photo.jpg       │ 856.2 KB │ 2024-01-14 09:15 │
└───────────────────────────┴──────────┴──────────────────┘

Proceed with operation? [y/N]: y
```

## Advanced Features

### Pattern-Based Batch Renaming

Use these placeholders in rename patterns:

- `{name}` - Original filename without extension
- `{ext}` - File extension  
- `{counter}` - Sequential counter (001, 002, etc.)
- `{date}` - Current date (YYYYMMDD)
- `{time}` - Current time (HHMMSS)

Examples:
```bash
# Rename photos with counter
localagent tools batch-rename "*.jpg" --pattern="vacation_{counter}"

# Add date prefix to documents
localagent tools batch-rename "*.pdf" --pattern="{date}_{name}"

# Timestamp all files
localagent tools batch-rename "*" --pattern="{name}_{date}_{time}"
```

### Search with Complex Patterns

```bash
# Find function definitions in Python files
localagent tools search "def \w+\(" --regex --include="*.py"

# Find TODO comments across the project
localagent tools search "TODO|FIXME|XXX" --regex --exclude="node_modules"

# Find large files by name pattern
localagent tools search "*" --files --include="*.zip,*.tar,*.gz"
```

### File Organization Strategies

#### By Extension
Creates folders like: `txt/`, `pdf/`, `jpg/`, `no_extension/`

#### By Date
Creates structure like: `2024/01/`, `2024/02/`, `2023/12/`

#### By Size
Creates folders: `small/` (< 1MB), `medium/` (< 100MB), `large/` (> 100MB)

#### By MIME Type
Creates folders: `image/`, `document/`, `video/`, `audio/`, `unknown/`

## Error Handling and Safety

### Dry Run Mode
Always use `--dry-run` first to preview changes:

```bash
# Preview organization
localagent tools organize "messy/*" --strategy=extension --dry-run

# Preview batch rename
localagent tools batch-rename "*.txt" --pattern="doc_{counter}" --dry-run
```

### Backup Options
For destructive operations, enable backups:

```bash
# Delete with backup
localagent tools file-ops delete --source="*.tmp" --backup

# Move with overwrite protection
localagent tools file-ops move --source="*.log" --dest="archive/" --no-overwrite
```

### Error Recovery
- Operations are atomic where possible
- Failed operations don't affect successful ones
- Detailed error reporting with file-specific failures
- Operation history for debugging

## Performance

### Search Performance
- Ripgrep integration provides sub-second search on large codebases
- Fallback pure-Python search when ripgrep unavailable
- Configurable result limits and context lines
- Efficient file filtering with glob patterns

### File Operations Performance
- Async I/O for better performance on large files
- Progress bars with transfer speeds and time remaining
- Chunked processing for memory efficiency
- Parallel processing where safe

## Testing

Run the built-in test suite:

```bash
cd app/cli/tools
python test_tools.py
```

This will:
1. Check all dependencies
2. Create test files and directory structure
3. Test search functionality with various patterns
4. Test file operations in dry-run mode
5. Validate integration with CLI commands

## Architecture

### Search Architecture (`search.py`)
- `SearchManager`: High-level search coordination
- `RipgrepIntegrator`: High-performance content search
- `FuzzyFileMatcher`: File name fuzzy matching
- `SearchContext`: Configuration and parameters
- `SearchResult`: Rich result metadata

### File Operations Architecture (`file_ops.py`)
- `FileOperationsManager`: Interactive operations interface
- `FileProcessor`: Core file operation engine
- `OperationContext`: Operation configuration
- `FileOperationResult`: Operation results and metadata

### CLI Integration (`commands.py`)
- Typer-based command structure
- Rich display integration
- Interactive and direct modes
- History and preset management

## Contributing

When adding new features:

1. Follow the existing async/await patterns
2. Use Rich for all display output
3. Support both interactive and direct CLI modes
4. Add comprehensive error handling
5. Include dry-run support for destructive operations
6. Update tests and documentation

## Troubleshooting

### Ripgrep Not Found
If you get "ripgrep not found" errors:

```bash
# Ubuntu/Debian
sudo apt install ripgrep

# macOS
brew install ripgrep

# Or use the fallback Python search (slower)
localagent tools search "query" --no-ripgrep
```

### Permission Errors
For permission issues:

```bash
# Check file permissions
ls -la problematic_file

# Use with elevated permissions if needed
sudo localagent tools file-ops move --source="system_files/*" --dest="/opt/backup/"
```

### Large File Performance
For operations on many large files:

```bash
# Use smaller batch sizes
localagent tools file-ops copy --source="*.iso" --dest="backup/" --batch-size=10

# Monitor with progress bars
localagent tools compress "large_files/*" --format=tar.gz --progress
```

This comprehensive toolset provides powerful search and file manipulation capabilities while maintaining ease of use through rich interactive interfaces.