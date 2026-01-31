"""Model client for AI inference using OpenAI-compatible API."""

import json
import time
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from phone_agent.config.i18n import get_message
from concurrent.futures import ThreadPoolExecutor


@dataclass
class ModelConfig:
    """Configuration for the AI model."""

    base_url: str = "http://localhost:8000/v1"
    api_key: str = "EMPTY"
    model_name: str = "autoglm-phone-9b"
    max_tokens: int = 3000
    temperature: float = 0.0
    top_p: float = 0.85
    # top_k: float = 1
    frequency_penalty: float = 0.2
    extra_body: dict[str, Any] = field(default_factory=dict)
    lang: str = "cn"  # Language for UI messages: 'cn' or 'en'


@dataclass
class ModelResponse:
    """Response from the AI model."""

    thinking: str
    action: str
    raw_content: str
    # Performance metrics
    time_to_first_token: float | None = None  # Time to first token (seconds)
    time_to_thinking_end: float | None = None  # Time to thinking end (seconds)
    total_time: float | None = None  # Total inference time (seconds)
    parse_action_ok: bool | None = None
    action_obj:dict[str, Any] | None = None

class ModelClient:
    """
    Client for interacting with OpenAI-compatible vision-language models.

    Args:
        config: Model configuration.
    """

    def __init__(self, config: ModelConfig | None = None):
        self.config = config or ModelConfig()
        self.client = OpenAI(base_url=self.config.base_url, api_key=self.config.api_key)

    def request_n(self, messages: list[dict[str, Any]], n: int = 3) -> list[ModelResponse]:
        """并行请求 n 次，仅展示第一次请求的流式输出"""

        def safe_request(index: int):
            # 只有第一个请求 (index 0) 不是 silent 模式
            # 这样用户能看到其中一个模型的“思考过程”，而不会导致终端混乱
            is_print = index == 0
            if is_print:
                print(f"\n[Parallel] 发起 {n} 路并行请求，正在展示第 1 路的实时思考...\n")


            return self.client.request(messages, is_print=is_print)

        with ThreadPoolExecutor(max_workers=n) as executor:
            # 提交 n 个任务
            results = list(executor.map(safe_request, range(n)))

        return results

    def get_best_response(results: list[ModelResponse]) -> ModelResponse:
        # 1. 尝试完全匹配（字符串级别）
        action_counts = {}
        for res in results:
            action_counts[res.action] = action_counts.get(res.action, 0) + 1

        # 找到票数最多的 action
        best_action = max(action_counts, key=action_counts.get)

        if action_counts[best_action] >= 2:
            # 如果有 2 票及以上达成一致，直接返回对应的 response 对象
            for res in results:
                if res.action == best_action:
                    return res

        # 2. 如果 1:1:1 互不相同，则执行你说的“想法 2”：调用更强的 VLM 做裁判
        return call_strong_vlm_judge(results)

    def request(self, messages: list[dict[str, Any]], is_print: bool = True) -> ModelResponse:
        """
        Send a request to the model.

        Args:
            messages: List of message dictionaries in OpenAI format.
            is_print: is print.
        Returns:
            ModelResponse containing thinking and action.

        Raises:
            ValueError: If the response cannot be parsed.
        """

        # 定义内部辅助打印函数
        def _log(msg: str = "", end: str = "\n", flush: bool = False):
            if is_print:
                print(msg, end=end, flush=flush)
        # Start timing
        start_time = time.time()
        time_to_first_token = None
        time_to_thinking_end = None

        stream = self.client.chat.completions.create(
            messages=messages,
            model=self.config.model_name,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            # top_p=self.config.top_p,
            frequency_penalty=self.config.frequency_penalty,
            extra_body=self.config.extra_body,
            stream=True,
        )
        # print(f"extra_body:\n{self.config.extra_body}\nextra_body end") #{} extra_body目前是空对象
        raw_content = ""
        buffer = ""  # Buffer to hold content that might be part of a marker
        action_markers = ["finish(message=", "do(action="]
        in_action_phase = False  # Track if we've entered the action phase
        first_token_received = False

        for chunk in stream:
            if len(chunk.choices) == 0:
                continue
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                raw_content += content

                # Record time to first token
                if not first_token_received:
                    time_to_first_token = time.time() - start_time
                    first_token_received = True

                if in_action_phase:
                    # Already in action phase, just accumulate content without printing
                    continue

                buffer += content

                # Check if any marker is fully present in buffer
                marker_found = False
                for marker in action_markers:
                    if marker in buffer:
                        # Marker found, print everything before it
                        thinking_part = buffer.split(marker, 1)[0]
                        _log(thinking_part, end="", flush=True)
                        _log()  # Print newline after thinking is complete
                        in_action_phase = True
                        marker_found = True

                        # Record time to thinking end
                        if time_to_thinking_end is None:
                            time_to_thinking_end = time.time() - start_time

                        break

                if marker_found:
                    continue  # Continue to collect remaining content

                # Check if buffer ends with a prefix of any marker
                # If so, don't print yet (wait for more content)
                is_potential_marker = False
                for marker in action_markers:
                    for i in range(1, len(marker)):
                        if buffer.endswith(marker[:i]):
                            is_potential_marker = True
                            break
                    if is_potential_marker:
                        break

                if not is_potential_marker:
                    # Safe to print the buffer
                    _log(buffer, end="", flush=True)
                    buffer = ""

        # Calculate total time
        total_time = time.time() - start_time

        # Parse thinking and action from response
        thinking, action = self._parse_response(raw_content)

        # Print performance metrics
        lang = self.config.lang
        _log()
        _log("=" * 50)
        _log(f"⏱️  {get_message('performance_metrics', lang)}:") #  ⏱️  性能指标:
        _log("-" * 50)
        if time_to_first_token is not None:
            _log(
                f"{get_message('time_to_first_token', lang)}: {time_to_first_token:.3f}s" #首 Token 延迟 (TTFT)
            )
        if time_to_thinking_end is not None:
            _log(
                f"{get_message('time_to_thinking_end', lang)}:        {time_to_thinking_end:.3f}s" #思考完成延迟
            )
        _log(
            f"{get_message('total_inference_time', lang)}:          {total_time:.3f}s" #总推理时间
        )
        _log("=" * 50)

        return ModelResponse(
            thinking=thinking,
            action=action,
            raw_content=raw_content,
            time_to_first_token=time_to_first_token,
            time_to_thinking_end=time_to_thinking_end,
            total_time=total_time,
        )

    def _parse_response(self, content: str) -> tuple[str, str]:
        """
        Parse the model response into thinking and action parts.

        Parsing rules:
        1. If content contains 'finish(message=', everything before is thinking,
           everything from 'finish(message=' onwards is action.
        2. If rule 1 doesn't apply but content contains 'do(action=',
           everything before is thinking, everything from 'do(action=' onwards is action.
        3. Fallback: If content contains '<answer>', use legacy parsing with XML tags.
        4. Otherwise, return empty thinking and full content as action.

        Args:
            content: Raw response content.

        Returns:
            Tuple of (thinking, action).
        """
        # Rule 1: Check for finish(message=
        if "finish(message=" in content:
            parts = content.split("finish(message=", 1)
            thinking = parts[0].strip()
            action = "finish(message=" + parts[1]
            return thinking, action

        # Rule 2: Check for do(action=
        if "do(action=" in content:
            parts = content.split("do(action=", 1)
            thinking = parts[0].strip()
            action = "do(action=" + parts[1]
            return thinking, action

        # Rule 3: Fallback to legacy XML tag parsing
        if "<answer>" in content:
            parts = content.split("<answer>", 1)
            thinking = parts[0].replace("<think>", "").replace("</think>", "").strip()
            action = parts[1].replace("</answer>", "").strip()
            return thinking, action

        # Rule 4: No markers found, return content as action
        return "", content


class MessageBuilder:
    """Helper class for building conversation messages."""

    @staticmethod
    def create_system_message(content: str) -> dict[str, Any]:
        """Create a system message."""
        return {"role": "system", "content": content}

    @staticmethod
    def create_user_message(
        text: str, image_base64: str | None = None
    ) -> dict[str, Any]:
        """
        Create a user message with optional image.

        Args:
            text: Text content.
            image_base64: Optional base64-encoded image.

        Returns:
            Message dictionary.
        """
        content = []

        if image_base64:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                }
            )

        content.append({"type": "text", "text": text})

        return {"role": "user", "content": content}

    @staticmethod
    def create_assistant_message(content: str) -> dict[str, Any]:
        """Create an assistant message."""
        return {"role": "assistant", "content": content}

    @staticmethod
    def remove_images_from_message(message: dict[str, Any]) -> dict[str, Any]:
        """
        Remove image content from a message to save context space.

        Args:
            message: Message dictionary.

        Returns:
            Message with images removed.
        """
        if isinstance(message.get("content"), list):
            message["content"] = [
                item for item in message["content"] if item.get("type") == "text"
            ]
        return message

    @staticmethod
    def build_screen_info(current_app: str, **extra_info) -> str:
        """
        Build screen info string for the model.

        Args:
            current_app: Current app name.
            **extra_info: Additional info to include.

        Returns:
            JSON string with screen info.
        """
        info = {"current_app": current_app, **extra_info}
        return json.dumps(info, ensure_ascii=False)
