# LocalAgent CLI Autocomplete Implementation Guide

## Overview

The LocalAgent CLI now features an advanced autocomplete system that provides intelligent command suggestions based on:
- **Command history** with secure storage
- **ML-enhanced predictions** using TensorFlow.js models
- **Fuzzy matching** for typo tolerance
- **Context-aware filtering** based on workflow phase, provider, and directory
- **Real-time keyboard navigation** with Tab completion

## Architecture

### Core Components

```
app/cli/intelligence/
├── autocomplete_history.py      # Secure history storage and retrieval
├── command_intelligence.py      # Enhanced with autocomplete integration
└── autocomplete_prompt.py       # Interactive UI component
```

### 1. Autocomplete History Manager (`autocomplete_history.py`)

**Features:**
- **Secure Storage**: Optional AES-256 encryption for command history
- **Privacy Controls**: Automatic sanitization of sensitive data (API keys, passwords)
- **Intelligent Deduplication**: Prevents suggesting recently used commands
- **Context Awareness**: Boosts suggestions based on working directory and provider
- **Performance Optimized**: < 16ms response time for suggestions

**Configuration:**
```python
from app.cli.intelligence.autocomplete_history import AutocompleteConfig

config = AutocompleteConfig(
    max_history_size=10000,           # Maximum commands to store
    max_suggestions=10,               # Max suggestions to return
    enable_fuzzy=True,               # Enable fuzzy matching
    fuzzy_threshold=0.6,             # Similarity threshold (0.0-1.0)
    enable_encryption=True,          # Encrypt history file
    history_retention_days=30,       # Auto-cleanup old entries
    deduplication_window=100         # Don't suggest last N commands
)
```

### 2. Command Intelligence Engine (Enhanced)

The existing `CommandIntelligenceEngine` now integrates autocomplete history:

```python
from app.cli.intelligence.command_intelligence import CommandIntelligenceEngine

# Initialize with autocomplete
engine = CommandIntelligenceEngine(
    behavior_tracker=behavior_tracker,
    model_manager=model_manager,
    autocomplete_config=config
)

# Record command execution
await engine.record_command_execution(
    command="git status",
    success=True,
    execution_time=0.5,
    provider="ollama"
)

# Get suggestions
suggestions = await engine.get_command_suggestions(
    partial_command="git",
    context=context,
    max_suggestions=10
)
```

### 3. Interactive Autocomplete Prompt (`autocomplete_prompt.py`)

**Features:**
- **Real-time suggestions** as you type
- **Keyboard navigation**:
  - `Tab`: Complete with selected suggestion
  - `↑/↓`: Navigate suggestions
  - `Enter`: Accept current input or suggestion
  - `Escape`: Hide suggestions or cancel
  - `Ctrl+W`: Delete word
  - `Ctrl+U/K`: Delete to beginning/end

**Usage:**
```python
from app.cli.ui.autocomplete_prompt import create_autocomplete_prompt

# Create prompt with intelligence
prompt = create_autocomplete_prompt(
    console=console,
    command_intelligence=intelligence_engine
)

# Get user input with autocomplete
result = await prompt.prompt_with_intelligence(
    context={'provider': 'ollama'},
    initial_text=""
)
```

## Integration Points

### 1. CLI Application (`app.py`)

The autocomplete system integrates with the main CLI application:

```python
# In LocalAgentApp initialization
self.command_intelligence = CommandIntelligenceEngine(
    behavior_tracker=self.behavior_tracker,
    model_manager=self.model_manager,
    config_dir=self.config_dir,
    autocomplete_config=AutocompleteConfig()
)

# Record commands after execution
await self.command_intelligence.record_command_execution(
    command=executed_command,
    success=result.success,
    execution_time=result.duration
)
```

### 2. Interactive Prompts (`enhanced_prompts.py`)

Enhanced prompts can use autocomplete:

```python
from app.cli.ui.autocomplete_prompt import EnhancedAutocompletePrompt

class ModernInteractivePrompts:
    def __init__(self, console, command_intelligence=None):
        self.autocomplete = EnhancedAutocompletePrompt(
            console=console,
            command_intelligence=command_intelligence
        )
    
    async def ask_command(self, prompt="Enter command"):
        return await self.autocomplete.prompt_with_intelligence()
```

### 3. Chat Interface (`chat.py`)

The chat interface can leverage autocomplete for command mode:

```python
# In chat session
if message.startswith('/'):
    # Use autocomplete for commands
    command = await self.autocomplete.prompt_with_intelligence(
        initial_text=message[1:]
    )
```

## Security Features

### 1. Sensitive Data Protection

The system automatically sanitizes sensitive patterns:
- API keys: `api_key=<REDACTED>`
- Passwords: `password=<REDACTED>`
- Tokens: `token=<REDACTED>`
- Secrets: `secret=<REDACTED>`

### 2. File Permissions

- History files: `600` (owner read/write only)
- Encryption key: `600` (owner read/write only)
- Config directory: `700` (owner full access only)

### 3. Encryption

When enabled, uses Fernet (AES-256) encryption:
```python
# Encrypted file location
~/.localagent/autocomplete_history.enc

# Key file (auto-generated)
~/.localagent/.autocomplete_key
```

## Performance Optimization

### 1. Response Time Targets

- **< 16ms**: Suggestion generation (60 FPS requirement)
- **< 50ms**: History search with fuzzy matching
- **< 100ms**: ML model inference

### 2. Caching Strategy

- **In-memory cache**: Recent suggestions cached for 5 minutes
- **LRU history**: Limited to 10,000 entries in memory
- **Lazy loading**: History loaded on first use

### 3. Optimization Techniques

- **Prefix indexing**: Fast prefix matching
- **Parallel search**: Multiple suggestion sources queried concurrently
- **Early termination**: Stop searching once enough suggestions found

## Usage Examples

### Basic Usage

```python
# Initialize in CLI
from app.cli.intelligence import CommandIntelligenceEngine
from app.cli.ui.autocomplete_prompt import create_autocomplete_prompt

# Create engine
intelligence = CommandIntelligenceEngine(
    behavior_tracker=tracker,
    model_manager=models
)

# Create prompt
prompt = create_autocomplete_prompt(
    console=console,
    command_intelligence=intelligence
)

# Get user input
command = await prompt.prompt_with_intelligence()

# Execute and record
result = execute_command(command)
await intelligence.record_command_execution(
    command=command,
    success=result.success
)
```

### Advanced Configuration

```python
# Custom autocomplete configuration
config = AutocompleteConfig(
    max_history_size=50000,
    enable_ml_predictions=True,
    sensitive_pattern_filters=[
        r'api[_-]?key',
        r'password',
        r'token',
        r'secret',
        r'ssh[_-]?key',
        r'private[_-]?key'
    ],
    history_retention_days=90
)

# Initialize with custom config
intelligence = CommandIntelligenceEngine(
    behavior_tracker=tracker,
    model_manager=models,
    autocomplete_config=config
)
```

### Context-Aware Suggestions

```python
# Provide context for better suggestions
context = CommandContext(
    current_directory="/project/backend",
    recent_commands=["cd backend", "npm install"],
    available_providers=["ollama", "openai"],
    workflow_phase="testing",
    user_skill_level="expert"
)

# Get contextual suggestions
suggestions = await intelligence.get_command_suggestions(
    partial_command="test",
    context=context
)
```

## Testing

Run the autocomplete test suite:

```bash
# Run all autocomplete tests
pytest tests/cli/test_autocomplete.py -v

# Run specific test categories
pytest tests/cli/test_autocomplete.py::TestAutocompleteHistory -v
pytest tests/cli/test_autocomplete.py::TestCommandIntelligence -v
pytest tests/cli/test_autocomplete.py::TestAutocompleteUI -v

# Run integration tests
pytest tests/cli/test_autocomplete.py -m integration -v
```

## Configuration

### User Configuration

Add to `~/.localagent/config.yaml`:

```yaml
autocomplete:
  enabled: true
  max_suggestions: 10
  enable_fuzzy: true
  fuzzy_threshold: 0.7
  enable_encryption: true
  history_retention_days: 30
  
  # Privacy settings
  sanitize_sensitive: true
  sensitive_patterns:
    - 'api_key'
    - 'password'
    - 'token'
    - 'secret'
```

### Environment Variables

```bash
# Enable/disable autocomplete
export LOCALAGENT_AUTOCOMPLETE_ENABLED=true

# Set history file location
export LOCALAGENT_AUTOCOMPLETE_HISTORY="$HOME/.localagent/history.enc"

# Disable encryption (not recommended)
export LOCALAGENT_AUTOCOMPLETE_ENCRYPT=false
```

## Troubleshooting

### Common Issues

1. **No suggestions appearing**
   - Check history file exists: `ls ~/.localagent/autocomplete_history.*`
   - Verify InquirerPy installed: `pip install inquirerpy`
   - Check readchar installed: `pip install readchar`

2. **Slow suggestion response**
   - Clear old history: `localagent autocomplete --clear-old 30`
   - Reduce fuzzy threshold: Set `fuzzy_threshold: 0.8`
   - Disable ML predictions if not needed

3. **Encrypted history issues**
   - Check key file permissions: `ls -la ~/.localagent/.autocomplete_key`
   - Regenerate key: Delete key file and restart
   - Disable encryption temporarily for debugging

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("AutocompleteHistory").setLevel(logging.DEBUG)
logging.getLogger("CommandIntelligenceEngine").setLevel(logging.DEBUG)
```

## API Reference

### AutocompleteHistoryManager

```python
class AutocompleteHistoryManager:
    def add_command(command: str, success: bool = True, ...) -> None
    def get_suggestions(partial: str, context: Dict = None) -> List[Tuple[str, float]]
    def save_history() -> None
    def load_history() -> None
    def clear_history(older_than_days: int = None) -> int
    def export_history(output_file: Path, format: str = 'json') -> None
    def get_statistics() -> Dict[str, Any]
```

### CommandIntelligenceEngine

```python
class CommandIntelligenceEngine:
    async def get_command_suggestions(partial: str, context: CommandContext) -> List[CommandSuggestion]
    async def record_command_execution(command: str, success: bool, ...) -> None
    def get_command_patterns(command: str) -> List[str]
```

### AutocompletePrompt

```python
class AutocompletePrompt:
    async def prompt_async(initial_text: str = "") -> Optional[str]
    def prompt(initial_text: str = "") -> Optional[str]
    
class EnhancedAutocompletePrompt(AutocompletePrompt):
    async def prompt_with_intelligence(context: Dict = None) -> Optional[str]
```

## Future Enhancements

### Planned Features

1. **Cloud Sync**: Sync command history across machines
2. **Team Sharing**: Share useful commands with team members
3. **Smart Aliases**: Auto-generate aliases for frequent command sequences
4. **Command Templates**: Parameterized command templates
5. **Natural Language**: Convert natural language to commands
6. **Command Validation**: Pre-execution validation and warnings
7. **Performance Analytics**: Track command execution patterns
8. **Plugin Commands**: Autocomplete for plugin-specific commands

### Contributing

To contribute to the autocomplete system:

1. Read the architecture documentation
2. Follow the existing patterns for suggestion sources
3. Maintain the < 16ms performance target
4. Add comprehensive tests
5. Update this documentation

## License

Part of LocalAgent CLI - see main LICENSE file.