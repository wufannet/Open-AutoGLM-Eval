from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple, Optional, List

from phone_agent.actions import ActionResult
from phone_agent.model.client import MessageBuilder, ModelResponse

class ActionInterceptor(ABC):
    """
    动作拦截器抽象基类
    继承 ABC (Abstract Base Class) 表明这是一个抽象类，不能被直接实例化。
    """

    @abstractmethod
    def before_execute(
            self,
            action: Dict[str, Any],
            screen_width: int,
            screen_height: int,
            step_count: int,
            response : ModelResponse,
    ) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str],Optional[ActionResult]]:
        """
        [抽象方法] 处理拦截逻辑。

        任何继承 ActionInterceptor 的子类都严格要求必须实现这个方法。

        Args:
            action: 当前准备执行的动作字典
            screen_width: 屏幕宽度
            screen_height: 屏幕高度
            step_count: 当前执行的步数
            response: 模型方法对象

        Returns:
            - bool: 是否允许继续执行后面的拦截器 (True 为放行，False 为阻断)
            - List[dict]: 处理过后的 action 列表 (即使不修改，也需要用 [action] 包裹返回),三选一返回-1.执行修改后的操作
            - str: 拦截原因 (阻断时的错误信息，放行时为 None) 三选一返回-2.执行失败,立即任务完成,错误消息
            - ActionResult: 执行结果,如果不为null,不再执行 handler 三选一返回-3.自定义的执行结果
        """
        pass  # 抽象方法通常用 pass 占位