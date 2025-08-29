# Configuration Quickstart

- Default config path: `~/.localagent/config.yaml` (managed by `localagent init`).
- Example file: `config/example.localagent.yaml` in this repo.

## Basic Steps
- Start Ollama and keep it at `http://localhost:11434`.
- Copy the example: `cp config/example.localagent.yaml ~/.localagent/config.yaml`.
- Set API keys via environment variables (preferred) before running the CLI:
  - `export OPENAI_API_KEY=...`
  - `export GEMINI_API_KEY=...`
  - `export PERPLEXITY_API_KEY=...`

## Enabling the Example Provider (Foo)
- Set in config: `foo.enabled: true` and optional `foo.default_model`.
- The provider is already wired in `ProviderManager` and activates when `foo.enabled` is true.
- Optional: add `foo` to `fallback_order` in your config.

## Validate
- `localagent providers` to list and check health.
- `localagent models --provider ollama` to verify connectivity.
- `make pre-commit` to run local checks before opening a PR.
