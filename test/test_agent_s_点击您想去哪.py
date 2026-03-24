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
        print("\n=== 开始 快捷方式-点击去哪 ===")
        total_runs = 1
        success_count = 0

        #
        data_path = "/Users/wufan/PycharmProjects/GitHub/Open-AutoGLM/logs_eval/20260206_211451_滴滴_压缩截图_v20_p17_c4_小米10_2/20260206_213340_滴滴_Task029_民发天地东门/step_2_req_0_s_v3_使用mae.json"


        for i in range(total_runs):
            with self.subTest(iteration=i):
                try:
                    # 注入目标地址并发送请求
                    # 使用这个
                    result = agent.run_step_replay_return1(is_first=False, data_path=data_path)
                    action = result.action_obj
                    # {
                    #     "_metadata": "do",
                    #     "action": "Launch",
                    #     "app": "滴滴出行"
                    # }
                    action_name = action.get("action")

                    self.assertTrue(action_name == "在主页点击您想去哪儿","方法不是在主页点击您想去哪儿")



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