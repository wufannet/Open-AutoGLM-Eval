import unittest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED, FIRST_COMPLETED
from dataclasses import dataclass, field
from typing import Any, List, Optional

from phone_agent import PhoneAgent
from phone_agent.model import ModelConfig
from phone_agent.agent import AgentConfig
import os
import sys
from ride.ride_llm_server import RideLlmServer
from dotenv import load_dotenv
from ride.prompt import Prompt
load_dotenv()

# 从环境变量中读取，如果读取不到则报错
API_KEY = os.getenv("ZP_API_KEY")
if not API_KEY:
    print("❌ 错误: 未在环境变量或 .env 文件中找到 API_KEY")
    sys.exit(1)

# llmServer = RideLlmServer(API_KEY, "https://open.bigmodel.cn/api/paas/v4",   "glm-4.6v-flash")
# llmServer = RideLlmServer(API_KEY, "https://open.bigmodel.cn/api/paas/v4",   "glm-4.1v-thinking-flash")

# --- 1. 模拟基础类 (Mock Classes) ---

model_config = ModelConfig(
    base_url="https://open.bigmodel.cn/api/paas/v4",
    model_name="autoglm-phone",
    api_key=API_KEY,
    lang="cn",
)
agent_config = AgentConfig(
    max_steps=15,
    device_id="mock",
    verbose=True,
    lang="cn",
)
agent = PhoneAgent(
    model_config=model_config,
    agent_config=agent_config,
)

# --- 3. 测试用例类 (UnitTest) ---

class TestAgentReplay(unittest.TestCase):

    def test_case_1(self):
        print("\n=== 开始 错误请求回放-点击去哪坐标错误 ===")
        # total_runs = 5  #最小测试5次
        # total_runs = 10
        total_runs = 50
        # total_runs = 100
        # total_runs = 200
        # total_runs = 500

        success_count = 0

        #在主页点击“您想去哪儿”中的“您您您您您您您您您您您您您您您您您您您您”字 20个您
        #最终统计: 成功 100/100 | 通过率: 100.00% 最终统计: 成功 200/200 | 通过率: 100.00% 最终统计: 成功 100/100 | 通过率: 100.00% 最终统计: 成功 100/100 | 通过率: 100.00% #2 100 100% 3 分钟 45 秒
        # data_path = "/Users/wufan/PycharmProjects/GitHub/Open-AutoGLM/logs_eval/20260206_211451_滴滴_压缩截图_v20_p17_c4_小米10_2/20260206_213340_滴滴_Task029_民发天地东门/step_2_req_0_v5_4_20个您去掉字.json"

        #最终统计:成功 47/50 | 通过率: 94.00% 成功 49/50 | 通过率: 98.00% 成功 45/50 | 通过率: 90.00%
        data_path = "/Users/wufan/PycharmProjects/GitHub/Open-AutoGLM/logs_eval/20260323_174716_滴滴_删除终点条件_v36_p105_c5_p30_360p_10_1/20260323_180147_滴滴_Task014_国投襄阳府/step_4_req_1_修7_修1去掉字.json"

        # 最终统计:
        # data_path = ""

        # 最终统计:
        # data_path = ""

        for i in range(total_runs):
            with self.subTest(iteration=i):
                try:
                    # 注入目标地址并发送请求
                    # 使用这个
                    result = agent.run_step_replay_return1(is_first=False, data_path=data_path)
                    action = result.action_obj
                    element = action.get("element")

                    self.assertTrue(element,"No element coordinates")
                    abs_x, abs_y = element[0], element[1]
                    # [272,509]正确 点击"您要去哪儿"
                    #[499,510] 错误

                    self.assertTrue( abs_x < 400 , "x大于 400")
                    self.assertTrue( abs_y < 550 , "y大于 550")

                    success_count += 1
                    print(f"第 {i + 1} 次: [PASS]")

                except Exception as e:
                    print(f"第 {i + 1} 次: [FAIL] - {str(e)[:100]}")

        # 计算并通过控制台输出
        pass_rate = (success_count / total_runs) * 100
        print(f"\n" + "=" * 30)
        print(f"最终统计: 成功 {success_count}/{total_runs} | 通过率: {pass_rate:.2f}%")
        print("=" * 30)

        # 稳定性红线：通过率低于 90% 则认为代码或 Prompt 需要优化
        self.assertGreaterEqual(pass_rate, 100.0, "通过率未达标")








if __name__ == '__main__':
    unittest.main()