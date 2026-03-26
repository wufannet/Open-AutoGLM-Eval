import copy

from phone_agent.action_intercepter import ActionInterceptor
from typing import Any, Dict, Tuple, Optional, List

from phone_agent.actions import ActionResult
from phone_agent.model.client import MessageBuilder, ModelResponse

class RideDidiInterceptor(ActionInterceptor):
    """滴滴打车拦截器"""

    def __init__(self, start: str = "", destination: str = ""):
        """
        初始化拦截器
        :param start: 乘车起点
        :param destination: 乘车终点
        """
        super().__init__()  # 推荐调用父类初始化（尤其在多重继承或父类有初始化逻辑时）
        self.start = start
        self.destination = destination

    # 必须实现 before_execute，否则该类也会变成抽象类且无法实例化
    def before_execute(
            self, action: Dict[str, Any], screen_width: int, screen_height: int, step_count: int,response : ModelResponse,
    ) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str],Optional[ActionResult]]:
        #修改点击终点 为点击终点+type地址

        thinking_text = response.thinking or ""
        print(f"拦截器-终点拦截器进入 thinking_text:'{thinking_text}'")
        print(f"拦截器-终点拦截器进入 action:'{action}'")


        if action.get("action") == "Tap":
            element = action.get("element")
            if element and len(element) >= 2:
                x, y = element[0], element[1]
                abs_x, abs_y = element[0], element[1]

                #点击起点区域
                #element=[499,467])

                # 点击终点坐标修改
                # 现在我应该点击"输入目的地"这个搜索框。do(action="Tap", element=[272,524])
                # do(action="Tap", element=[499, 524]). 搜索框
                if abs_x > 200 and abs_x < 520 and abs_y > 500 and abs_y < 550 and  ( "搜索框" in thinking_text or "输入目的地" in thinking_text ) :
                    modified_action = copy.deepcopy(action)
                    new_x = 272  # 假设模型输出的是 0-1000 相对坐标
                    new_y = 524
                    modified_action["element"] = [new_x, new_y]
                    if(new_x != abs_x and new_y != abs_y):
                        print(f"拦截器 点击终点坐标修改: ({x},{y}) -> ({new_x},{new_y})")

                    # "action_obj": {
                    #     "_metadata": "do",
                    #     "action": "Type",
                    #     "text": "襄阳刘集机场到达"
                    # }
                    # 3. 构造输入动作 (Type) - 使用我们初始化的目的地属性
                    type_action = {
                        "_metadata": "do",
                        "action": "Type",
                        "text": self.destination
                    }

                    print(f"拦截器-终点拦截器生效, ⚡触发宏指令: [点击终点]  + [输入 {self.destination}]")
                    #TODO 额外添加一个 type输入destination的操作,这样点击终点搜索框+输入终点地址2个操作可以一次模型调用完成,加快速度
                    msg = "我已经通过type输入了要求的目的地地址,接下来需要点击匹配的目的地址"
                    return False, [modified_action,type_action], msg,None



        return True, None, None,None