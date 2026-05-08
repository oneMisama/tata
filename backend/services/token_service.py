"""
Tata - Token Service & LLM API Gateway
Manages user token quotas, multi-provider routing, and API key proxying.
The server acts as a secure middleware between users and LLM providers.
"""

import hashlib
import time
import asyncio
from datetime import datetime, timedelta
from typing import Optional, AsyncGenerator
from openai import AsyncOpenAI

from config import settings


class TokenService:
    """
    Token quota management + LLM provider gateway.
    
    Architecture:
    ┌──────────┐     ┌──────────────┐     ┌─────────────┐
    │  Client  │────▶│ Tata Server  │────▶│ DeepSeek API │
    │ (App)    │     │ (Token Gate) │     │ OpenAI  API  │
    └──────────┘     └──────────────┘     │ MiMo    API  │
                                          └─────────────┘
    
    The server holds API keys, manages user quotas, and proxies
    LLM requests. Users never touch API keys directly.
    """

    # Provider configurations
    PROVIDERS = {
        "deepseek": {
            "name": "DeepSeek",
            "base_url": "https://api.deepseek.com/v1",
            "models": ["deepseek-chat", "deepseek-reasoner"],
            "default_model": "deepseek-chat",
            "input_price_per_1m": 0.14,   # USD
            "output_price_per_1m": 0.28,
        },
        "openai": {
            "name": "OpenAI",
            "base_url": "https://api.openai.com/v1",
            "models": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
            "default_model": "gpt-4o-mini",
            "input_price_per_1m": 0.15,
            "output_price_per_1m": 0.60,
        },
        "mimo": {
            "name": "Xiaomi MiMo",
            "base_url": "https://api.xiaomimimo.com/v1",
            "models": ["mimo-v2.5", "mimo-v2.5-pro"],
            "default_model": "mimo-v2.5",
            "input_price_per_1m": 0.10,
            "output_price_per_1m": 0.20,
        },
    }

    def __init__(self):
        self._clients: dict[str, AsyncOpenAI] = {}
        self._init_clients()

    def _init_clients(self):
        """Initialize API clients for each configured provider."""
        provider_keys = {
            "deepseek": settings.deepseek_api_key,
            "openai": settings.openai_api_key,
            "mimo": settings.mimo_api_key,
        }
        for name, config in self.PROVIDERS.items():
            key = provider_keys.get(name)
            if key:
                self._clients[name] = AsyncOpenAI(
                    api_key=key,
                    base_url=config["base_url"]
                )

    def get_available_providers(self) -> list[dict]:
        """List providers with available API keys."""
        result = []
        for name, config in self.PROVIDERS.items():
            result.append({
                "id": name,
                "name": config["name"],
                "models": config["models"],
                "default_model": config["default_model"],
                "available": name in self._clients,
                "pricing": {
                    "input_per_1m": config["input_price_per_1m"],
                    "output_per_1m": config["output_price_per_1m"],
                }
            })
        return result

    def get_client(self, provider: str) -> Optional[AsyncOpenAI]:
        return self._clients.get(provider)

    # ── Token Quota Management ─────────────────────────

    @staticmethod
    def calculate_tokens(text: str) -> int:
        """Rough token estimation (~4 chars per token for Chinese)."""
        return len(text) // 2  # Conservative estimate for mixed CN/EN

    @staticmethod
    def check_quota(user_tokens_remaining: int, input_text: str, estimated_output: int = 500) -> tuple[bool, int]:
        """Check if user has enough tokens. Returns (ok, estimated_cost)."""
        input_tokens = TokenService.calculate_tokens(input_text)
        total_estimate = input_tokens + estimated_output
        return user_tokens_remaining >= total_estimate, total_estimate

    @staticmethod
    def estimate_cost(provider: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost in USD."""
        config = TokenService.PROVIDERS.get(provider, TokenService.PROVIDERS["deepseek"])
        return (input_tokens * config["input_price_per_1m"] / 1_000_000) + \
               (output_tokens * config["output_price_per_1m"] / 1_000_000)

    # ── LLM Gateway (Proxied API Calls) ────────────────

    async def chat_completion(
        self,
        provider: str,
        model: str,
        messages: list[dict],
        temperature: float = 0.85,
        max_tokens: int = 1024,
    ) -> dict:
        """Proxy chat completion through the server."""
        client = self.get_client(provider)
        if not client:
            raise ValueError(f"Provider '{provider}' not configured")

        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=0.95,
            frequency_penalty=0.3,
            presence_penalty=0.4,
        )

        usage = response.usage
        return {
            "content": response.choices[0].message.content,
            "model": response.model,
            "usage": {
                "input_tokens": usage.prompt_tokens,
                "output_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "estimated_cost_usd": self.estimate_cost(
                    provider, usage.prompt_tokens, usage.completion_tokens
                ),
            },
            "provider": provider,
        }

    async def chat_completion_stream(
        self,
        provider: str,
        model: str,
        messages: list[dict],
        temperature: float = 0.85,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion."""
        client = self.get_client(provider)
        if not client:
            raise ValueError(f"Provider '{provider}' not configured")

        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=0.95,
            frequency_penalty=0.3,
            presence_penalty=0.4,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    # ── Admin / Monitoring ─────────────────────────────

    def get_usage_stats(self, provider: str = None) -> dict:
        """Get provider usage statistics."""
        stats = {}
        providers = [provider] if provider else list(self._clients.keys())
        for p in providers:
            config = self.PROVIDERS.get(p, {})
            stats[p] = {
                "name": config.get("name", p),
                "available": p in self._clients,
                "models": config.get("models", []),
                "base_url": config.get("base_url", ""),
            }
        return stats


# Singleton
token_service = TokenService()
