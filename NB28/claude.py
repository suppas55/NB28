"""
title: Anthropic API Integration for OpenWebUI
author: Balaxxe
version: 2.2 - CaptResolve
license: MIT
requirements: pydantic>=2.0.0, requests>=2.0.0
environment_variables:
    - ANTHROPIC_API_KEY (required)

Supports:
- All Claude 3 models
- Streaming responses
- Image processing
- Prompt caching (server-side)
- Function calling
- PDF processing
- Cache Control

Updates:
Added Claude 3.7
Added valves to support thinking
"""

import os
import json
import time
import hashlib
import logging
import asyncio
from datetime import datetime
from typing import (
    List,
    Union,
    Generator,
    Iterator,
    Dict,
    Optional,
    AsyncIterator,
)
from pydantic import BaseModel, Field
from open_webui.utils.misc import pop_system_message
import aiohttp


class Pipe:
    API_VERSION = "2023-06-01"
    MODEL_URL = "https://api.anthropic.com/v1/messages"
    SUPPORTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    SUPPORTED_PDF_MODELS = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-20240620",
        "claude-3-7-sonnet-latest",
    ]
    MAX_IMAGE_SIZE = 5 * 1024 * 1024
    MAX_PDF_SIZE = 32 * 1024 * 1024
    TOTAL_MAX_IMAGE_SIZE = 100 * 1024 * 1024
    PDF_BETA_HEADER = "pdfs-2024-09-25"
    OUTPUT_128K_BETA = "output-128k-2025-02-19"
    # Model max tokens - updated with Claude 3.7 values
    MODEL_MAX_TOKENS = {
        "claude-3-opus-20240229": 4096,
        "claude-3-sonnet-20240229": 4096,
        "claude-3-haiku-20240307": 4096,
        "claude-3-5-sonnet-20240620": 8192,
        "claude-3-5-sonnet-20241022": 8192,
        "claude-3-5-haiku-20241022": 8192,
        "claude-3-opus-latest": 4096,
        "claude-3-5-sonnet-latest": 8192,
        "claude-3-5-haiku-latest": 8192,
        "claude-3-7-sonnet-latest": 16384,
        "claude-opus-4-0": 32000,
        "claude-sonnet-4-0": 64000,  # Claude 3.7 supports up to 16K output tokens by default, 128K with beta
    }
    # Model context lengths - maximum input tokens
    MODEL_CONTEXT_LENGTH = {
        "claude-3-opus-20240229": 200000,
        "claude-3-sonnet-20240229": 200000,
        "claude-3-haiku-20240307": 200000,
        "claude-3-5-sonnet-20240620": 200000,
        "claude-3-5-sonnet-20241022": 200000,
        "claude-3-5-haiku-20241022": 200000,
        "claude-3-opus-latest": 200000,
        "claude-3-5-sonnet-latest": 200000,
        "claude-3-5-haiku-latest": 200000,
        "claude-3-7-sonnet-latest": 200000,
        "claude-opus-4-0": 200000,
        "claude-sonnet-4-0": 200000,  # Claude 3.7 supports up to 200K context
    }
    BETA_HEADER = "prompt-caching-2024-07-31"
    REQUEST_TIMEOUT = 120  # Increased timeout for longer responses
    THINKING_BUDGET_TOKENS = 16000  # Default thinking budget tokens

    class Valves(BaseModel):
        ANTHROPIC_API_KEY: str = "Your API Key Here"
        ENABLE_THINKING: bool = False  # Valve to enable/disable thinking mode
        MAX_OUTPUT_TOKENS: bool = True  # Valve to use maximum possible output tokens
        ENABLE_TOOL_CHOICE: bool = True  # Valve to enable tool choice
        ENABLE_SYSTEM_PROMPT: bool = True  # Valve to enable system prompt
        THINKING_BUDGET_TOKENS: int = Field(
            default=16000, ge=0, le=16000
        )  # Configurable thinking budget tokens 16,000 max

    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.type = "manifold"
        self.id = "anthropic"
        self.valves = self.Valves()
        self.request_id = None

    def get_anthropic_models(self) -> List[dict]:
        return [
            {
                "id": f"anthropic/{name}",
                "name": name,
                "context_length": self.MODEL_CONTEXT_LENGTH.get(name, 200000),
                "supports_vision": name != "claude-3-5-haiku-20241022",
                "supports_thinking": name
                == "claude-3-7-sonnet-latest",  # Only Claude 3.7 supports thinking
            }
            for name in [
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
                "claude-3-5-sonnet-20240620",
                "claude-3-5-sonnet-20241022",
                "claude-3-5-haiku-20241022",
                "claude-3-opus-latest",
                "claude-3-5-sonnet-latest",
                "claude-3-5-haiku-latest",
                "claude-3-7-sonnet-latest",
                "claude-opus-4-0",
                "claude-sonnet-4-0",
            ]
        ]

    def pipes(self) -> List[dict]:
        return self.get_anthropic_models()

    def process_content(self, content: Union[str, List[dict]]) -> List[dict]:
        if isinstance(content, str):
            return [{"type": "text", "text": content}]

        processed_content = []
        for item in content:
            if item["type"] == "text":
                processed_content.append({"type": "text", "text": item["text"]})
            elif item["type"] == "image_url":
                processed_content.append(self.process_image(item))
            elif item["type"] == "pdf_url":
                model_name = item.get("model", "").split("/")[-1]
                if model_name not in self.SUPPORTED_PDF_MODELS:
                    raise ValueError(
                        f"PDF support is only available for models: {', '.join(self.SUPPORTED_PDF_MODELS)}"
                    )
                processed_content.append(self.process_pdf(item))
            elif item["type"] == "tool_calls":
                processed_content.append(item)
            elif item["type"] == "tool_results":
                processed_content.append(item)
        return processed_content

    def process_image(self, image_data):
        if image_data["image_url"]["url"].startswith("data:image"):
            mime_type, base64_data = image_data["image_url"]["url"].split(",", 1)
            media_type = mime_type.split(":")[1].split(";")[0]

            if media_type not in self.SUPPORTED_IMAGE_TYPES:
                raise ValueError(f"Unsupported media type: {media_type}")

            # Check image size
            image_size = len(base64_data) * 3 / 4  # Approximate size of decoded base64
            if image_size > self.MAX_IMAGE_SIZE:
                raise ValueError(
                    f"Image size exceeds {self.MAX_IMAGE_SIZE/(1024*1024)}MB limit: {image_size/(1024*1024):.2f}MB"
                )

            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64_data,
                },
            }
        else:
            return {
                "type": "image",
                "source": {"type": "url", "url": image_data["image_url"]["url"]},
            }

    def process_pdf(self, pdf_data):
        if pdf_data["pdf_url"]["url"].startswith("data:application/pdf"):
            mime_type, base64_data = pdf_data["pdf_url"]["url"].split(",", 1)

            # Check PDF size
            pdf_size = len(base64_data) * 3 / 4  # Approximate size of decoded base64
            if pdf_size > self.MAX_PDF_SIZE:
                raise ValueError(
                    f"PDF size exceeds {self.MAX_PDF_SIZE/(1024*1024)}MB limit: {pdf_size/(1024*1024):.2f}MB"
                )

            document = {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": base64_data,
                },
            }

            if pdf_data.get("cache_control"):
                document["cache_control"] = pdf_data["cache_control"]

            return document
        else:
            document = {
                "type": "document",
                "source": {"type": "url", "url": pdf_data["pdf_url"]["url"]},
            }

            if pdf_data.get("cache_control"):
                document["cache_control"] = pdf_data["cache_control"]

            return document

    async def pipe(
        self, body: Dict, __event_emitter__=None
    ) -> Union[str, AsyncIterator[str]]:
        """
        Process a request to the Anthropic API.

        Args:
            body: The request body containing messages and parameters
            __event_emitter__: Optional event emitter for status updates

        Returns:
            Either a string response or an async iterator for streaming responses
        """
        if not self.valves.ANTHROPIC_API_KEY:
            error_msg = "Error: ANTHROPIC_API_KEY is required"
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": error_msg,
                            "done": True,
                        },
                    }
                )
            return {"content": error_msg, "format": "text"}

        try:
            system_message, messages = pop_system_message(body["messages"])

            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": "Processing request...", "done": False},
                    }
                )

            model_name = body["model"].split("/")[-1]
            if model_name not in self.MODEL_MAX_TOKENS:
                logging.warning(
                    f"Unknown model: {model_name}, using default token limit"
                )

            # Get max tokens for the model
            max_tokens_limit = self.MODEL_MAX_TOKENS.get(model_name, 4096)

            # If MAX_OUTPUT_TOKENS valve is enabled, use the maximum possible tokens for the model
            if self.valves.MAX_OUTPUT_TOKENS:
                max_tokens = max_tokens_limit
            else:
                max_tokens = min(
                    body.get("max_tokens", max_tokens_limit), max_tokens_limit
                )

            payload = {
                "model": model_name,
                "messages": self._process_messages(messages),
                "max_tokens": max_tokens,
                "temperature": (
                    float(body.get("temperature"))
                    if body.get("temperature") is not None
                    else None
                ),
                "top_k": (
                    int(body.get("top_k")) if body.get("top_k") is not None else None
                ),
                "top_p": (
                    float(body.get("top_p")) if body.get("top_p") is not None else None
                ),
                "stream": body.get("stream", False),
                "metadata": body.get("metadata", {}),
            }

            # Add thinking parameter with proper format if enabled and model supports it
            if self.valves.ENABLE_THINKING and model_name == "claude-3-7-sonnet-latest":
                payload["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": self.valves.THINKING_BUDGET_TOKENS,
                }

            payload = {k: v for k, v in payload.items() if v is not None}

            # Add system message if enabled
            if system_message and self.valves.ENABLE_SYSTEM_PROMPT:
                payload["system"] = str(system_message)

            # Add tools if enabled
            if "tools" in body and self.valves.ENABLE_TOOL_CHOICE:
                payload["tools"] = [
                    {"type": "function", "function": tool} for tool in body["tools"]
                ]
                payload["tool_choice"] = body.get("tool_choice")

            if "response_format" in body:
                payload["response_format"] = {
                    "type": body["response_format"].get("type")
                }

            headers = {
                "x-api-key": self.valves.ANTHROPIC_API_KEY,
                "anthropic-version": self.API_VERSION,
                "content-type": "application/json",
            }

            beta_headers = []

            # Add PDF beta header if needed
            if any(
                isinstance(msg["content"], list)
                and any(item.get("type") == "pdf_url" for item in msg["content"])
                for msg in body.get("messages", [])
            ):
                beta_headers.append(self.PDF_BETA_HEADER)

            # Add cache control beta header if needed
            if any(
                isinstance(msg["content"], list)
                and any(item.get("cache_control") for item in msg["content"])
                for msg in body.get("messages", [])
            ):
                beta_headers.append(self.BETA_HEADER)

            # Add 128K output beta header for Claude 3.7
            if (
                model_name == "claude-3-7-sonnet-latest"
                and self.valves.MAX_OUTPUT_TOKENS
            ):
                beta_headers.append(self.OUTPUT_128K_BETA)

            if beta_headers:
                headers["anthropic-beta"] = ",".join(beta_headers)

            try:
                if payload["stream"]:
                    return self._stream_with_ui(
                        self.MODEL_URL, headers, payload, body, __event_emitter__
                    )

                response_data, cache_metrics = await self._send_request(
                    self.MODEL_URL, headers, payload
                )

                if (
                    isinstance(response_data, dict)
                    and "content" in response_data
                    and response_data.get("format") == "text"
                ):
                    # This is an error response
                    if __event_emitter__:
                        await __event_emitter__(
                            {
                                "type": "status",
                                "data": {
                                    "description": response_data["content"],
                                    "done": True,
                                },
                            }
                        )
                    return response_data["content"]

                # Handle tool calls in the response
                if any(
                    block.get("type") == "tool_use"
                    for block in response_data.get("content", [])
                ):
                    tool_blocks = [
                        block
                        for block in response_data.get("content", [])
                        if block.get("type") == "tool_use"
                    ]
                    tool_calls = []
                    for block in tool_blocks:
                        tool_use = block["tool_use"]
                        tool_calls.append(
                            {
                                "id": tool_use["id"],
                                "type": "function",
                                "function": {
                                    "name": tool_use["name"],
                                    "arguments": tool_use["input"],
                                },
                            }
                        )

                    if tool_calls:
                        return json.dumps(
                            {"type": "tool_calls", "tool_calls": tool_calls}
                        )

                # Handle thinking in the response
                thinking_content = None
                if (
                    self.valves.ENABLE_THINKING
                    and model_name == "claude-3-7-sonnet-latest"
                ):
                    thinking_blocks = [
                        block
                        for block in response_data.get("content", [])
                        if block.get("type") == "thinking"
                    ]
                    if thinking_blocks:
                        thinking_content = thinking_blocks[0].get("thinking", "")

                # Get the text response
                text_blocks = [
                    block
                    for block in response_data.get("content", [])
                    if block.get("type") == "text"
                ]
                response_text = text_blocks[0]["text"] if text_blocks else ""

                # If thinking is available, prepend it to the response
                if thinking_content:
                    response_text = f"### Thinking\n{thinking_content}\n\n### Response\n{response_text}"

                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {
                                "description": "Request completed successfully",
                                "done": True,
                            },
                        }
                    )

                return response_text

            except Exception as e:
                error_msg = f"Request failed: {str(e)}"
                if self.request_id:
                    error_msg += f" (Request ID: {self.request_id})"

                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {"description": error_msg, "done": True},
                        }
                    )
                return {"content": error_msg, "format": "text"}

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            if self.request_id:
                error_msg += f" (Request ID: {self.request_id})"

            if __event_emitter__:
                await __event_emitter__(
                    {"type": "status", "data": {"description": error_msg, "done": True}}
                )
            return {"content": error_msg, "format": "text"}

    async def _stream_with_ui(
        self, url: str, headers: dict, payload: dict, body: dict, __event_emitter__=None
    ) -> AsyncIterator[str]:
        """
        Stream responses from the Anthropic API with UI event updates.

        Args:
            url: The API endpoint URL
            headers: Request headers
            payload: Request payload
            body: Original request body
            __event_emitter__: Optional event emitter for status updates

        Yields:
            Text chunks from the streaming response
        """
        try:
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT)
                async with session.post(
                    url, headers=headers, json=payload, timeout=timeout
                ) as response:
                    self.request_id = response.headers.get("x-request-id")
                    if response.status != 200:
                        error_text = await response.text()
                        error_msg = f"Error: HTTP {response.status}: {error_text}"
                        if self.request_id:
                            error_msg += f" (Request ID: {self.request_id})"
                        if __event_emitter__:
                            await __event_emitter__(
                                {
                                    "type": "status",
                                    "data": {
                                        "description": error_msg,
                                        "done": True,
                                    },
                                }
                            )
                        yield error_msg
                        return

                    # For tracking thinking content in streaming mode
                    thinking_content = ""
                    is_thinking = False

                    async for line in response.content:
                        if line and line.startswith(b"data: "):
                            try:
                                line_text = line[6:].decode("utf-8").strip()
                                if line_text == "[DONE]":
                                    break

                                data = json.loads(line_text)

                                # Handle thinking blocks
                                if (
                                    data["type"] == "content_block_start"
                                    and data["content_block"]["type"] == "thinking"
                                ):
                                    is_thinking = True
                                    if self.valves.ENABLE_THINKING:
                                        yield "\n### Thinking\n"

                                elif (
                                    data["type"] == "content_block_delta"
                                    and is_thinking
                                ):
                                    if (
                                        "text" in data["delta"]
                                        and self.valves.ENABLE_THINKING
                                    ):
                                        thinking_content += data["delta"]["text"]
                                        yield data["delta"]["text"]

                                elif (
                                    data["type"] == "content_block_stop" and is_thinking
                                ):
                                    is_thinking = False
                                    if self.valves.ENABLE_THINKING:
                                        yield "\n\n### Response\n"

                                # Handle regular text content
                                elif (
                                    data["type"] == "content_block_delta"
                                    and "text" in data["delta"]
                                    and not is_thinking
                                ):
                                    yield data["delta"]["text"]

                                # Handle tool use responses
                                elif (
                                    data["type"] == "content_block_start"
                                    and data["content_block"]["type"] == "tool_use"
                                ):
                                    # Handle tool use responses
                                    tool_use = data["content_block"]["tool_use"]
                                    tool_data = {
                                        "type": "tool_calls",
                                        "tool_calls": [
                                            {
                                                "id": tool_use["id"],
                                                "type": "function",
                                                "function": {
                                                    "name": tool_use["name"],
                                                    "arguments": tool_use["input"],
                                                },
                                            }
                                        ],
                                    }
                                    yield json.dumps(tool_data)

                                elif data["type"] == "message_stop":
                                    if __event_emitter__:
                                        await __event_emitter__(
                                            {
                                                "type": "status",
                                                "data": {
                                                    "description": "Request completed",
                                                    "done": True,
                                                },
                                            }
                                        )
                                    break
                            except json.JSONDecodeError as e:
                                logging.error(
                                    f"Failed to parse streaming response: {e}"
                                )
                                continue
        except asyncio.TimeoutError:
            error_msg = "Request timed out"
            if self.request_id:
                error_msg += f" (Request ID: {self.request_id})"
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": error_msg, "done": True},
                    }
                )
            yield error_msg
        except Exception as e:
            error_msg = f"Stream error: {str(e)}"
            if self.request_id:
                error_msg += f" (Request ID: {self.request_id})"
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": error_msg, "done": True},
                    }
                )
            yield error_msg

    def _process_messages(self, messages: List[dict]) -> List[dict]:
        """
        Process messages for the Anthropic API format.

        Args:
            messages: List of message objects

        Returns:
            Processed messages in Anthropic API format
        """
        processed_messages = []
        for message in messages:
            processed_content = []
            for content in self.process_content(message["content"]):
                if (
                    message.get("role") == "assistant"
                    and content.get("type") == "tool_calls"
                ):
                    content["cache_control"] = {"type": "ephemeral"}
                elif (
                    message.get("role") == "user"
                    and content.get("type") == "tool_results"
                ):
                    content["cache_control"] = {"type": "ephemeral"}
                processed_content.append(content)
            processed_messages.append(
                {"role": message["role"], "content": processed_content}
            )
        return processed_messages

    async def _send_request(
        self, url: str, headers: dict, payload: dict
    ) -> tuple[dict, Optional[dict]]:
        """
        Send a request to the Anthropic API with retry logic.

        Args:
            url: The API endpoint URL
            headers: Request headers
            payload: Request payload

        Returns:
            Tuple of (response_data, cache_metrics)
        """
        retry_count = 0
        base_delay = 1  # Start with 1 second delay
        max_retries = 3

        while retry_count < max_retries:
            try:
                async with aiohttp.ClientSession() as session:
                    timeout = aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT)
                    async with session.post(
                        url, headers=headers, json=payload, timeout=timeout
                    ) as response:
                        self.request_id = response.headers.get("x-request-id")

                        if response.status == 429:
                            retry_after = int(
                                response.headers.get(
                                    "retry-after", base_delay * (2**retry_count)
                                )
                            )
                            logging.warning(
                                f"Rate limit hit. Retrying in {retry_after} seconds. Retry count: {retry_count + 1}"
                            )
                            await asyncio.sleep(retry_after)
                            retry_count += 1
                            continue

                        response_text = await response.text()

                        if response.status != 200:
                            error_msg = f"Error: HTTP {response.status}"
                            try:
                                error_data = json.loads(response_text).get("error", {})
                                error_msg += (
                                    f": {error_data.get('message', response_text)}"
                                )
                            except:
                                error_msg += f": {response_text}"

                            if self.request_id:
                                error_msg += f" (Request ID: {self.request_id})"

                            return {"content": error_msg, "format": "text"}, None

                        result = json.loads(response_text)
                        usage = result.get("usage", {})
                        cache_metrics = {
                            "cache_creation_input_tokens": usage.get(
                                "cache_creation_input_tokens", 0
                            ),
                            "cache_read_input_tokens": usage.get(
                                "cache_read_input_tokens", 0
                            ),
                            "input_tokens": usage.get("input_tokens", 0),
                            "output_tokens": usage.get("output_tokens", 0),
                        }
                        return result, cache_metrics

            except aiohttp.ClientError as e:
                logging.error(f"Request failed: {str(e)}")
                if retry_count < max_retries - 1:
                    retry_count += 1
                    await asyncio.sleep(base_delay * (2**retry_count))
                    continue
                raise

        logging.error("Max retries exceeded for rate limit.")
        return {"content": "Max retries exceeded", "format": "text"}, None
