import unittest
from unittest.mock import MagicMock

from ride.action_intercepter.RideDidiInterceptor import RideDidiInterceptor


# 假设你的拦截器代码保存在 phone_agent/action_intercepter/RideDidiInterceptor.py
# from phone_agent.action_intercepter.RideDidiInterceptor import RideDidiInterceptor

class TestRideDidiInterceptor(unittest.TestCase):

    def setUp(self):
        """
        在每个测试用例执行前都会运行：初始化拦截器实例
        """
        self.destination_text = "襄阳刘集机场"
        self.interceptor = RideDidiInterceptor(start="我的位置", destination=self.destination_text)

        # 伪造一个 ModelResponse 对象
        self.mock_response = MagicMock()

    def test_match_condition(self):
        """
        测试用例 1：完全匹配条件（触发点击纠偏 + 输入宏指令）
        条件：动作是Tap，坐标在[200-520, 500-550] 之间，且 thinking 包含"搜索框"
        """
        action = {
            "_metadata": "do",
            "action": "Tap",
            "element": [499, 524]  # 落在拦截范围内
        }
        # self.mock_response.thinking = "现在我应该点击输入目的地这个搜索框。"
        # self.mock_response.thinking = """让我点击这个搜索框。do(action="Tap", element=[499,524])"""
        # self.mock_response.thinking = """搜索框"""
        self.mock_response.thinking = """好的，滴滴出行已经打开了。我可以看到：\n- 地图上显示了\"民发天地-东门\"的位置\n- 页面显示\"从 民发天地-东门 上车\"\n- 有一个搜索框显示\"输入目的地\"\n- 还有其他选项如\"AI叫车\"、\"预约\"、\"帮忙叫车\"、\"接送机\"等\n\n现在我需要点击\"输入目的地\"这个搜索框。我可以看到搜索框的位置在屏幕中间偏下的位置，显示\"输入目的地\"的文字。"""

        passed, modified_actions, msg, action_result = self.interceptor.before_execute(
            action=action,
            screen_width=1080,
            screen_height=2400,
            step_count=3,
            response=self.mock_response
        )

        # 1. 验证返回值基础状态
        self.assertFalse(passed, "匹配成功时应该返回 False 阻断原流程（交由框架执行修改后的宏指令）")
        self.assertIsNone(msg)
        self.assertIsNone(action_result)

        # 2. 验证动作被成功扩展为 2 个 (Tap + Type)
        self.assertIsNotNone(modified_actions)
        self.assertEqual(len(modified_actions), 2, "应该返回包含两个动作的列表")

        # 3. 验证第一个动作 (Tap) 被正确修改了坐标
        tap_action = modified_actions[0]
        self.assertEqual(tap_action["action"], "Tap")
        self.assertEqual(tap_action["element"], [272, 524], "Tap坐标应该被纠偏为 [272, 524]")

        # 4. 验证第二个动作 (Type) 被成功创建并填入了正确的目的地
        type_action = modified_actions[1]
        self.assertEqual(type_action["action"], "Type")
        self.assertEqual(type_action["text"], self.destination_text, "Type动作应该包含设定的目的地")

    def test_not_match_wrong_coordinates(self):
        """
        测试用例 2：坐标不匹配（正常放行）
        """
        action = {
            "_metadata": "do",
            "action": "Tap",
            "element": [100, 800]  # X 和 Y 都不在范围内
        }
        self.mock_response.thinking = "我想点击搜索框。"

        passed, modified_actions, msg, action_result = self.interceptor.before_execute(
            action=action, screen_width=1080, screen_height=2400, step_count=3, response=self.mock_response
        )

        self.assertTrue(passed, "坐标不匹配应该返回 True 放行")
        self.assertIsNone(modified_actions, "放行时修改动作列表应为 None")

    def test_not_match_wrong_thinking_text(self):
        """
        测试用例 3：大模型思考文本不匹配（正常放行）
        """
        action = {
            "_metadata": "do",
            "action": "Tap",
            "element": [300, 520]  # 坐标在拦截范围内
        }
        self.mock_response.thinking = "这里有个无关紧要的按钮，我点一下试试。"  # 没有关键词

        passed, modified_actions, msg, action_result = self.interceptor.before_execute(
            action=action, screen_width=1080, screen_height=2400, step_count=3, response=self.mock_response
        )

        self.assertTrue(passed, "意图文本不匹配应该返回 True 放行")
        self.assertIsNone(modified_actions)

    def test_not_match_wrong_action_type(self):
        """
        测试用例 4：动作类型不匹配（正常放行）
        """
        action = {
            "_metadata": "do",
            "action": "Swipe",  # 不是 Tap
            "start": [300, 520],
            "end": [300, 100]
        }
        self.mock_response.thinking = "我要向下滑动寻找搜索框。"

        passed, modified_actions, msg, action_result = self.interceptor.before_execute(
            action=action, screen_width=1080, screen_height=2400, step_count=3, response=self.mock_response
        )

        self.assertTrue(passed, "非Tap动作应该直接返回 True 放行")
        self.assertIsNone(modified_actions)




if __name__ == '__main__':
    # 运行所有测试
    unittest.main()