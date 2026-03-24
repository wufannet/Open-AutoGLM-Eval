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

        ################################ 20260206_213340_滴滴_Task029_民发天地东门
        # 地址取反:20260129_173334_滴滴_Task037_吾悦广场1号门 #最终统计: 成功 0/20 | 通过率: 0.00%  #最终统计: 成功 2/10 | 通过率: 20.00%
        # data_path = "/Users/wufan/PycharmProjects/GitHub/Open-AutoGLM/logs_eval/20260206_211451_滴滴_压缩截图_v20_p17_c4_小米10_2/20260206_213340_滴滴_Task029_民发天地东门/step_2_req_0.json"
        # data_path = "/Users/wufan/PycharmProjects/GitHub/Open-AutoGLM/logs_eval/20260206_211451_滴滴_压缩截图_v20_p17_c4_小米10_2/20260206_213340_滴滴_Task029_民发天地东门/step_2_req_0_v1.json"

        #我应该点击"输入目的地"这个搜索框来输入目的地。do(action="Tap", element=[499, 510])
        #最终统计: 13/13 全部 fail 原本的提示词 成功 0/5 | 通过率: 0.00% 区别就是这么大
        # data_path = "/Users/wufan/PycharmProjects/GitHub/Open-AutoGLM/logs_eval/20260323_174716_滴滴_删除终点条件_v36_p105_c5_p30_360p_10_1/20260323_180147_滴滴_Task014_国投襄阳府/step_4_req_1.json"

        #修改:
        # 设置目的地终点地址 - 点击进入目的地搜索页面(显示请输入终点)：在主页点击“输入目的地”中的 //分析原因: 搜索-点击搜索框-搜索框训练最长点的中间坐标element=[499, 510], 最终坐标错误
        # 触发搜索： 在主页点击“输入目的地”中的
        #step_4_req_1_修1_修改为原来的终点设置 成功 5/5 | 通过率: 100.00% 最终统计: 成功 91/100 | 通过率: 91.00% 13,48,50,测50次就够 最终统计: 成功 46/50 | 通过率: 92.00% 最终统计: 成功 48/50 | 通过率: 96.00%  成功 47/50 | 通过率: 94.00%
        #成功 94/100 | 通过率: 94.00% 都是 90以上 成功 91/100 | 通过率: 91.00% 成功 45/50 | 通过率: 90.00% 成功 45/50 | 通过率: 90.00%
        #看来就是 90的水平了
        data_path = "/Users/wufan/PycharmProjects/GitHub/Open-AutoGLM/logs_eval/20260323_174716_滴滴_删除终点条件_v36_p105_c5_p30_360p_10_1/20260323_180147_滴滴_Task014_国投襄阳府/step_4_req_1_修1_修改为原来的终点设置.json"

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