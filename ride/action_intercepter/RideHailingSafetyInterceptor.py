from phone_agent.action_intercepter import ActionInterceptor
from typing import Any, Dict, Tuple, Optional, List

from phone_agent.actions import ActionResult
from phone_agent.model.client import MessageBuilder, ModelResponse

class RideHailingSafetyInterceptor(ActionInterceptor):
    """打车安全风控拦截器"""


    # 必须实现 before_execute，否则该类也会变成抽象类且无法实例化
    def before_execute(
            self, action: Dict[str, Any], screen_width: int, screen_height: int, step_count: int,response : ModelResponse,
    ) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str],Optional[ActionResult]]:

        if action.get("action") == "Tap" and step_count > 2:
            element = action.get("element")
            if element and isinstance(element, list) and len(element) >= 2:
                abs_x, abs_y = element[0], element[1]
                if abs_x > 500 and abs_y > 850:
                    error_msg = "触发安全风控：打车呼叫错误,禁止执行打车呼叫区域的点击"
                    print(f"RideHailingSafetyInterceptor 拦截器 error_msg: {error_msg}")
                    actionResutl =  ActionResult(
                        # 现在我需要点击搜索按钮或者选择其中一个搜索结果。我应该点击右下角的"搜索"按钮来进行搜索。do(action="Tap", element=[848, 954])
                        success=False, #如果当做成功,只用改这个参数  #fix 打车错误的安全拦截器还是返回失败,方便记录错误和拍错,有输入法点击搜索的情况
                        # success=True, #在打车价格页面点击了打车,直接返回为完成完成,
                        should_finish=True,
                        # message="User cancelled sensitive operation 打车呼叫错误 ",
                        message=error_msg,
                    )
                    return False, None, error_msg,actionResutl

        return True, None, None,None