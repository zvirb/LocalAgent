"""
Example provider scaffold for contributors.
Disabled by default; not registered in ProviderManager.
"""

from typing import Any, Dict, AsyncIterator, List
from .base_provider import (
    BaseProvider,
    CompletionRequest,
    CompletionResponse,
    ModelInfo,
)


class FooProvider(BaseProvider):
    """Minimal example provider for LocalAgent."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.is_local = True
        self.requires_api_key = False

    async def initialize(self) -> bool:
        return True

    async def list_models(self) -> List[ModelInfo]:
        default_model = self.config.get("default_model", "foo-small")
        return [
            ModelInfo(
                name=default_model,
                provider="foo",
                context_length=128_000,
                capabilities=["chat", "completion"],
            )
        ]

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        usage = {"prompt": 1, "completion": 1, "total": 2}
        return CompletionResponse(
            content="ok",
            model=request.model,
            provider="foo",
            usage=usage,
        )

    async def stream_complete(self, request: CompletionRequest) -> AsyncIterator[str]:
        yield "ok"

    async def health_check(self) -> Dict[str, Any]:
        return {"healthy": True, "provider": "foo"}

