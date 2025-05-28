"""
title: Perplexity Sonar Models

author: stoiccoder
author_url: https://github.com/stoiccoder
description: >
    Use Perplexity's Sonar models for online queries.
    Based on original work by konbakuyomu and sepp.
version: 1.0.0
licence: MIT
"""

import json
import httpx
import re
import traceback
import asyncio
import logging
from typing import AsyncGenerator, Callable, Awaitable
from pydantic import BaseModel, Field
from urllib.parse import urlparse

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

TITLE_REGEX = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)


async def fetch_page_title(url: str, timeout: float = 10.0) -> str:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=timeout)
            if resp.status_code != 200:
                return ""
            html_content = resp.text
            match = TITLE_REGEX.search(html_content)
            if match:
                return match.group(1).strip()
    except Exception as e:
        print(f"Error requesting or parsing the page: {e}")
    return ""


def extract_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
        return parsed.netloc or ""
    except:
        return ""


class Pipe:
    class Valves(BaseModel):
        PERPLEXITY_API_BASE_URL: str = Field(
            default="https://api.perplexity.ai",
            description="Perplexity's base request URL",
        )
        PERPLEXITY_API_KEY: str = Field(
            default="",
            description="Required API key to access Perplexity services.",
        )
        NAME_PREFIX: str = Field(
            default="Perplexity/",
            description="The prefix applied before the model names.",
        )

    VALID_MODELS = [
        "sonar-reasoning-pro",
        "sonar-reasoning",
        "sonar-pro",
        "sonar",
        "sonar-deep-research",
    ]

    def __init__(self):
        self.type = "manifold"
        self.valves = self.Valves()
        self.data_prefix = "data: "
        self.emitter = None
        self.current_citations = []
        # Used to track the state of the reasoning chain: -1 not started, 0 thinking, 1 thinking ended
        self.thinking_state = {"thinking": -1}

    def pipes(self):
        """Return list of available Perplexity models."""
        return [
            {
                "id": "sonar-reasoning-pro",
                "name": f"{self.valves.NAME_PREFIX}Sonar Reasoning Pro",
            },
            {
                "id": "sonar-reasoning",
                "name": f"{self.valves.NAME_PREFIX}Sonar Reasoning",
            },
            {
                "id": "sonar-pro",
                "name": f"{self.valves.NAME_PREFIX}Sonar Pro",
            },
            {
                "id": "sonar",
                "name": f"{self.valves.NAME_PREFIX}Sonar",
            },
            {
                "id": "sonar-deep-research",
                "name": f"{self.valves.NAME_PREFIX}Sonar Deep Research",
            },
        ]

    async def pipe(
        self, body: dict, __event_emitter__: Callable[[dict], Awaitable[None]] = None
    ) -> AsyncGenerator[str, None]:
        logger.debug("Starting pipe execution")
        logger.debug(f"Input body: {json.dumps(body, indent=2)}")

        self.emitter = __event_emitter__
        self.current_citations = []

        # (A) Check TOKEN
        if not self.valves.PERPLEXITY_API_KEY:
            logger.error("Perplexity API Key not configured")
            err_msg = "Perplexity API Key not configured"
            yield json.dumps({"error": err_msg}, ensure_ascii=False)
            return

        # (B) Check if the model is valid
        model_id = body["model"]
        if model_id.startswith(self.valves.NAME_PREFIX):
            model_id = model_id[len(self.valves.NAME_PREFIX) :]
        if model_id.startswith("perplexity_sonar_models."):
            model_id = model_id[len("perplexity_sonar_models.") :]

        if model_id not in self.VALID_MODELS:
            logger.error(f"Invalid model selected: {model_id}")
            err_msg = (
                f"Model '{model_id}' is not in the valid range: "
                f"{', '.join(self.VALID_MODELS)}"
            )
            yield json.dumps({"error": err_msg}, ensure_ascii=False)
            return

        # (C) Clean up image links in user input
        logger.debug("Cleaning up image links in user input")
        self._inject_image_if_any(body)

        # (D) Preprocess messages
        logger.debug("Preprocessing messages")
        self._process_messages(body)

        # Assemble payload
        payload = {**body}
        payload["model"] = model_id
        if "stream" not in payload:
            payload["stream"] = True

        logger.debug(f"Prepared payload: {json.dumps(payload, indent=2)}")

        headers = {
            "Authorization": f"Bearer {self.valves.PERPLEXITY_API_KEY}",
            "Content-Type": "application/json",
        }
        url = f"{self.valves.PERPLEXITY_API_BASE_URL}/chat/completions"

        try:
            logger.debug(f"Making request to: {url}")
            async with httpx.AsyncClient(http2=True) as client:
                async with client.stream(
                    "POST", url, json=payload, headers=headers, timeout=120
                ) as response:
                    logger.debug(f"Response status: {response.status_code}")

                    if response.status_code != 200:
                        error_content = await response.aread()
                        logger.error(f"API Error: {error_content}")
                        err_str = self._format_error(
                            response.status_code, error_content
                        )
                        yield err_str
                        return
                    # Status: Connection successful, start generating response
                    if self.emitter:
                        await self.emitter(
                            {
                                "type": "status",
                                "data": {
                                    "description": "AI response is being generated...",
                                    "done": False,
                                },
                            }
                        )
                    first_chunk = True
                    # Read SSE line by line
                    async for line in response.aiter_lines():
                        if not line.startswith(self.data_prefix):
                            continue
                        data_str = line[len(self.data_prefix) :].strip()
                        if not data_str:
                            continue
                        try:
                            data = json.loads(data_str)
                        except:
                            continue
                        if "citations" in data:
                            self.current_citations = data["citations"]
                        choice = data.get("choices", [{}])[0]
                        delta = choice.get("delta", {})
                        # Update reasoning chain state (insert thinking marker if reasoning_content is encountered)
                        state_output = await self._update_thinking_state(
                            delta, self.thinking_state
                        )
                        if state_output:
                            yield state_output
                        delta_text = delta.get("content", "")
                        if delta_text:
                            # If it's the first valid response chunk, update the status
                            if first_chunk and self.emitter:
                                await self.emitter(
                                    {
                                        "type": "status",
                                        "data": {
                                            "description": "Perplexity is querying online, please wait...",
                                            "done": False,
                                        },
                                    }
                                )
                                first_chunk = False
                            # Keep reference transformation processing
                            delta_text = self._transform_references(
                                delta_text, self.current_citations
                            )
                            yield delta_text
                    # Status: Fetching reference website titles
                    if self.emitter:
                        await self.emitter(
                            {
                                "type": "status",
                                "data": {
                                    "description": "Fetching reference website titles, please wait...",
                                    "done": False,
                                },
                            }
                        )
                    # Output reference URLs (with webpage titles)
                    if self.current_citations:
                        yield await self._format_references(self.current_citations)
                    # Status: Completed
                    if self.emitter:
                        await self.emitter(
                            {
                                "type": "status",
                                "data": {
                                    "description": "✅ Perplexity generation completed",
                                    "done": True,
                                },
                            }
                        )
                    # Reset reasoning chain state
                    self.thinking_state = {"thinking": -1}
        except Exception as e:
            traceback.print_exc()
            err_str = self._format_exception(e)
            yield err_str

    def _inject_image_if_any(self, payload: dict) -> None:
        """Remove image links from user messages"""
        messages = payload.get("messages", [])
        if not messages:
            return
        last_msg = messages[-1]
        if last_msg.get("role") != "user":
            return
        content_str = last_msg.get("content", "")
        if not isinstance(content_str, str):
            return
        cleaned_text = re.sub(
            r"(https?://[^\s]+?\.(?:png|jpg|jpeg|gif|bmp|tiff|webp))",
            "",
            content_str,
            flags=re.IGNORECASE,
        ).strip()
        last_msg["content"] = cleaned_text

    def _process_messages(self, payload: dict) -> None:
        """Avoid consecutive same-role messages, insert placeholder messages"""
        messages = payload.get("messages", [])
        i = 0
        while i < len(messages) - 1:
            if messages[i]["role"] == messages[i + 1]["role"]:
                alternate_role = (
                    "assistant" if messages[i]["role"] == "user" else "user"
                )
                messages.insert(
                    i + 1, {"role": alternate_role, "content": "[Unfinished thinking]"}
                )
                i += 1  # Skip the inserted placeholder message
            i += 1

    async def _update_thinking_state(self, delta: dict, thinking_state: dict) -> str:
        """Update reasoning chain state, based on whether reasoning_content exists in delta"""
        state_output = ""
        # When reasoning_content is received, consider it as entering the thinking state
        if thinking_state["thinking"] == -1 and delta.get("reasoning_content"):
            thinking_state["thinking"] = 0
            state_output = "\n\n"
        return state_output

    def _transform_references(self, text: str, citations: list) -> str:
        def _replace_one(m: re.Match) -> str:
            idx_str = m.group(1)
            idx = int(idx_str)
            if 1 <= idx <= len(citations):
                url = citations[idx - 1]
                return f"[[{idx_str}]]({url})"
            else:
                return f"[[{idx_str}]]"

        return re.sub(r"\[(\d+)\]", _replace_one, text)

    async def _format_references(self, citations: list) -> str:
        if not citations:
            return ""
        lines = []
        lines.append("\n\n<details>\n<summary>Reference Websites</summary>")

        # Create tasks for all title fetches
        tasks = [fetch_page_title(url) for url in citations]
        titles = await asyncio.gather(*tasks)

        for i, (url, title) in enumerate(zip(citations, titles), 1):
            if title:
                lines.append(f"{i}: [{title}]({url})")
            else:
                domain = extract_domain(url)
                if not domain:
                    domain = "unknown"
                lines.append(f"{i}: [News source: {domain}]({url})")
        lines.append("</details>")
        return "\n".join(lines)

    def _format_error(self, status_code: int, error: bytes) -> str:
        try:
            err_msg = json.loads(error).get("message", error.decode(errors="ignore"))[
                :200
            ]
        except:
            err_msg = error.decode(errors="ignore")[:200]
        return json.dumps(
            {"error": f"HTTP {status_code}: {err_msg}"}, ensure_ascii=False
        )

    def _format_exception(self, e: Exception) -> str:
        err_type = type(e).__name__
        return json.dumps({"error": f"{err_type}: {str(e)}"}, ensure_ascii=False)
