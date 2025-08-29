# Repository Guidelines

## Project Structure & Module Organization
- `app/`: Core Python (CLI, providers, orchestration, security)
- `agents/`, `workflows/`: Agent specs and workflow configs
- `scripts/`: CLI entry (`scripts/localagent`), setup/deploy helpers
- `tests/`: Unit, integration, CLI, security, performance
- `docker/`, `docker-compose.yml`: Dev stack
- `config/`, `templates/`, `UnifiedWorkflow/`: Configs, templates, framework

## Build, Test, and Development Commands
- `make install`: Create venv and install deps
- `make test`: Run pytest suite
- `make test-cov`: Coverage report (`--cov=app`)
- `make lint`: `pylint` and `flake8`
- `make format`: `black` + `isort` on code
- `make type-check`: `mypy app/`
- `make pre-commit`: All checks must pass
- `make docker-up` / `make docker-down`: Start/stop stack

## Coding Style & Naming Conventions
- Python 3.11; 4 spaces; Black (88); isort (profile=black)
- Lint: `pylint`, `flake8`; types: `mypy` where practical
- Naming: modules `snake_case.py`, classes `PascalCase`, funcs/vars `snake_case`

## Testing Guidelines
- Use `pytest` (+ `pytest-asyncio`)
- Names: `test_*.py`, functions `test_*`, classes `Test*` (no `__init__`)
- Run: `make test` or `pytest -v`; coverage: `make test-cov`

## Commit & PR Workflow
- Commits: imperative title (≤72 chars); atomic; reference issues (`#123`)
- PRs: description, rationale, test plan; screenshots for UI changes
- CI: `.github/workflows/*` runs on PR; pass `make pre-commit` before opening

## Security & Configuration Tips
- Never commit secrets; use OS keyring or env vars
- Prefer local Ollama; document provider/API requirements
- For sensitive code, run `make security` (Bandit/Safety)

## Provider Extensions
- Add `app/llm_providers/<name>_provider.py` with `class <Name>Provider(BaseProvider)`
- Implement: `initialize`, `list_models`, `complete`, `stream_complete`, `health_check`
- Register in `ProviderManager.initialize_providers`; update `fallback_order` if needed
- Config: follow `config['<name>']` pattern; add tests under `tests/unit/`

### Scaffold Example
```python
# app/llm_providers/foo_provider.py
from .base_provider import BaseProvider, CompletionRequest, CompletionResponse, ModelInfo

class FooProvider(BaseProvider):
    async def initialize(self) -> bool: return True
    async def list_models(self):
        return [ModelInfo(name="foo-small", provider="foo", context_length=128000, capabilities=["chat"])]
    async def complete(self, r: CompletionRequest) -> CompletionResponse:
        return CompletionResponse(content="ok", model=r.model, provider="foo", usage={"prompt": 1, "completion": 1})
    async def health_check(self): return {"healthy": True}
```

- Register in `app/llm_providers/provider_manager.py`: `from .foo_provider import FooProvider`; then in `initialize_providers`: `self.providers['foo'] = FooProvider(self.config.get('foo', {}))`.

```python
# tests/unit/test_foo_provider.py
import pytest
from app.llm_providers.foo_provider import FooProvider
from app.llm_providers.base_provider import CompletionRequest

@pytest.mark.asyncio
async def test_complete():
    p = FooProvider({}); await p.initialize()
    resp = await p.complete(CompletionRequest(messages=[{"role":"user","content":"hi"}], model="foo-small"))
    assert resp.content and resp.provider == "foo"
```
