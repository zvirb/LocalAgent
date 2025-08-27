# LocalAgent CLI Usage Guide

## Available Commands

### `cli` - Simple Interactive Chat
Basic chat interface with Ollama models.

```bash
cli
```

Features:
- Direct chat with Ollama models
- Model switching
- Simple and fast

### `clix` - Full-Featured Interactive CLI
Enhanced CLI with orchestration and tools support.

```bash
clix
```

Features:
- Chat with Ollama models
- Lazy-loaded advanced features (type `init` to activate)
- Workflow engine integration (when initialized)
- File search and operations tools
- Configuration management

## Commands in `clix`

| Command | Description |
|---------|-------------|
| `help` | Show available commands and status |
| `init` | Initialize advanced features (workflow, tools) |
| `model` | Switch between available models |
| `config` | Show current configuration |
| `search [query]` | Search files (requires init) |
| `workflow [task]` | Execute workflow (requires init) |
| `clear` | Clear screen |
| `exit/quit/bye` | Exit the CLI |

## Usage Examples

### Basic Chat
```bash
clix
# Select model when prompted
You> Hello, how are you?
# Get response from model
```

### With Advanced Features
```bash
clix
You> init
# Initializes workflow engine and tools
You> search authentication
# Opens search interface
You> workflow fix the login bug
# Executes workflow (stub implementation for now)
```

## Architecture

The fixed CLI uses:
- **Lazy Loading**: Components load only when needed
- **Error Tolerance**: Missing components don't crash the CLI
- **Progressive Enhancement**: Start basic, add features on demand
- **Async/Await**: Proper handling of async operations

## Troubleshooting

1. **"Could not connect to Ollama"**: Ensure Docker is running:
   ```bash
   docker-compose up -d
   ```

2. **"No models installed"**: Install a model:
   ```bash
   docker exec localagent-ollama ollama pull tinyllama:latest
   ```

3. **"Configuration not loaded"**: Type `init` to initialize features

4. **Import errors**: Ensure virtual environment is activated:
   ```bash
   source .venv/bin/activate
   ```