"""Main PhoneAgent class for orchestrating phone automation."""

import json
import sys
import traceback
from dataclasses import dataclass
from typing import Any, Callable

from phone_agent.actions import ActionHandler
from phone_agent.actions.handler import do, finish, parse_action, ActionResult
from phone_agent.config import get_messages, get_system_prompt
from phone_agent.device_factory import get_device_factory
from phone_agent.model import ModelClient, ModelConfig
from phone_agent.model.client import MessageBuilder, ModelResponse
from datetime import datetime
import os
import uuid
import copy
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED, FIRST_COMPLETED

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
        self._image_save_path = "./logs"


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
        self._image_save_path = image_save_path
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

    @staticmethod
    def safe_serialize(response):
        try:
            return vars(response)
        except TypeError:
            return str(response)

    def log_model_message(self, response, index: int, text_content=None):
        """
        记录模型接口日志到指定的 JSON 文件。

        Args:
            response: 模型响应对象，需包含 total_time 属性。
            message_save_path: 日志保存的目录路径。
            index: 请求缩影
        """


        message_save_path =self._image_save_path
        file_prefix = f"step_{self._step_count}_req_{index}"

        # 构建文件路径
        message_file = os.path.join(message_save_path,f"{file_prefix}.json")

        # 提取响应数据
        # 如果 response 是对象则转为字典，如果是字典则直接使用
        # resp_data = vars(response) if hasattr(response, '__dict__') else response

        message_data = {
            "name": "manager",
            "messages": self._context,
            "response": self.safe_serialize(response),
            "step_id": self._step_count,
            "total_time": response.total_time,
        }

        try:
            with open(message_file, 'w', encoding='utf-8') as json_file:
                json.dump(message_data, json_file, ensure_ascii=False, indent=4)
                # Save prompt and output to manager.log
            log_file = os.path.join(message_save_path, f"{file_prefix}.log")
            with open(log_file, "w", encoding="utf-8") as f:
                f.write("=== PROMPT ===\n")
                f.write(text_content + "\n\n")  # 无图片提示词方便查看,只有用户提示词
                f.write("=== OUTPUT ===\n")
                f.write(response.raw_content)  # 怎么没有标签,模型并没有按照要求
        except Exception as e:
            print(f"Failed to save log: {e}")

    @staticmethod
    def get_best_response(responses: list[ModelResponse]) -> ModelResponse:
        """
        从多个并行响应中选出最优结果。
        逻辑：
        1. 校验解析状态
        2. 优先返回非 'do' 动作 (如 finish)
        3. 优先返回非 'Tap' 动作 (如 Scroll, Input)
        4. 对多个 Tap 动作进行坐标平滑处理 (去掉最大值取平均)
        """
        if not responses:
            return None

        # --- 1. 遍历校验解析状态 ---
        ok_responses = [r for r in responses if r.parse_action_ok is True]

        if not ok_responses:
            return responses[0]  # 全部失败，返回第一个
        if len(ok_responses) == 1:
            return ok_responses[0]  # 只有一个解析成功
        #  {
        #   "_metadata": "do",
        #   "action": "Tap",
        #   "element": [
        #     499,
        #     165
        #   ]
        # }
        # action_type = action.get("_metadata")
        # element = action.get("element")

        # --- 2. 遍历检查 _metadata (非 do 优先) ---
        # 例如：finish(message="xxx") 通常解析后的 _metadata 为 "finish"
        for r in ok_responses:
            if r.action_obj and r.action_obj.get("_metadata") != "do":
                return r

        # --- 3. 遍历检查 action 类型 (非 Tap 优先) ---
        # 如果有输入、滑动等复杂操作，不进行投票，直接取第一个遇到的
        for r in ok_responses:
            if r.action_obj and r.action_obj.get("action") != "Tap":
                return r

        # --- 4. 坐标平滑处理 (针对全为 Tap 的情况) ---
        # 5. 坐标去噪 (X:[300,320,500]->310, Y:[500,600,520]->510)
        # 提取所有有效的坐标
        coords_x = []  # x的坐标如[300,320,500]
        coords_y = []
        old_elements = []

        for r in ok_responses:
            element = r.action_obj.get("element")
            old_elements.append(element)
            if isinstance(element, list) and len(element) >= 2:
                coords_x.append(float(element[0]))
                coords_y.append(float(element[1]))

        if len(coords_x) >= 2:
            # 逻辑：丢弃最大值，计算剩余的平均值
            def get_denoised_avg(data_list):
                if not data_list: return 0
                if len(data_list) == 1: return data_list[0]

                sorted_data = sorted(data_list)
                # 丢弃最大值（最后一个）
                trimmed_data = sorted_data[:-1]
                return sum(trimmed_data) / len(trimmed_data)

            avg_x = get_denoised_avg(coords_x)
            avg_y = get_denoised_avg(coords_y)

            # 构建最终返回对象
            # 深拷贝第一个 OK 的响应，防止修改原始数据
            best_res = copy.deepcopy(ok_responses[0])  # 到5. 坐标去噪,只有全部是 tap类型才可能.非 do,和非 tap都返回了
            best_res.action_obj["element"] = [int(avg_x), int(avg_y)]

            # 同步更新 action 字符串描述（可选，保持数据一致性）
            new_coords_str = f"({int(avg_x)}, {int(avg_y)})"
            # 假设原始 action 是 do(action=Tap(element=[x, y]))
            # 这里进行简单的字符串替换，或者重新生成
            best_res.action = f"do(action=Tap(element=[{int(avg_x)}, {int(avg_y)}]))"
            best_res.action_obj["old_elements"] = old_elements  # 方便排错,保留原始坐标数据
            return best_res

        return ok_responses[0]

    def request_n(self, messages: list[dict[str, Any]], n: int = 3, text_content=None) -> list[ModelResponse]:
        """并行请求 n 次，仅展示第一次请求的流式输出"""
        """
            并行请求 n 次。
            策略：等待最多 15 秒。如果 15 秒后收集到 >= 2 个结果，则提前返回，忽略慢请求。
            """

        # 定义配置常量 (也可以提取为参数)
        SOFT_TIMEOUT = 10  # 软截止时间10秒
        MIN_REQUIRED = 2  # 最小需要成功的数量

        def safe_request(index: int):
            # 只有第一个请求 (index 0) 不是 silent 模式
            # 这样用户能看到其中一个模型的“思考过程”，而不会导致终端混乱
            is_print = index == 0
            if is_print:
                print(f"\n[Parallel] 发起 {n} 路并行请求，正在展示第 1 路的实时思考...\n")

            response = self.model_client.request(self._context, is_print=is_print)
            # 能并行的都并行
            #1.保存log,json到文件
            self.log_model_message(response, index, text_content)
            #2.解析action字符串到action dict方便后续使用
            parse_action_ok = True
            # Parse action from response
            try:
                # print(f"Response:\n{response}\nResponse end")
                action = parse_action(response.action)  # 从 action字符串解析 action对象
                response.action_obj = action
            except ValueError as e:
                if self.agent_config.verbose:
                    traceback.print_exc()
                # action解析错误
                parse_action_ok = False
            response.parse_action_ok=parse_action_ok
            return response

        results = []

        # 【核心修改 1】手动创建 Executor，不使用 with 上下文管理器
        executor = ThreadPoolExecutor(max_workers=n)
        try:
            # 1. 提交所有任务，获取 Future 对象列表
            futures = [executor.submit(safe_request, i) for i in range(n)]

            # 2. 第一次等待：设置 15 秒超时
            # return_when=ALL_COMPLETED 意为“在这个时间内，尽量等所有完成”
            # 如果超时，它会返回当前已完成的任务集合 (done) 和未完成的集合 (not_done)
            done, not_done = wait(futures, timeout=SOFT_TIMEOUT, return_when=ALL_COMPLETED)

            # 3. 检查是否满足“提前返回”条件
            if len(done) >= MIN_REQUIRED:
                # A情况：已经有 >= 2 个结果，且时间可能已经过了 15s (或者全都在 15s 内完成了)
                # 动作：直接取结果，放弃 not_done
                pass
            else:
                # B情况：15秒到了，但是完成的还不到 2 个 (遇到了极端的整体延迟)
                # 动作：我们需要继续等待，直到满足最小数量 (或者你可以选择在这里抛出超时异常)
                print(f"[Parallel] 10s超时，仅获取 {len(done)} 个结果，继续等待直到满足 {MIN_REQUIRED} 个...")

                # 继续等待剩下的任务，直到有新的任务完成
                # 这里使用了循环来逐个获取，直到凑够数
                while len(done) < MIN_REQUIRED and not_done:
                    # 等待任意一个完成
                    new_done, not_done = wait(not_done, return_when=FIRST_COMPLETED)
                    done.update(new_done)

            # 4. 收集结果
            # 注意：done 是无序的集合。如果必须保持 index=0,1,2 的顺序，需要做额外处理。
            # 这里假设只要拿到结果就行，顺序不重要。
            for f in done:
                try:
                    results.append(f.result())
                except Exception as e:
                    print(f"Task failed: {e}")

            # 5. (可选) 取消剩下的慢请求，节省资源
            # 注意：Python线程很难强制杀死，但 cancel() 可以阻止尚未开始的任务运行
            for f in not_done:
                f.cancel()
        finally:
            # 【核心修改 3】关键！wait=False
            # 告诉 Python: "不要等后台那些慢线程了，直接向下执行，让它们自生自灭"
            # 这样如果软超时时间已到并且完成了两个，主程序直接 return，
            # 那个 20s 的线程会在后台默默跑完，不会拖慢主程序。
            executor.shutdown(wait=False)
        return results

    def _execute_step(
        self, user_prompt: str | None = None, is_first: bool = False,image_save_path: str = ""
    ) -> StepResult:
        """Execute a single step of the agent loop."""
        self._step_count += 1

        # Capture current screen state
        device_factory = get_device_factory()
        current_time = datetime.now()
        formatted_time = current_time.strftime(
            f'%Y-%m-%d_%H-%M-%S_{str(uuid.uuid4().hex[:8])}')
        # # 格式1：2026-02-04_15-30-20（基础版，可读性最佳）
        #  strftime("%Y-%m-%d_%H-%M-%S") 截图文件名加入时分秒,同时看时分秒,同时后面当天秒的整数方便计算下一步耗时多少
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
            # response = self.model_client.request(self._context,is_print=False)
            responses = self.request_n(self._context,n = 3, text_content=text_content)
            response = self.get_best_response(responses)
            print(f"response json:\n{json.dumps(vars(response), indent=2, ensure_ascii=False)}\nresponse end")

        except Exception as e:
            if self.agent_config.verbose:
                traceback.print_exc()
            return StepResult(
                success=False,
                finished=False,
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
            if response.parse_action_ok:
                action = response.action_obj
            else:
                action = parse_action(response.action)  # 从 action字符串解析 action对象
            self._parse_action_error_count = 0
            if self.agent_config.verbose: #解析成功才打印
                # Print thinking process
                print("-" * 50)  # --------------------------------------------------
                print(f"🎯 {msgs['action']}:")  # 🎯 执行动作:
                print(json.dumps(action, ensure_ascii=False, indent=2))
                print("=" * 50 + "\n")
        except ValueError as e:
            if self.agent_config.verbose:
                traceback.print_exc()
            # action解析错误
            parse_action_ok = False
            self._parse_action_error_count += 1
            parse_action_error_log =f"parse_action_error response.action {response.action}"
            self._error_log.append({"type": "parse_action_error", "text": parse_action_error_log})
            if self._parse_action_error_count > self.agent_config.max_parse_action_error:
                #超过3次直接标记完成
                action = finish(message=parse_action_error_log)  # 解析错误生成一个空message的 finish.
            else:
                #不超过3次继续执行下一次 step
                return StepResult(
                    success=False,
                    finished=False,
                    action=None,
                    thinking="",
                    message=f"parse_action_error: {e}",
                )

        # Execute action
        if parse_action_ok or self._parse_action_error_count > self.agent_config.max_parse_action_error: #解析成功,或者错误大于 3 次
            #1.执行action
            try:
                result = self.action_handler.execute(
                    action, screenshot.width, screenshot.height, self._step_count
                )
            except Exception as e:
                if self.agent_config.verbose:
                    traceback.print_exc()
                result = self.action_handler.execute(
                    finish(message=str(e)), screenshot.width, screenshot.height, self._step_count
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


        # Check if finished 3.答应完成
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
            message=result.message or action.get("message"),#正常情况执行结果 result没有message,除非执行敏感操作错误.
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

    def run_step_replay_return1(
            self, user_prompt: str | None = None, is_first: bool = False, image_save_path: str = "",data_path: str = ""
    )-> ModelResponse:
        """Execute a single step of the agent loop."""
        self._step_count += 1

        # Capture current screen state
        # device_factory = get_device_factory()
        current_time = datetime.now()
        formatted_time = current_time.strftime(
            f'%Y-%m-%d_%H-%M-%S_{str(uuid.uuid4().hex[:8])}')
        # # 格式1：2026-02-04_15-30-20（基础版，可读性最佳）
        #  strftime("%Y-%m-%d_%H-%M-%S") 截图文件名加入时分秒,同时看时分秒,同时后面当天秒的整数方便计算下一步耗时多少
        local_image_dir = os.path.join(image_save_path, f"screenshot_{formatted_time}_{self._step_count}.png")
        # screenshot = device_factory.get_screenshot(self.agent_config.device_id, 10, local_image_dir=local_image_dir)
        # current_app = device_factory.get_current_app(self.agent_config.device_id)

        #加载 json文件的 context到self._context变量.
        # 严格判断：如果目录已存在，强制停止程序，防止数据覆盖或混淆
        print(f"data_path: {data_path}")
        if not os.path.exists(data_path):
            print(f"🛑 停止运行: 文件 {data_path} 不存在。")
            sys.exit(1)

        try:
            with open(data_path, "r", encoding="UTF-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"错误：文件 {data_path} 不存在")
            data = None  # 或根据业务逻辑处理
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"错误：文件 {data_path} 不是合法的 JSON 格式")
            data = None
            sys.exit(1)

        # message_data = {
        #     "name": "manager",
        #     "messages": self._context,
        #     "response": self.safe_serialize(response),
        #     "step_id": self._step_count,
        #     "total_time": response.total_time,
        # }
        action_name = "messages"
        if "messages" in data:
            # 执行已有脚本
            # print(f"有数据, messages")
            action_object = data[action_name]
            self._context = action_object
            # print(f"shortcuts: {data}")
        else:
            # TODO 1.打开打车应用 调用模型生成脚本
            print(f"🛑 停止运行: 字段 messages 不存在。")
            sys.exit(1)


        # Get model response
        try:
            msgs = get_messages(self.agent_config.lang)
            print("\n" + "=" * 50)  # --------------------------------------------------
            print(f"💭 {msgs['thinking']}:")  # 💭 思考过程: request中会答应思考过程,出错会是空
            print("-" * 50)
            response = self.model_client.request(self._context,is_print=False) #重放错误请求,不做并发多次尝试
            # responses = self.request_n(self._context, n=3, text_content=text_content)
            # response = self.get_best_response(responses)
            # print(f"response json:\n{json.dumps(vars(response), indent=2, ensure_ascii=False)}\nresponse end")

            # 2.解析
            parse_action_ok = True
            # Parse action from response
            try:
                # print(f"Response:\n{response}\nResponse end")  "action": "do(action=\"Tap\", element=[272,509])",
                action = parse_action(response.action)  # 从 action字符串解析 action对象
                response.action_obj = action
            except ValueError as e:
                if self.agent_config.verbose:
                    traceback.print_exc()
                # action解析错误
                parse_action_ok = False

            response.parse_action_ok = parse_action_ok
            print(f"response json:\n{json.dumps(vars(response), indent=2, ensure_ascii=False)}\nresponse end")
            return response
        except Exception as e:
            if self.agent_config.verbose:
                traceback.print_exc()
            raise e
