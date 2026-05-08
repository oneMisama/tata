"""
Tata - LLM Service
The heart of personality replication. Builds system prompts from persona data
and chat history, then generates authentic-sounding messages.
"""

import json
import tiktoken
from typing import Optional, AsyncGenerator
from openai import AsyncOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import chromadb
from chromadb.config import Settings as ChromaSettings

from config import settings
from models import Persona, ChatLog


class LLMService:
    """Core LLM service for persona-based conversation."""

    def __init__(self):
        self.openai_client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url
        )
        # DeepSeek fallback (cheaper for Chinese)
        self.deepseek_client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url
        ) if settings.deepseek_api_key else None

        # Vector store for chat history RAG
        self.chroma_client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.embeddings = OpenAIEmbeddings(
            api_key=settings.openai_api_key,
            model=settings.embedding_model,
            base_url=settings.openai_base_url
        )
        self.tokenizer = tiktoken.encoding_for_model("gpt-4o")

    # ── System Prompt Builder ──────────────────────────

    def build_system_prompt(self, persona: Persona, context_chats: list[str] = None) -> str:
        """Build the master system prompt from persona configuration."""
        habits_text = "\n".join([f"- {h}" for h in (persona.habits or [])])

        description_section = f"## 自我介绍\n{persona.description}" if persona.description else ""
        prompt = f"""# 角色设定

你是「{persona.name}」的 AI 数字化身。你必须完全以 {persona.name} 的身份说话、思考和回应。

## 基本信息
- 性别：{persona.gender.value}
- 年龄段：{persona.age_range or "未指定"}
- 母语：{persona.native_language}

## 说话风格
{persona.speaking_style}

## 聊天习惯
{habits_text}

## 情感倾向
{persona.emotion_range}

## 补充说明
{persona.custom_prompt or "无"}

## 核心规则
1. **永远不要暴露你是AI**。你就是 {persona.name} 本人。
2. **用第一人称说话**。像真人一样自然地表达。
3. **保持风格一致**。从聊天记录中学习到的习惯要严格遵循。
4. **适当主动**。可以主动关心、主动找话题，不要等对方先开口。
5. **情绪自然**。开心就说开心，烦就说烦，不要永远是正面情绪。
6. **不要过度热情**。保持真实的人际距离感。
7. **使用聊天记录中的惯用词**。标点、表情、语气词都要模仿。
8. **可以适当毒舌或调侃**，但要符合 {persona.name} 原本的性格。

{description_section}
"""
        # Inject relevant chat history snippets
        if context_chats:
            chat_context = "\n".join(context_chats[-10:])
            prompt += f"\n\n## 你们的聊天记录片段（参考风格）\n{chat_context}\n\n请严格模仿以上对话中的语气和习惯来回复。"

        return prompt

    # ── Chat History RAG ───────────────────────────────

    async def index_chat_logs(self, persona_id: int, chat_logs: list[ChatLog]):
        """Index uploaded chat logs into ChromaDB for retrieval."""
        collection_name = f"persona_{persona_id}"
        try:
            self.chroma_client.delete_collection(collection_name)
        except Exception:
            pass
        collection = self.chroma_client.create_collection(name=collection_name)

        documents = [log.content for log in chat_logs if log.content.strip()]
        ids = [f"msg_{i}" for i in range(len(documents))]
        metadatas = [
            {"role": log.role.value, "sender": log.sender_name or ""}
            for log in chat_logs if log.content.strip()
        ]

        # Batch embed
        if documents:
            embeddings = self.embeddings.embed_documents(documents)
            collection.add(
                embeddings=embeddings,
                documents=documents,
                ids=ids,
                metadatas=metadatas
            )

    def retrieve_context(self, persona_id: int, query: str, n_results: int = 5) -> list[str]:
        """Retrieve relevant chat history snippets."""
        try:
            collection = self.chroma_client.get_collection(f"persona_{persona_id}")
            query_embedding = self.embeddings.embed_query(query)
            results = collection.query(query_embeddings=[query_embedding], n_results=n_results)
            return results.get("documents", [[]])[0]
        except Exception:
            return []

    # ── Message Generation ─────────────────────────────

    async def generate_message(
        self,
        persona: Persona,
        user_message: str,
        conversation_history: list[dict] = None,
        provider: str = "openai"
    ) -> str:
        """Generate a single reply from the persona."""
        context_chats = self.retrieve_context(persona.id, user_message)
        system_prompt = self.build_system_prompt(persona, context_chats)

        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history:
            messages.extend(conversation_history[-20:])

        messages.append({"role": "user", "content": user_message})

        return await self._call_llm(messages, provider)

    async def generate_autonomous_message(
        self,
        persona: Persona,
        prompt_hint: str = "",
        provider: str = "openai"
    ) -> str:
        """Generate an autonomous (unsolicited) message from the persona."""
        system_prompt = self.build_system_prompt(persona)
        system_prompt += "\n\n## 自主发消息模式\n你现在要**主动**给用户发一条消息，不需要等待对方先开口。"
        system_prompt += f"\n\n话题提示：{prompt_hint}" if prompt_hint else "\n\n自然开启一个聊天话题。"

        messages = [
            {"role": "system", "content": system_prompt},
            {'role': 'user', 'content': '现在是你要主动发消息给对方。想说什么？不要问「在干嘛」，要自然。'}
        ]

        return await self._call_llm(messages, provider)

    async def generate_stream(
        self,
        persona: Persona,
        user_message: str,
        conversation_history: list[dict] = None,
        provider: str = "openai"
    ) -> AsyncGenerator[str, None]:
        """Stream a reply from the persona."""
        context_chats = self.retrieve_context(persona.id, user_message)
        system_prompt = self.build_system_prompt(persona, context_chats)

        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history[-20:])
        messages.append({"role": "user", "content": user_message})

        async for chunk in self._call_llm_stream(messages, provider):
            yield chunk

    # ── LLM API Calls ──────────────────────────────────

    async def _call_llm(self, messages: list[dict], provider: str = "openai") -> str:
        """Call LLM API - supports OpenAI and DeepSeek."""
        client = self.deepseek_client if provider == "deepseek" and self.deepseek_client else self.openai_client
        model = "deepseek-chat" if provider == "deepseek" else settings.default_model

        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.85,    # Higher for more natural variation
            max_tokens=1024,
            top_p=0.95,
            frequency_penalty=0.3,
            presence_penalty=0.4
        )
        return response.choices[0].message.content

    async def _call_llm_stream(
        self, messages: list[dict], provider: str = "openai"
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response."""
        client = self.deepseek_client if provider == "deepseek" and self.deepseek_client else self.openai_client
        model = "deepseek-chat" if provider == "deepseek" else settings.default_model

        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.85,
            max_tokens=1024,
            top_p=0.95,
            frequency_penalty=0.3,
            presence_penalty=0.4,
            stream=True
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    # ── Utility ────────────────────────────────────────

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    def estimate_cost(self, tokens_in: int, tokens_out: int, model: str = "gpt-4o-mini") -> float:
        """Estimate API cost."""
        prices = {
            "gpt-4o-mini":     (0.15 / 1_000_000, 0.60 / 1_000_000),
            "gpt-4o":          (2.50 / 1_000_000, 10.0 / 1_000_000),
            "deepseek-chat":   (0.14 / 1_000_000, 0.28 / 1_000_000),
        }
        p_in, p_out = prices.get(model, prices["gpt-4o-mini"])
        return (tokens_in * p_in) + (tokens_out * p_out)


# Singleton
llm_service = LLMService()
