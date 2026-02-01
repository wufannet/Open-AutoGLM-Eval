# 从dataclasses模块导入dataclass和field装饰器，用于创建数据类
from dataclasses import dataclass, field
# 从abc模块导入ABC（抽象基类）和abstractmethod装饰器，用于定义抽象类和抽象方法
from abc import ABC, abstractmethod
# 重复导入dataclasses模块（可能是代码冗余，实际可只导入一次）
from dataclasses import dataclass, field
# 导入re模块，用于正则表达式操作
import re


# 定义InfoPool数据类，用于存储所有代理之间共享的信息
@dataclass
class InfoPool:
    """跟踪所有代理之间的所有信息。"""

    # 用户输入/累积的知识
    instruction: str = ""  # 用户指令
    task_name: str = ""  # 任务名称
    additional_knowledge_manager: str = ""  # 给Manager的额外知识
    additional_knowledge_executor: str = ""  # 给Executor的额外知识
    add_info_token = "[add_info]"  # 额外信息标记

    ui_elements_list_before: str = ""  # 操作前的UI元素列表（带索引）
    ui_elements_list_after: str = ""  # 操作后的UI元素列表（带索引）
    action_pool: list = field(default_factory=list)  # 动作池

    # 工作记忆
    summary_history: list = field(default_factory=list)  # 动作描述列表
    action_history: list = field(default_factory=list)  # 动作列表
    action_outcomes: list = field(default_factory=list)  # 动作结果列表
    error_descriptions: list = field(default_factory=list)  # 错误描述列表

    last_summary: str = ""  # 最后一个动作的描述
    last_action: str = ""  # 最后一个动作
    last_action_thought: str = ""  # 最后一个动作的思考过程
    important_notes: str = ""  # 重要笔记

    error_flag_plan: bool = False  # 标记计划是否多次尝试未解决错误
    error_description_plan: bool = False  # 用于修改计划的错误解释

    # 计划相关
    plan: str = ""  # 计划内容
    completed_plan: str = ""  # 已完成的计划内容
    progress_status: str = ""  # 进度状态 #为什么有两个变量, 完成计划和进度状态有什么区别
    progress_status_history: list = field(default_factory=list)  # 进度状态历史
    finish_thought: str = ""  # 完成思考
    current_subgoal: str = ""  # 当前子目标
    err_to_manager_thresh: int = 2  # 向管理器报告错误的阈值

    # 未来任务
    future_tasks: list = field(default_factory=list)  # 未来任务列表


# 定义BaseAgent抽象基类，所有代理类的父类
class BaseAgent(ABC):
    # 抽象方法：获取提示信息，子类必须实现,请求提示词封装
    @abstractmethod
    def get_prompt(self, info_pool: InfoPool) -> str:
        pass

    # 抽象方法：解析响应结果，子类必须实现,这个相当于java直接定义实体类解析返回的str到biz业务对象.
    @abstractmethod
    def parse_response(self, response: str) -> dict:
        pass


# 定义Manager类，继承自BaseAgent，负责跟踪进度和制定高层计划
class Manager(BaseAgent):

    # 实现get_prompt方法，生成给Manager的提示信息
    def get_prompt(self, info_pool: InfoPool) -> str:
        # 初始化提示信息，说明Manager的角色和目标
        prompt = "You are an agent who can operate an Android phone on behalf of a user. Your goal is to track progress and devise high-level plans to achieve the user's requests.\n\n"
        # 中文翻译：你是一个可以代表用户操作Android手机的代理。你的目标是跟踪进度并制定高层计划以实现用户的请求。

        # 添加用户请求部分
        prompt += "### User Request ###\n"
        # 中文翻译：### 用户请求 ###
        prompt += f"{info_pool.instruction}\n\n"

        # 根据任务类型设置特定备注
        task_specific_note = ""
        if ".html" in info_pool.instruction:
            task_specific_note = "NOTE: The .html file may contain additional interactable elements, such as a drawing canvas or a game. Do not open other apps without completing the task in the .html file."
            # 中文翻译：注意：.html文件可能包含额外的可交互元素，如绘图画布或游戏。在完成.html文件中的任务之前，不要打开其他应用。
        elif "Audio Recorder" in info_pool.instruction:
            task_specific_note = "NOTE: The stop recording icon is a white square, located fourth from the left at the bottom. Please do not click the circular pause icon in the middle."
            # 中文翻译：注意：停止录音图标是一个白色方块，位于底部从左数第四个位置。请不要点击中间的圆形暂停图标。

        # 如果是第一次制定计划（计划为空）
        if info_pool.plan == "":
            # 首次计划的提示内容
            prompt += "---\n"
            # 中文翻译：---
            prompt += "Make a high-level plan to achieve the user's request. If the request is complex, break it down into subgoals. The screenshot displays the starting state of the phone.\n"
            # 中文翻译：制定一个高层计划来实现用户的请求。如果请求很复杂，将其分解为子目标。截图显示了手机的初始状态。
            prompt += "IMPORTANT: For requests that explicitly require an answer, always add 'perform the `answer` action' as the last step to the plan!\n\n"
            # 中文翻译：重要：对于明确需要回答的请求，务必在计划的最后一步添加"执行`answer`动作"！

            # 添加任务特定备注（如果有）
            if task_specific_note != "":
                prompt += f"{task_specific_note}\n\n"

            # 添加指导原则
            prompt += "### Guidelines ###\n"
            # 中文翻译：### 指导原则 ###
            prompt += "The following guidelines will help you plan this request.\n"
            # 中文翻译：以下指导原则将帮助你规划此请求。
            prompt += "General:\n"
            # 中文翻译：通用：
            prompt += "Use search to quickly find a file or entry with a specific name, if search function is applicable.\n"
            # 中文翻译：如果适用，使用搜索功能快速查找具有特定名称的文件或条目。
            prompt += "Task-specific:\n"
            # 中文翻译：任务特定：
            # 添加给Manager的额外知识（如果有）
            if info_pool.additional_knowledge_manager != "":
                prompt += f"{info_pool.additional_knowledge_manager}\n\n"
            else:
                prompt += f"{info_pool.add_info_token}\n\n"
                # 中文翻译：[add_info]

            # 规定输出格式
            prompt += "Provide your output in the following format which contains two parts:\n"
            # 中文翻译：请以下列包含两部分的格式提供你的输出：
            prompt += "### Thought ###\n"
            # 中文翻译：### 思考 ###
            prompt += "A detailed explanation of your rationale for the plan and subgoals.\n\n"
            # 中文翻译：对你的计划和子目标的详细解释。
            prompt += "### Plan ###\n"
            # 中文翻译：### 计划 ###
            prompt += "1. first subgoal\n"
            # 中文翻译：1. 第一个子目标
            prompt += "2. second subgoal\n"
            # 中文翻译：2. 第二个子目标
            prompt += "...\n"
            # 中文翻译：...
        else:
            # 非首次计划（已有计划），需要更新计划
            # 添加已完成的操作历史
            if info_pool.completed_plan != "No completed subgoal.":
                prompt += "### Historical Operations ###\n"
                # 中文翻译：### 历史操作 ###
                prompt += "Operations that have been completed before:\n"
                # 中文翻译：之前已经完成的操作：
                prompt += f"{info_pool.completed_plan}\n\n"
            # 添加当前计划
            prompt += "### Plan ###\n"
            # 中文翻译：### 计划 ###
            prompt += f"{info_pool.plan}\n\n"
            # 添加最后一个动作
            prompt += f"### Last Action ###\n"
            # 中文翻译：### 最后一个动作 ###
            prompt += f"{info_pool.last_action}\n\n"
            # 添加最后一个动作的描述
            prompt += f"### Last Action Description ###\n"
            # 中文翻译：### 最后一个动作描述 ###
            prompt += f"{info_pool.last_summary}\n\n"
            # 添加重要笔记
            prompt += "### Important Notes ###\n"
            # 中文翻译：### 重要笔记 ###
            if info_pool.important_notes != "":
                prompt += f"{info_pool.important_notes}\n\n"
            else:
                prompt += "No important notes recorded.\n\n"
                # 中文翻译：没有记录重要笔记。

            # 添加指导原则
            prompt += "### Guidelines ###\n"
            # 中文翻译：### 指导原则 ###
            prompt += "The following guidelines will help you plan this request.\n"
            # 中文翻译：以下指导原则将帮助你规划此请求。
            prompt += "General:\n"
            # 中文翻译：通用：
            prompt += "Use search to quickly find a file or entry with a specific name, if search function is applicable.\n"
            # 中文翻译：如果适用，使用搜索功能快速查找具有特定名称的文件或条目。
            prompt += "Task-specific:\n"
            # 中文翻译：任务特定：
            if info_pool.additional_knowledge_manager != "":
                prompt += f"{info_pool.additional_knowledge_manager}\n\n"
            else:
                prompt += f"{info_pool.add_info_token}\n\n"
                # 中文翻译：[add_info]

            # 如果有计划错误标记，添加错误信息
            if info_pool.error_flag_plan:
                prompt += "### Potentially Stuck! ###\n"
                # 中文翻译：### 可能卡住了！ ###
                prompt += "You have encountered several failed attempts. Here are some logs:\n"
                # 中文翻译：你已经遇到了几次失败的尝试。以下是一些日志：
                k = info_pool.err_to_manager_thresh
                recent_actions = info_pool.action_history[-k:]
                recent_summaries = info_pool.summary_history[-k:]
                recent_err_des = info_pool.error_descriptions[-k:]
                # 拼接最近的错误尝试记录
                for i, (act, summ, err_des) in enumerate(zip(recent_actions, recent_summaries, recent_err_des)):
                    prompt += f"- Attempt: Action: {act} | Description: {summ} | Outcome: Failed | Feedback: {err_des}\n"

            # 添加计划更新的指示
            prompt += "---\n"
            # 中文翻译：---
            prompt += "Carefully assess the current status and the provided screenshot. Check if the current plan needs to be revised.\n Determine if the user request has been fully completed. If you are confident that no further actions are required, mark the plan as \"Finished\" in your output. If the user request is not finished, update the plan. If you are stuck with errors, think step by step about whether the overall plan needs to be revised to address the error.\n"
            # 中文翻译：仔细评估当前状态和提供的截图。检查当前计划是否需要修订。确定用户请求是否已完全完成。如果你确信不需要进一步的操作，请在输出中将计划标记为"Finished"。如果用户请求尚未完成，请更新计划。如果你因错误而卡住，请逐步思考是否需要修订整体计划来解决错误。
            prompt += "NOTE: 1. If the current situation prevents proceeding with the original plan or requires clarification from the user, make reasonable assumptions and revise the plan accordingly. Act as though you are the user in such cases. 2. Please refer to the helpful information and steps in the Guidelines first for planning. 3. If the first subgoal in plan has been completed, please update the plan in time according to the screenshot and progress to ensure that the next subgoal is always the first item in the plan. 4. If the first subgoal is not completed, please copy the previous round's plan or update the plan based on the completion of the subgoal.\n"
            # 中文翻译：注意：1. 如果当前情况阻止继续执行原始计划或需要用户澄清，请做出合理假设并相应地修订计划。在这种情况下，要像用户一样思考。2. 请首先参考指导原则中的有用信息和步骤进行规划。3. 如果计划中的第一个子目标已经完成，请根据截图和进度及时更新计划，确保下一个子目标始终是计划中的第一项。4. 如果第一个子目标未完成，请复制上一轮的计划或根据子目标的完成情况更新计划。
            prompt += "IMPORTANT: If the next steps require an `answer` action, make sure that there is a plan to perform the `answer` action. In this case, you should not mark the plan as \"Finished\" unless the last action is `answer`.\n"
            # 中文翻译：重要：如果下一步需要`answer`动作，请确保有执行`answer`动作的计划。在这种情况下，除非最后一个动作是`answer`，否则不应将计划标记为"Finished"。
            # 添加任务特定备注（如果有）
            if task_specific_note != "":
                prompt += f"{task_specific_note}\n\n"

            # 规定输出格式
            prompt += "Provide your output in the following format, which contains three parts:\n\n"
            # 中文翻译：请以下列包含三部分的格式提供你的输出：
            prompt += "### Thought ###\n"
            # 中文翻译：### 思考 ###
            prompt += "An explanation of your rationale for the updated plan and current subgoal.\n\n"
            # 中文翻译：对你更新后的计划和当前子目标的解释。
            prompt += "### Historical Operations ###\n"
            # 中文翻译：### 历史操作 ###
            prompt += "Try to add the most recently completed subgoal on top of the existing historical operations. Please do not delete any existing historical operation. If there is no newly completed subgoal, just copy the existing historical operations.\n\n"
            # 中文翻译：尝试在现有历史操作的顶部添加最近完成的子目标。请不要删除任何现有的历史操作。如果没有新完成的子目标，只需复制现有的历史操作。
            prompt += "### Plan ###\n"
            # 中文翻译：### 计划 ###
            prompt += "Please update or copy the existing plan according to the current page and progress. Please pay close attention to the historical operations. Please do not repeat the plan of completed content unless you can judge from the screen status that a subgoal is indeed not completed.\n"
            # 中文翻译：请根据当前页面和进度更新或复制现有计划。请注意历史操作。除非你能从屏幕状态判断某个子目标确实未完成，否则请不要重复已完成内容的计划。

        return prompt

    # 实现parse_response方法，解析Manager的响应  t是第一部分,h是第二部分,p是第三部分
    def parse_response(self, response: str) -> dict:
        # 提取思考过程、已完成子目标和计划
        if "### Historical Operations" in response:
            # 有历史操作,也就是完成计划, 先截取t后面,然后再对这部分截取h前面.
            thought = response.split("### Thought")[-1].split("### Historical Operations")[0].replace("\n",
                                                                                                      " ").replace("  ",
                                                                                                                   " ").replace(
                "###", "").strip()
            # 截取h标记后面的,plan标记前面的历史操作,就是完成子目标,也就是完成计划.
            completed_subgoal = response.split("### Historical Operations")[-1].split("### Plan")[0].replace("\n",
                                                                                                             " ").replace(
                "  ", " ").replace("###", "").strip()
        else:
            thought = response.split("### Thought")[-1].split("### Plan")[0].replace("\n", " ").replace("  ",
                                                                                                        " ").replace(
                "###", "").strip()
            completed_subgoal = "No completed subgoal."
        # plan 是最后一部分,     为什么不直接用###切分,也一样
        plan = response.split("### Plan")[-1].replace("\n", " ").replace("  ", " ").replace("###", "").strip()
        return {"thought": thought, "completed_subgoal": completed_subgoal, "plan": plan}


# 从工具模块导入原子动作相关常量
from utils.new_json_action import *

# 定义原子动作的签名（无XML相关），包含参数和描述
ATOMIC_ACTION_SIGNITURES_noxml = {
    ANSWER: {
        "arguments": ["text"],
        "description": lambda
            info: "Answer user's question. Usage example: {\"action\": \"answer\", \"text\": \"the content of your answer\"}"
        # 中文翻译：回答用户的问题。使用示例：{"action": "answer", "text": "你的回答内容"}
    },
    CLICK: {
        "arguments": ["coordinate"],
        "description": lambda
            info: "Click the point on the screen with specified (x, y) coordinates. Usage Example: {\"action\": \"click\", \"coordinate\": [x, y]}"
        # 中文翻译：点击屏幕上具有指定(x, y)坐标的点。使用示例：{"action": "click", "coordinate": [x, y]}
    },
    LONG_PRESS: {
        "arguments": ["coordinate"],
        "description": lambda
            info: "Long press on the position (x, y) on the screen. Usage Example: {\"action\": \"long_press\", \"coordinate\": [x, y]}"
        # 中文翻译：长按屏幕上的位置(x, y)。使用示例：{"action": "long_press", "coordinate": [x, y]}
    },
    TYPE: {
        "arguments": ["text"],
        "description": lambda
            info: "Type text into current activated input box or text field. If you have activated the input box, you can see the words \"ADB Keyboard {on}\" at the bottom of the screen. If not, click the input box to confirm again. Please make sure the correct input box has been activated before typing. Usage Example: {\"action\": \"type\", \"text\": \"the text you want to type\"}"
        # 中文翻译：在当前激活的输入框或文本字段中输入文本。如果你已激活输入框，可以在屏幕底部看到"ADB Keyboard {on}"字样。如果没有，请再次点击输入框确认。请确保在打字前已激活正确的输入框。使用示例：{"action": "type", "text": "你想要输入的文本"}
    },
    SYSTEM_BUTTON: {
        "arguments": ["button"],
        "description": lambda
            info: "Press a system button, including back, home, and enter. Usage example: {\"action\": \"system_button\", \"button\": \"Home\"}"
        # 中文翻译：按下系统按钮，包括返回、主页和回车。使用示例：{"action": "system_button", "button": "Home"}
    },
    SWIPE: {
        "arguments": ["coordinate", "coordinate2"],
        "description": lambda
            info: "Scroll from the position with coordinate to the position with coordinate2. Please make sure the start and end points of your swipe are within the swipeable area and away from the keyboard (y1 < 1400). Usage Example: {\"action\": \"swipe\", \"coordinate\": [x1, y1], \"coordinate2\": [x2, y2]}"
        # 中文翻译：从coordinate位置滚动到coordinate2位置。请确保滑动的起点和终点在可滑动区域内且远离键盘(y1 < 1400)。使用示例：{"action": "swipe", "coordinate": [x1, y1], "coordinate2": [x2, y2]}
    }
}

# 输入相关知识：关于输入框激活状态的说明
INPUT_KNOW = "If you've activated an input field, you'll see \"ADB Keyboard {on}\" at the bottom of the screen. This phone doesn't display a soft keyboard. So, if you see \"ADB Keyboard {on}\" at the bottom of the screen, it means you can type. Otherwise, you'll need to tap the correct input field to activate it."


# 中文翻译：如果你已激活输入字段，可以在屏幕底部看到"ADB Keyboard {on}"。这部手机不显示软键盘。所以，如果你在屏幕底部看到"ADB Keyboard {on}"，意味着你可以打字。否则，你需要点击正确的输入字段来激活它。

# 定义Executor类，继承自BaseAgent，负责决定下一步具体动作
class Executor(BaseAgent):

    # 实现get_prompt方法，生成给Executor的提示信息
    def get_prompt(self, info_pool: InfoPool) -> str:
        # 初始化提示信息，说明Executor的角色和目标
        prompt = "You are an agent who can operate an Android phone on behalf of a user. Your goal is to decide the next action to perform based on the current state of the phone and the user's request.\n\n"
        # 中文翻译：你是一个可以代表用户操作Android手机的代理。你的目标是根据手机的当前状态和用户的请求决定下一步要执行的动作。

        # 添加用户请求
        prompt += "### User Request ###\n"
        # 中文翻译：### 用户请求 ###
        prompt += f"{info_pool.instruction}\n\n"

        # 添加整体计划
        prompt += "### Overall Plan ###\n"
        # 中文翻译：### 整体计划 ###
        prompt += f"{info_pool.plan}\n\n"

        # 添加当前子目标（截取计划的前4个子目标）
        prompt += "### Current Subgoal ###\n"
        # 中文翻译：### 当前子目标 ###
        current_goal = info_pool.plan
        current_goal = re.split(r'(?<=\d)\. ', current_goal)
        truncated_current_goal = ". ".join(current_goal[:4]) + '.'
        truncated_current_goal = truncated_current_goal[:-2].strip()
        prompt += f"{truncated_current_goal}\n\n"

        # 添加进度状态
        prompt += "### Progress Status ###\n"
        # 中文翻译：### 进度状态 ###
        if info_pool.progress_status != "": #
            prompt += f"{info_pool.progress_status}\n\n"
        else:
            prompt += "No progress yet.\n\n" #进度状态 1.第一次请求规划,进度状态没有进度 # 第二次也没有进度,因为这个是在第二次反思调用后才赋值为info_pool.completed_plan
            # 中文翻译：尚未有进度。

        # 添加给Executor的额外知识（如果有）
        if info_pool.additional_knowledge_executor != "":
            prompt += "### Guidelines ###\n"
            # 中文翻译：### 指导原则 ###
            prompt += f"{info_pool.additional_knowledge_executor}\n"

        # 添加特定任务的指导原则
        if "exact duplicates" in info_pool.instruction:
            prompt += "Task-specific:\nOnly two items with the same name, date, and details can be considered duplicates.\n\n"
            # 中文翻译：任务特定：只有名称、日期和详情都相同的两个项目才能被视为重复项。
        elif "Audio Recorder" in info_pool.instruction:
            prompt += "Task-specific:\nThe stop recording icon is a white square, located fourth from the left at the bottom. Please do not click the circular pause icon in the middle.\n\n"
            # 中文翻译：任务特定：停止录音图标是一个白色方块，位于底部从左数第四个位置。请不要点击中间的圆形暂停图标。
        else:
            prompt += "\n"

        # 添加动作选择指示
        prompt += "---\n"
        # 中文翻译：---
        prompt += "Carefully examine all the information provided above and decide on the next action to perform. If you notice an unsolved error in the previous action, think as a human user and attempt to rectify them. You must choose your action from one of the atomic actions.\n\n"
        # 中文翻译：仔细检查以上提供的所有信息，并决定下一步要执行的动作。如果你注意到上一个动作中有未解决的错误，请像人类用户一样思考并尝试纠正它们。你必须从原子动作中选择一个动作。

        # 列出可用的原子动作
        prompt += "#### Atomic Actions ####\n"
        # 中文翻译：#### 原子动作 ####
        prompt += "The atomic action functions are listed in the format of `action(arguments): description` as follows:\n"
        # 中文翻译：原子动作函数以下列格式列出：`action(arguments): description`：

        for action, value in ATOMIC_ACTION_SIGNITURES_noxml.items():
            prompt += f"- {action}({', '.join(value['arguments'])}): {value['description'](info_pool)}\n"

        prompt += "\n"
        # 添加最近的动作历史
        prompt += "### Latest Action History ###\n"
        # 中文翻译：### 最近动作历史 ###
        if info_pool.action_history != []:
            prompt += "Recent actions you took previously and whether they were successful:\n"
            # 中文翻译：你之前执行的最近动作及其是否成功：
            num_actions = min(5, len(info_pool.action_history)) #最多5条
            latest_actions = info_pool.action_history[-num_actions:]
            latest_summary = info_pool.summary_history[-num_actions:]
            latest_outcomes = info_pool.action_outcomes[-num_actions:]
            error_descriptions = info_pool.error_descriptions[-num_actions:]
            action_log_strs = []
            # 拼接最近的动作记录（包含结果和错误描述）
            for act, summ, outcome, err_des in zip(latest_actions, latest_summary, latest_outcomes, error_descriptions):
                if outcome == "A":
                    action_log_str = f"Action: {act} | Description: {summ} | Outcome: Successful\n"
                    # 中文翻译：动作：{act} | 描述：{summ} | 结果：成功
                else:
                    action_log_str = f"Action: {act} | Description: {summ} | Outcome: Failed | Feedback: {err_des}\n"
                    # 中文翻译：动作：{act} | 描述：{summ} | 结果：失败 | 反馈：{err_des}
                prompt += action_log_str
                action_log_strs.append(action_log_str)

            prompt += "\n"
        else:
            prompt += "No actions have been taken yet.\n\n"
            # 中文翻译：尚未执行任何动作。

        # 添加重要提示
        prompt += "---\n"
        # 中文翻译：---
        prompt += "IMPORTANT:\n1. Do NOT repeat previously failed actions multiple times. Try changing to another action.\n"
        # 中文翻译：重要：1. 不要多次重复之前失败的动作。尝试改为其他动作。
        prompt += "2. Please prioritize the current subgoal.\n\n"
        # 中文翻译：2. 请优先考虑当前子目标。
        # 规定输出格式
        prompt += "Provide your output in the following format, which contains three parts:\n"
        # 中文翻译：请以下列包含三部分的格式提供你的输出：
        prompt += "### Thought ###\n"
        # 中文翻译：### 思考 ###
        prompt += "Provide a detailed explanation of your rationale for the chosen action.\n\n"
        # 中文翻译：提供你选择该动作的详细理由解释。

        prompt += "### Action ###\n"
        # 中文翻译：### 动作 ###



        prompt += "Choose only one action or shortcut from the options provided.\n"
        # 中文翻译：从提供的选项中只选择一个动作或快捷方式。
        prompt += "You must provide your decision using a valid JSON format specifying the `action` and the arguments of the action. For example, if you want to type some text, you should write {\"action\":\"type\", \"text\": \"the text you want to type\"}.\n\n"
        # 中文翻译：你必须使用有效的JSON格式提供你的决定，指定`action`和动作的参数。例如，如果你想输入一些文本，你应该写{"action":"type", "text": "你想要输入的文本"}。

        prompt += "### Description ###\n"
        # 中文翻译：### 描述 ###
        prompt += "A brief description of the chosen action. Do not describe expected outcome.\n"
        # 中文翻译：所选动作的简要描述。不要描述预期结果。
        return prompt

    # 实现parse_response方法，解析Executor的响应
    def parse_response(self, response: str) -> dict:
        # 提取思考过程、动作和描述
        thought = response.split("### Thought")[-1].split("### Action")[0].replace("\n", " ").replace("  ",
                                                                                                      " ").replace(
            "###", "").strip()
        action = response.split("### Action")[-1].split("### Description")[0].replace("\n", " ").replace("  ",
                                                                                                         " ").replace(
            "###", "").strip()
        description = response.split("### Description")[-1].replace("\n", " ").replace("  ", " ").replace("###",
                                                                                                          "").strip()
        return {"thought": thought, "action": action, "description": description}


# 定义ActionReflector类，继承自BaseAgent，负责验证上一个动作的结果
class ActionReflector(BaseAgent):

    # 实现get_prompt方法，生成给ActionReflector的提示信息
    def get_prompt(self, info_pool: InfoPool) -> str:
        # 初始化提示信息，说明ActionReflector的角色和目标
        prompt = "You are an agent who can operate an Android phone on behalf of a user. Your goal is to verify whether the last action produced the expected behavior and to keep track of the overall progress.\n\n"
        # 中文翻译：你是一个可以代表用户操作Android手机的代理。你的目标是验证上一个动作是否产生了预期的行为，并跟踪整体进度。

        # 添加用户请求
        prompt += "### User Request ###\n"
        # 中文翻译：### 用户请求 ###
        prompt += f"{info_pool.instruction}\n\n"

        # 添加进度状态
        prompt += "### Progress Status ###\n"
        # 中文翻译：### 进度状态 ###
        if info_pool.completed_plan != "":
            prompt += f"{info_pool.completed_plan}\n\n"
        else:
            prompt += "No progress yet.\n\n"
            # 中文翻译：尚未有进度。

        # 添加动作结果验证的指示
        prompt += "---\n"
        # 中文翻译：---
        prompt += "The two attached images are phone screenshots taken before and after your last action. \n"
        # 中文翻译：附上的两张图片是在上一个动作之前和之后拍摄的手机截图。

        # 添加最近的动作信息
        prompt += "---\n"
        # 中文翻译：---
        prompt += "### Latest Action ###\n"
        # 中文翻译：### 最近动作 ###
        prompt += f"Action: {info_pool.last_action}\n"
        prompt += f"Expectation: {info_pool.last_summary}\n\n"

        # 添加结果判断的指示
        prompt += "---\n"
        # 中文翻译：---
        prompt += "Carefully examine the information provided above to determine whether the last action produced the expected behavior. If the action was successful, update the progress status accordingly. If the action failed, identify the failure mode and provide reasoning on the potential reason causing this failure.\n\n"
        # 中文翻译：仔细检查以上提供的信息，以确定上一个动作是否产生了预期的行为。如果动作成功，相应地更新进度状态。如果动作失败，识别失败模式并提供导致此失败的潜在原因的推理。
        prompt += "Note: For swiping to scroll the screen to view more content, if the content displayed before and after the swipe is exactly the same, the swipe is considered to be C: Failed. The last action produces no changes. This may be because the content has been scrolled to the bottom.\n\n"
        # 中文翻译：注意：对于滑动屏幕以查看更多内容的操作，如果滑动前后显示的内容完全相同，则该滑动被视为C:失败。上一个动作没有产生任何变化。这可能是因为内容已经滚动到底部。

        # 规定输出格式
        prompt += "Provide your output in the following format containing two parts:\n"
        # 中文翻译：请以下列包含两部分的格式提供你的输出：
        prompt += "### Outcome ###\n"
        # 中文翻译：### 结果 ###
        prompt += "Choose from the following options. Give your response as \"A\", \"B\" or \"C\":\n"
        # 中文翻译：从以下选项中选择。用"A"、"B"或"C"给出你的响应：
        prompt += "A: Successful or Partially Successful. The result of the last action meets the expectation.\n"
        # 中文翻译：A: 成功或部分成功。上一个动作的结果符合预期。
        prompt += "B: Failed. The last action results in a wrong page. I need to return to the previous state.\n"
        # 中文翻译：B: 失败。上一个动作导致错误页面。需要返回到之前的状态。
        prompt += "C: Failed. The last action produces no changes.\n\n"
        # 中文翻译：C: 失败。上一个动作没有产生任何变化。

        prompt += "### Error Description ###\n"
        # 中文翻译：### 错误描述 ###
        prompt += "If the action failed, provide a detailed description of the error and the potential reason causing this failure. If the action succeeded, put \"None\" here.\n"
        # 中文翻译：如果动作失败，提供错误的详细描述和导致此失败的潜在原因。如果动作成功，在此处填写"None"。

        return prompt

    # 实现parse_response方法，解析ActionReflector的响应
    def parse_response(self, response: str) -> dict:
        # 提取结果和错误描述
        outcome = response.split("### Outcome")[-1].split("### Error Description")[0].replace("\n", " ").replace("  ",
                                                                                                                 " ").replace(
            "###", "").strip()
        error_description = response.split("### Error Description")[-1].replace("\n", " ").replace("###", "").replace(
            "  ", " ").strip()
        return {"outcome": outcome, "error_description": error_description}


# 定义Notetaker类，继承自BaseAgent，负责记录与用户请求相关的重要内容
class Notetaker(BaseAgent):

    # 实现get_prompt方法，生成给Notetaker的提示信息
    def get_prompt(self, info_pool: InfoPool) -> str:
        # 初始化提示信息，说明Notetaker的角色和目标
        prompt = "You are a helpful AI assistant for operating mobile phones. Your goal is to take notes of important content relevant to the user's request.\n\n"
        # 中文翻译：你是一个用于操作手机的有用AI助手。你的目标是记录与用户请求相关的重要内容。

        # 添加用户请求
        prompt += "### User Request ###\n"
        # 中文翻译：### 用户请求 ###
        prompt += f"{info_pool.instruction}\n\n"

        # 添加进度状态
        prompt += "### Progress Status ###\n"
        # 中文翻译：### 进度状态 ###
        prompt += f"{info_pool.progress_status}\n\n"

        # 添加已有的重要笔记
        prompt += "### Existing Important Notes ###\n"
        # 中文翻译：### 现有重要笔记 ###
        if info_pool.important_notes != "":
            prompt += f"{info_pool.important_notes}\n\n"
        else:
            prompt += "No important notes recorded.\n\n"
            # 中文翻译：没有记录重要笔记。

        # 添加特定任务的记录指导原则
        if "transactions" in info_pool.instruction and "Simple Gallery" in info_pool.instruction:
            prompt += "### Guideline ###\nYou can only record the transaction information in DCIM, because the other transactions are irrelevant to the task.\n"
            # 中文翻译：### 指导原则 ### 你只能记录DCIM中的交易信息，因为其他交易与任务无关。
        elif "enter their product" in info_pool.instruction:
            prompt += "### Guideline ###\nPlease record the number that appears each time so that you can calculate their product at the end.\n"
            # 中文翻译：### 指导原则 ### 请记录每次出现的数字，以便在最后计算它们的乘积。

        # 添加笔记记录的指示
        prompt += "---\n"
        # 中文翻译：---
        prompt += "Carefully examine the information above to identify any important content on the current screen that needs to be recorded.\n"
        # 中文翻译：仔细检查以上信息，识别当前屏幕上需要记录的任何重要内容。
        prompt += "IMPORTANT:\nDo not take notes on low-level actions; only keep track of significant textual or visual information relevant to the user's request. Do not repeat user request or progress status. Do not make up content that you are not sure about.\n\n"
        # 中文翻译：重要：不要记录低级别动作的笔记；只跟踪与用户请求相关的重要文本或视觉信息。不要重复用户请求或进度状态。不要编造你不确定的内容。

        # 规定输出格式
        prompt += "Provide your output in the following format:\n"
        # 中文翻译：请以下列格式提供你的输出：
        prompt += "### Important Notes ###\n"
        # 中文翻译：### 重要笔记 ###
        prompt += "The updated important notes, combining the old and new ones. If nothing new to record, copy the existing important notes.\n"
        # 中文翻译：更新后的重要笔记，结合了旧的和新的内容。如果没有新内容需要记录，请复制现有的重要笔记。

        return prompt

    # 实现parse_response方法，解析Notetaker的响应
    def parse_response(self, response: str) -> dict:
        # 提取重要笔记
        important_notes = response.split("### Important Notes")[-1].replace("\n", " ").replace("  ", " ").replace("###",
                                                                                                                  "").strip()
        return {"important_notes": important_notes}