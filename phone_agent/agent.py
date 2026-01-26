"""Main PhoneAgent class for orchestrating phone automation."""

import json
import traceback
from dataclasses import dataclass
from typing import Any, Callable

from phone_agent.actions import ActionHandler
from phone_agent.actions.handler import do, finish, parse_action, ActionResult
from phone_agent.config import get_messages, get_system_prompt
from phone_agent.device_factory import get_device_factory
from phone_agent.model import ModelClient, ModelConfig
from phone_agent.model.client import MessageBuilder
from datetime import datetime
import os
import uuid


@dataclass
class AgentConfig:
    """Configuration for the PhoneAgent."""

    max_steps: int = 15
    max_parse_action_error: int =3 #Failed to parse action retry next step
    device_id: str | None = None
    lang: str = "cn"
    system_prompt: str | None = None
    verbose: bool = True

    def __post_init__(self):
        if self.system_prompt is None:
            self.system_prompt = get_system_prompt(self.lang)


@dataclass
class StepResult:
    """Result of a single agent step."""

    success: bool
    finished: bool
    action: dict[str, Any] | None
    thinking: str
    message: str | None = None
    img: str=""


class PhoneAgent:
    """
    AI-powered agent for automating Android phone interactions.

    The agent uses a vision-language model to understand screen content
    and decide on actions to complete user tasks.

    Args:
        model_config: Configuration for the AI model.
        agent_config: Configuration for the agent behavior.
        confirmation_callback: Optional callback for sensitive action confirmation.
        takeover_callback: Optional callback for takeover requests.

    Example:
        >>> from phone_agent import PhoneAgent
        >>> from phone_agent.model import ModelConfig
        >>>
        >>> model_config = ModelConfig(base_url="http://localhost:8000/v1")
        >>> agent = PhoneAgent(model_config)
        >>> agent.run("Open WeChat and send a message to John")
    """

    def __init__(
        self,
        model_config: ModelConfig | None = None,
        agent_config: AgentConfig | None = None,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
    ):
        self.model_config = model_config or ModelConfig()
        self.agent_config = agent_config or AgentConfig()

        self.model_client = ModelClient(self.model_config)
        self.action_handler = ActionHandler(
            device_id=self.agent_config.device_id,
            confirmation_callback=confirmation_callback,
            takeover_callback=takeover_callback,
        )

        self._context: list[dict[str, Any]] = []
        self._step_count = 0
        self._parse_action_error_count = 0
        self._error_log:  list[dict[str, Any]] = []


    def run(self, task: str,image_save_path: str) -> str:
        """
        Run the agent to complete a task.

        Args:
            task: Natural language description of the task.

        Returns:
            Final message from the agent.
        """
        self._context = []
        self._step_count = 0
        # 记录自动化评估需要的数据
        program_start_time = datetime.now()
        hit_step_limit = False
        result_type = 0 #0初始化,1成功

        try:
            # First step with user prompt
            result = self._execute_step(task, is_first=True, image_save_path=image_save_path)

            if result.finished:
                if result.success:
                    result_type = 1
                return result.message or "Task completed"

            # Continue until finished or max steps reached
            while self._step_count < self.agent_config.max_steps:
                result = self._execute_step(is_first=False, image_save_path=image_save_path)

                if result.finished:
                    if result.success:
                        result_type = 1
                    return result.message or "Task completed"
            hit_step_limit = True #任务结果只有 2 种,成功和失败,失败有 2 种情况,发送错误或者达到最大步骤
            # print(f"\nResult: Max steps reached")
            return "Max steps reached"

        finally:
            # 记录自动化评估需要的数据
            program_end_time = datetime.now()
            duration = program_end_time - program_start_time
            print(f"程序开始时间: {program_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"程序结束时间: {program_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"程序运行耗时: {duration}")
            print(f"程序运行耗时秒: {duration.total_seconds():.1f} 秒")
            task_result_path = os.path.join(image_save_path, "task_result.json") #和截图一样使用传入路径

            task_result_data = {
                "task": task,
                "hit_step_limit": hit_step_limit,
                "program_start_time": program_start_time.strftime('%Y-%m-%d %H:%M:%S'),
                "program_end_time": program_end_time.strftime('%Y-%m-%d %H:%M:%S'),
                # "program_duration": {str(duration)[:-5]},
                "program_duration_seconds":  f"{duration.total_seconds():.1f}",
                "success": result.success and result.finished, #finish和成功才算任务完成
                "result_type": result_type, #0初始化,1成功,2,错误失败
                "final_img": result.img if result else "",  #最后的截图
                "max_steps": self.agent_config.max_steps,  #最后的截图
                "step_count": self._step_count,  #最后的截图
                "have_error":len(self._error_log) > 0, #发生过错误
                "error_log": self._error_log,
            }

            with open(task_result_path, 'w', encoding='utf-8') as json_file:
                json.dump(task_result_data, json_file, ensure_ascii=False, indent=4)





    def step(self, task: str | None = None) -> StepResult:
        """
        Execute a single step of the agent.

        Useful for manual control or debugging.

        Args:
            task: Task description (only needed for first step).

        Returns:
            StepResult with step details.
        """
        is_first = len(self._context) == 0

        if is_first and not task:
            raise ValueError("Task is required for the first step")

        return self._execute_step(task, is_first)

    def reset(self) -> None:
        """Reset the agent state for a new task."""
        self._context = []
        self._step_count = 0

    def _execute_step(
        self, user_prompt: str | None = None, is_first: bool = False,image_save_path: str = ""
    ) -> StepResult:
        """Execute a single step of the agent loop."""
        self._step_count += 1

        # Capture current screen state
        device_factory = get_device_factory()
        current_time = datetime.now()
        formatted_time = current_time.strftime(
            f'%Y-%m-%d-{current_time.hour * 3600 + current_time.minute * 60 + current_time.second}-{str(uuid.uuid4().hex[:8])}')
        local_image_dir = os.path.join(image_save_path, f"screenshot_{formatted_time}_{self._step_count}.png")
        screenshot = device_factory.get_screenshot(self.agent_config.device_id,10,local_image_dir=local_image_dir)
        current_app = device_factory.get_current_app(self.agent_config.device_id)

        # Build messages
        if is_first:
            self._context.append(
                MessageBuilder.create_system_message(self.agent_config.system_prompt)
            )

            screen_info = MessageBuilder.build_screen_info(current_app) #JSON string with screen info. 当前一直返回桌面怪不得,如果返回当前应用会更快,打开应用这步不让模型做
            text_content = f"{user_prompt}\n\n{screen_info}" #user_prompt只第一次请求有,后面通过聊天历史/上下文获得用户提示词和规划.方法的确不同

            self._context.append(
                MessageBuilder.create_user_message(
                    text=text_content, image_base64=screenshot.base64_data
                )
            )
        else:
            screen_info = MessageBuilder.build_screen_info(current_app)
            text_content = f"** Screen Info **\n\n{screen_info}"

            self._context.append(
                MessageBuilder.create_user_message(
                    text=text_content, image_base64=screenshot.base64_data
                )
            )

        # Get model response
        try:
            msgs = get_messages(self.agent_config.lang)
            print("\n" + "=" * 50) #--------------------------------------------------
            print(f"💭 {msgs['thinking']}:") #💭 思考过程: request中会答应思考过程,出错会是空
            print("-" * 50)
            response = self.model_client.request(self._context)
        except Exception as e:
            if self.agent_config.verbose:
                traceback.print_exc()
            return StepResult(
                success=False,
                finished=True,
                action=None,
                thinking="",
                message=f"Model error: {e}",
            )


        # Remove image from context to save space 移动到前面保证执行
        self._context[-1] = MessageBuilder.remove_images_from_message(self._context[-1])

        parse_action_ok = True
        # Parse action from response
        try:
            # print(f"Response:\n{response}\nResponse end")
            print(f"response json:\n{json.dumps(vars(response), indent=2, ensure_ascii=False)}\nresponse end")
            action = parse_action(response.action)
            self._parse_action_error_count = 0
            if self.agent_config.verbose: #解析成功才打印
                # Print thinking process
                print("-" * 50)  # --------------------------------------------------
                print(f"🎯 {msgs['action']}:")  # 🎯 执行动作:
                print(json.dumps(action, ensure_ascii=False, indent=2))
                print("=" * 50 + "\n")
        except ValueError:
            if self.agent_config.verbose:
                traceback.print_exc()
            # 解析错误
            parse_action_ok = False
            self._parse_action_error_count += 1
            parse_action_error_log =f"parse_action_error response.action {response.action}"
            self._error_log.append({"type": "parse_action_error", "text": parse_action_error_log})
            if self._parse_action_error_count > self.agent_config.max_parse_action_error:
                action = finish(message=parse_action_error_log)  # 解析错误生成一个空message的 finish.









        # Execute action
        if parse_action_ok or self._parse_action_error_count > self.agent_config.max_parse_action_error: #解析成功,或者错误大于 3 次
            #1.执行action
            try:
                result = self.action_handler.execute(
                    action, screenshot.width, screenshot.height
                )
            except Exception as e:
                if self.agent_config.verbose:
                    traceback.print_exc()
                result = self.action_handler.execute(
                    finish(message=str(e)), screenshot.width, screenshot.height
                )
                result.success = False #执行报错不成功
                # Add assistant response to context # 模型方法都 think和 action会使用解析后的添加进上下文发送到下一次
            #2.添加响应到上下文
            self._context.append(
                MessageBuilder.create_assistant_message(
                    f"<think>{response.thinking}</think><answer>{response.action}</answer>"
                )
            )
            if not parse_action_ok:
                result.success = False
        else:
            result = ActionResult(
                success=False,
                should_finish=False,
                message=parse_action_error_log,
            )


        # Check if finished
        finished = action.get("_metadata") == "finish" or result.should_finish

        if finished and self.agent_config.verbose:
            msgs = get_messages(self.agent_config.lang)
            print("\n" + "🎉 " + "=" * 48)
            print(
                f"✅ {msgs['task_completed']}: {result.message or action.get('message', msgs['done'])}" #  ✅ 任务完成:
            )
            print("=" * 50 + "\n")

        return StepResult(
            success=result.success,
            finished=finished,
            action=action,
            thinking=response.thinking,
            message=result.message or action.get("message"),#正常情况执行结果 result没有 message,除非执行敏感操作错误.
            img=local_image_dir,
        )

    @property
    def context(self) -> list[dict[str, Any]]:
        """Get the current conversation context."""
        return self._context.copy()

    @property
    def step_count(self) -> int:
        """Get the current step count."""
        return self._step_count
