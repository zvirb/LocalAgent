import pytest

pytestmark = pytest.mark.skip(reason="Example provider scaffold; enable when integrating FooProvider")

from app.llm_providers.foo_provider import FooProvider
from app.llm_providers.base_provider import CompletionRequest


@pytest.mark.asyncio
async def test_complete_returns_content():
    p = FooProvider({})
    await p.initialize()
    req = CompletionRequest(messages=[{"role": "user", "content": "hi"}], model="foo-small")
    resp = await p.complete(req)
    assert resp.content and resp.provider == "foo"

