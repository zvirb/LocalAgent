import sys
import types

# Stub aioredis to avoid heavy dependency during tests
sys.modules.setdefault("aioredis", types.ModuleType("aioredis"))

from app.orchestration.cli_interface import LocalAgentCLI


def test_load_agents_context(tmp_path, monkeypatch):
    root_agents = tmp_path / "AGENTS.md"
    root_agents.write_text("root instruction", encoding="utf-8")

    subdir = tmp_path / "sub"
    subdir.mkdir()
    sub_agents = subdir / "AGENTS.md"
    sub_agents.write_text("sub instruction", encoding="utf-8")

    cli = LocalAgentCLI()
    monkeypatch.chdir(subdir)

    content = cli._load_agents_context()

    assert "root instruction" in content
    assert "sub instruction" in content
    assert content.index("root instruction") < content.index("sub instruction")

