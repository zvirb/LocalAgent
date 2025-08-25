# LocalAgent - Multi-Provider LLM Orchestration CLI

A powerful, Claude Code-compatible CLI that provides unified access to multiple LLM providers including Ollama (local), OpenAI, Google Gemini, and Perplexity.

## Features

- **Multi-Provider Support**: Seamlessly switch between Ollama, OpenAI, Gemini, and Perplexity
- **Local-First Design**: Defaults to Ollama for privacy and cost-efficiency
- **Claude Code Compatible**: Familiar interface and workflow patterns
- **12-Phase Unified Workflow**: Advanced orchestration system from UnifiedWorkflow
- **Streaming Responses**: Real-time output with rich terminal formatting
- **Automatic Fallback**: Intelligent provider failover on errors
- **API Key Management**: Secure credential storage with OS keyring integration

## Installation

```bash
# Clone the repository
git clone https://github.com/zvirb/LocalAgent.git
cd LocalAgent

# Install dependencies
pip install -r requirements.txt

# Make CLI executable
chmod +x scripts/localagent

# Add to PATH (optional)
ln -s $(pwd)/scripts/localagent /usr/local/bin/localagent
```

## Quick Start

### 1. Initialize Configuration

```bash
localagent init
```

This will guide you through setting up:
- Ollama server URL (default: http://localhost:11434)
- OpenAI API key (optional)
- Google Gemini API key (optional)
- Perplexity API key (optional)

### 2. Start Ollama Server

If using Ollama (recommended for local execution):

```bash
# Install Ollama if not already installed
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama server
ollama serve

# Pull a model
ollama pull llama3.2
```

### 3. Use LocalAgent

#### Interactive Mode (Default)
```bash
localagent
```

#### Direct Completion
```bash
localagent complete "Explain quantum computing" --provider ollama
```

#### Check Provider Status
```bash
localagent providers
```

## Available Commands

- `localagent` - Launch interactive chat mode
- `localagent init` - Initialize configuration
- `localagent providers` - List provider status
- `localagent complete <prompt>` - Generate completion
- `localagent models --provider <name>` - List available models

## Interactive Mode Commands

- `/help` - Show available commands
- `/provider <name>` - Switch active provider
- `/models` - List models for current provider
- `/clear` - Clear screen
- `/exit` - Exit interactive mode

## Provider Configuration

### Ollama (Local)
- No API key required
- Runs entirely on your machine
- Supports all Ollama models

### OpenAI
- Requires API key from https://platform.openai.com
- Supports GPT-4o, GPT-4-turbo, GPT-3.5-turbo
- Includes cost tracking

### Google Gemini
- Requires API key from Google AI Studio
- Supports Gemini Pro and Flash models
- Large context windows (up to 1M tokens)

### Perplexity
- Requires API key from Perplexity
- Provides search-grounded responses
- Includes citations and sources

## Architecture

LocalAgent is built on the UnifiedWorkflow orchestration system, providing:

- **40+ Specialized Agents**: Domain-specific capabilities
- **12-Phase Workflow**: Comprehensive task execution pipeline
- **Parallel Execution**: Multi-stream coordination
- **Context Management**: Sophisticated token optimization
- **MCP Integration**: Memory and coordination servers

## Development

### Project Structure
```
LocalAgent/
├── app/
│   └── llm_providers/      # Provider implementations
├── agents/                 # Agent definitions (from UnifiedWorkflow)
├── workflows/              # Workflow configurations
├── scripts/
│   └── localagent         # CLI entry point
├── config/                # Configuration templates
└── docs/                  # Documentation
```

### Adding a New Provider

1. Create provider class inheriting from `BaseProvider`
2. Implement required methods (initialize, complete, stream_complete, etc.)
3. Register in `ProviderManager`
4. Update CLI configuration options

## Security

- API keys stored securely using OS keyring when available
- Fallback to encrypted file storage with master password
- Environment variable support for CI/CD
- No credentials stored in plain text

## License

MIT License - See LICENSE file for details

## Acknowledgments

Built on the UnifiedWorkflow orchestration framework, incorporating best practices from Claude Code CLI and modern LLM integration patterns.