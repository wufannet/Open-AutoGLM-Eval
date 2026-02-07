import unittest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED, FIRST_COMPLETED
from dataclasses import dataclass, field
from typing import Any, List, Optional


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
llmServer = RideLlmServer(API_KEY, "https://open.bigmodel.cn/api/paas/v4",   "glm-4.1v-thinking-flash")

# --- 3. 测试用例类 (UnitTest) ---

class TestRequestN(unittest.TestCase):

    def test_case_1_address(self):
        """
        测试用例 1: 3 个请求都 1 秒钟返回.
        预期: 整个 request_n 1 秒左右返回. 包含 3 个对象.
        """
        print("\n=== 测试用例 1: 全速模式 (1s, 1s, 1s) ===")
        image_dir = "/Users/wufan/PycharmProjects/GitHub/Open-AutoGLM/logs_eval/20260129_1627_滴滴_解决寻找确认下车点_v15_1/20260129_172253_滴滴_Task029_民发天地东门/screenshot_2026-01-29-62688-3041eeb7_15.png"
        # result = llmServer.request({"image_dir": image_dir, "app_name": "滴滴", "LOG_TAG": "didi_eval",
        #                             "prompt": Prompt.didi_eval_v3 + "民发天地东门"})  #
        result = llmServer.request({"image_dir": image_dir, "app_name": "滴滴", "LOG_TAG": "didi_eval",
                                    "prompt": Prompt.didi_address_eval_v2})  # + "民发天地东门"

        self.assertEqual(result.get("destination_check").get("starting_point"), "民发天地-东门", "应该民发天地-东门")
        self.assertEqual(result.get("destination_check").get("destination"), "白马广场", "应该白马广场")



    def test_case_2_address_json(self):
        """
        测试用例 1: 3 个请求都 1 秒钟返回.
        预期: 整个 request_n 1 秒左右返回. 包含 3 个对象.
        """
        print("\n=== 测试用例 1: 全速模式 (1s, 1s, 1s) ===")
        image_dir = "/Users/wufan/PycharmProjects/GitHub/Open-AutoGLM/logs_eval/20260129_1627_滴滴_解决寻找确认下车点_v15_1/20260129_172253_滴滴_Task029_民发天地东门/screenshot_2026-01-29-62688-3041eeb7_15.png"
        result = llmServer.request({"image_dir": image_dir, "app_name": "滴滴", "LOG_TAG": "didi_eval",
                                    "prompt": Prompt.didi_eval_use + "民发天地东门"}) #
        # result = llmServer.request({"image_dir": image_dir, "app_name": "滴滴", "LOG_TAG": "didi_eval",
        #                             "prompt": Prompt.didi_address_eval_v1})  # + "民发天地东门"
        if not result:
            result = {
                'final_decision': {'reason': 'request failed', 'decision': 'FAILED', 'error_type': 'request failed'}}

    #     result_expect =  {
    #   "处于报价预览页检查": {
    #     "reason": "简短描述当前 UI 是否处于报价预览页,处于就是成功",
    #     "decision": "SUCCESS or FAILED"
    #   }
    #   "destination_check": {
    #     "starting_point": "截图提取出的起点"
    #     "destination": "截图提取出的终点"
    #     "reason": "简短描述识别到的终点地址与任务要求的终点地址的语义匹配情况",
    #     "decision": "SUCCESS or FAILED"
    #   },
    #   "final_decision": {
    #     "reason": "简短描述综合判定理由，说明成功的关键点或失败的核心原因",
    #     "decision": "SUCCESS or FAILED",
    #     "error_type": "NONE (若成功) 或第一个FAILED的检查项的Key (如处于报价预览页检查)"
    #   }
    # }

        self.assertEqual(result.get("destination_check").get("starting_point"), "民发天地-东门", "应该民发天地-东门")
        self.assertEqual(result.get("destination_check").get("destination"), "白马广场", "应该白马广场")
        self.assertEqual(result.get("destination_check").get("decision"), "FAILED", "应该FAILED")


    # 单独判断地址用这个
    def test_case_3_didi_address_eval_v2(self):
        """
        测试用例 1: 全速模式多次运行并统计通过率
        """
        print("\n=== 测试开始: LLM 地址提取稳定性评估 ===")

        total_runs = 10  # 设定运行次数
        success_count = 0
        # 例子1 150/150
        # image_dir = "/Users/wufan/PycharmProjects/GitHub/Open-AutoGLM/logs_eval/20260129_1627_滴滴_解决寻找确认下车点_v15_1/20260129_172253_滴滴_Task029_民发天地东门/screenshot_2026-01-29-62688-3041eeb7_15.png"
        # target_dest = "吾悦广场1号门"
        # img_start = "民发天地-东门"
        # img_des = "白马广场"

        # 例子2
        image_dir = "/Users/wufan/PycharmProjects/GitHub/Open-AutoGLM/logs_eval/20260202_2109_滴滴_并行生成多次_v17_p17_c1_p30_2/20260202_213706_滴滴_Task037_吾悦广场1号门/screenshot_2026-02-02-77860-53c1cb95_5.png"
        target_dest = "吾悦广场1号门"
        img_start = "民发天地"
        img_des = "襄阳吾悦广场"
        # 襄阳吾悦广场-1号门
        # 民发天地-东门

        for i in range(total_runs):
            # 使用 subTest 确保某次失败不会停止整个测试
            with self.subTest(iteration=i):
                try:
                    result = llmServer.request({
                        "image_dir": image_dir,
                        "app_name": "滴滴",
                        "LOG_TAG": "didi_eval",
                        "prompt": Prompt.didi_address_eval_v2
                    })

                    # 执行断言
                    self.assertIn(img_start, result.get("destination_check").get("starting_point"), "起点提取错误")
                    self.assertIn(img_des, result.get("destination_check").get("destination"), "终点提取错误")
                    # self.assertEqual(result.get("destination_check").get("decision"), "SUCCESS", "应该SUCCESS")



                    # 如果断言成功，计数加 1
                    success_count += 1
                    print(f"运行结果成功,第 {i + 1} 次运行: [PASS]")

                except self.failureException as e:
                    # 捕获断言失败，打印并交给 subTest 继续
                    print(f"运行结果失败,失败,第 {i + 1} 次运行: [FAIL] - {e}")
                except Exception as e:
                    # 捕获其他异常（如网络、超时等）
                    print(f"运行结果失败,异常,第 {i + 1} 次运行: [ERROR] - {e}")

        # 计算并通过控制台输出通过率
        pass_rate = (success_count / total_runs) * 100
        print(f"\n" + "=" * 30)
        print(f"最终统计结果:")
        print(f"总运行次数: {total_runs}")
        print(f"成功次数: {success_count}")
        print(f"通过率: {pass_rate:.2f}%")
        print("=" * 30)

        # 可选：如果通过率低于阈值，让整个测试方法最终失败
        self.assertGreaterEqual(pass_rate, 100.0, f"通过率 {pass_rate}% 低于预期的 100%")

    def test_case_4_pass_rate_all(self):
        """
        测试用例 1: 全速模式多次运行并统计通过率
        """
        print("\n=== 测试开始: LLM 地址提取稳定性评估 ===")

        total_runs = 10  # 设定运行次数
        success_count = 0
        image_dir = "/Users/wufan/PycharmProjects/GitHub/Open-AutoGLM/logs_eval/20260129_1627_滴滴_解决寻找确认下车点_v15_1/20260129_172253_滴滴_Task029_民发天地东门/screenshot_2026-01-29-62688-3041eeb7_15.png"

        for i in range(total_runs):
            # 使用 subTest 确保某次失败不会停止整个测试
            with self.subTest(iteration=i):
                try:
                    result = llmServer.request({"image_dir": image_dir, "app_name": "滴滴", "LOG_TAG": "didi_eval",
                                                "prompt": Prompt.didi_eval_use + "民发天地东门"})

                    # 执行断言
                    self.assertEqual(result.get("destination_check").get("starting_point"), "民发天地-东门")
                    self.assertEqual(result.get("destination_check").get("destination"), "白马广场")
                    self.assertEqual(result.get("destination_check").get("decision"), "FAILED", "应该FAILED")

                    # 如果断言成功，计数加 1
                    success_count += 1
                    print(f"第 {i + 1} 次运行: [PASS]")

                except self.failureException as e:
                    # 捕获断言失败，打印并交给 subTest 继续
                    print(f"第 {i + 1} 次运行: [FAIL] - {e}")
                except Exception as e:
                    # 捕获其他异常（如网络、超时等）
                    print(f"第 {i + 1} 次运行: [ERROR] - {e}")

        # 计算并通过控制台输出通过率
        pass_rate = (success_count / total_runs) * 100
        print(f"\n" + "=" * 30)
        print(f"最终统计结果:")
        print(f"总运行次数: {total_runs}")
        print(f"成功次数: {success_count}")
        print(f"通过率: {pass_rate:.2f}%")
        print("=" * 30)

        # 可选：如果通过率低于阈值，让整个测试方法最终失败
        self.assertGreaterEqual(pass_rate, 100.0, f"通过率 {pass_rate}% 低于预期的 90%")

    def test_case_didi_v4_stability(self):
        """
        测试用例：使用 v4 混合模式提示词，统计 10 次运行的通过率。
        预期：起点应为“民发天地-东门”，终点应为“白马广场”。
        """
        print("\n=== 开始 v4 稳定性评估 (CoT 模式) ===")

        total_runs = 50
        success_count = 0
        target_dest = "民发天地东门"
        image_dir = "/Users/wufan/PycharmProjects/GitHub/Open-AutoGLM/logs_eval/20260129_1627_滴滴_解决寻找确认下车点_v15_1/20260129_172253_滴滴_Task029_民发天地东门/screenshot_2026-01-29-62688-3041eeb7_15.png"

        for i in range(total_runs):
            with self.subTest(iteration=i):
                try:
                    # 注入目标地址并发送请求
                    # prompt = Prompt.didi_eval_v4.format(target_destination=target_dest)
                    prompt = Prompt.didi_eval_use + "民发天地东门"
                    result = llmServer.request({
                        "image_dir": image_dir,
                        "app_name": "滴滴",
                        "LOG_TAG": "didi_eval_v4",
                        "prompt": prompt
                    })

                    # 获取感知数据和决策结果
                    perception = result.get("perception_data", {})
                    final_decision = result.get("final_decision", {}).get("decision")

                    # 验证点 1：视觉提取的准确性（解决你之前的“当前位置”问题）
                    self.assertIn("民发天地", perception.get("starting_point", ""), "起点提取错误")
                    self.assertIn("白马广场", perception.get("destination", ""), "终点提取错误")
                    self.assertEqual(result.get("destination_check").get("decision"), "FAILED", "应该FAILED")

                    # 验证点 2：审计逻辑的正确性
                    self.assertEqual(final_decision, "FAILED", "应该FAILED")

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
        self.assertGreaterEqual(pass_rate, 90.0, "通过率未达标")

    # 提取为变量
    def test_case_didi_v4_stability_2(self):
        """
        测试用例：使用 v4 混合模式提示词，统计 10 次运行的通过率。
        预期：起点应为“民发天地-东门”，终点应为“白马广场”。
        """
        print("\n=== 开始 v4 稳定性评估 (CoT 模式) ===")

        total_runs = 20
        success_count = 0
        target_dest = "吾悦广场1号门"
        img_start = "民发天地"
        img_des = "吾悦广场"
        image_dir = "/Users/wufan/PycharmProjects/GitHub/Open-AutoGLM/logs_eval/20260202_2109_滴滴_并行生成多次_v17_p17_c1_p30_2/20260202_213706_滴滴_Task037_吾悦广场1号门/screenshot_2026-02-02-77860-53c1cb95_5.png"

        for i in range(total_runs):
            with self.subTest(iteration=i):
                try:
                    # 注入目标地址并发送请求
                    # prompt = Prompt.didi_eval_v4.format(target_destination=target_dest)
                    prompt = Prompt.didi_eval_use + target_dest
                    result = llmServer.request({
                        "image_dir": image_dir,
                        "app_name": "滴滴",
                        "LOG_TAG": "didi_eval_v4",
                        "prompt": prompt
                    })

                    # 获取感知数据和决策结果
                    perception = result.get("perception_data", {})
                    final_decision = result.get("final_decision", {}).get("decision")

                    # 验证点 1：视觉提取的准确性（解决你之前的“当前位置”问题）
                    self.assertIn(img_start, perception.get("starting_point", ""), "起点提取错误")
                    self.assertIn(img_des, perception.get("destination", ""), "终点提取错误")
                    self.assertEqual(result.get("destination_check").get("decision"), "SUCCESS", "应该SUCCESS")

                    # 验证点 2：审计逻辑的正确性
                    self.assertEqual(final_decision, "SUCCESS", "应该SUCCESS")

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

        # 提取为变量
    #用这个
    def test_case_didi_v4_stability_3_wuyue(self):
        """
        测试用例：使用 v4 混合模式提示词，统计 10 次运行的通过率。
        预期：起点应为“民发天地-东门”，终点应为“白马广场”。
        """
        print("\n=== 开始 v4 稳定性评估 (CoT 模式) ===")

        total_runs = 5
        success_count = 0

        # 名称语义匹配错误
        # 最终统计: 成功 20/20 | 通过率: 100.00%
        # target_dest = "勇士篮球总部"
        # img_start = "民发天地"
        # img_des = "勇士少年篮球总部"
        # image_dir = "/Users/wufan/PycharmProjects/GitHub/Open-AutoGLM/logs_eval/20260129_1627_滴滴_解决寻找确认下车点_v15_1/20260129_173234_滴滴_Task036_勇士篮球总部/screenshot_2026-01-29-63204-4597cc2c_6.png"

        # 地址取反:20260129_173334_滴滴_Task037_吾悦广场1号门 #最终统计: 成功 0/10 | 通过率: 0.00%
        target_dest = "吾悦广场1号门"
        img_start = "民发天地"
        img_des = "吾悦广场"
        # image_dir = "/Users/wufan/PycharmProjects/GitHub/Open-AutoGLM/logs_eval/20260129_1627_滴滴_解决寻找确认下车点_v15_1/20260129_173334_滴滴_Task037_吾悦广场1号门/screenshot_2026-01-29-63273-54a746fc_7.png"
        #华为p30没有定位蓝点
        image_dir = "/Users/wufan/PycharmProjects/GitHub/Open-AutoGLM/logs_eval/20260206_100441_滴滴_解决模型评估地址错误_v19_p17_c3_p30_8/20260206_101057_滴滴_Task009_吾悦广场1号门/screenshot_2026-02-06-36693-dd4bd79f_5.png"

        # #模板
        # target_dest = ""
        # img_start = "民发天地"
        # img_des = ""
        # image_dir = ""



        #地址取反:万达广场1号门 最终统计: 成功 10/10 | 通过率: 100.00%
        # img_start = "民发天地"
        # img_des = "万达广场"
        # target_dest = "万达广场1号门"
        # image_dir = "/Users/wufan/PycharmProjects/GitHub/Open-AutoGLM/logs_eval/20260131_1704_滴滴_并行生成多次_v17_p17_c1_p30_1/20260202_210021_滴滴_Task044_万达广场1号门/screenshot_2026-02-02-75655-89c2689e_5.png"

        #地址取反 20260202_210459_滴滴_Task050_勇士篮球总部 最终统计: 成功 9/10 | 通过率: 90.00%, 1个地址取反
        # target_dest = "勇士篮球总部"
        # img_start = "民发天地"
        # img_des = "勇士"
        # image_dir = "/Users/wufan/PycharmProjects/GitHub/Open-AutoGLM/logs_eval/20260131_1704_滴滴_并行生成多次_v17_p17_c1_p30_1/20260202_210459_滴滴_Task050_勇士篮球总部/screenshot_2026-02-02-75941-afd46a6e_6.png"

        for i in range(total_runs):
            with self.subTest(iteration=i):
                try:
                    # 注入目标地址并发送请求
                    # 使用这个
                    prompt = Prompt.didi_eval_v9_2 + target_dest
                    result = llmServer.request({
                        "image_dir": image_dir,
                        "app_name": "滴滴",
                        "LOG_TAG": Prompt.didi_eval_v9_2,
                        "prompt": prompt
                    })

                    # 获取感知数据和决策结果
                    perception = result.get("perception_data", {})
                    final_decision = result.get("final_decision", {}).get("decision")

                    # 验证点 1：视觉提取的准确性（解决你之前的“当前位置”问题）
                    self.assertIn(img_start, perception.get("starting_point", ""), "起点提取错误")
                    self.assertIn(img_des, perception.get("destination", ""), "终点提取错误")
                    self.assertEqual(result.get("destination_check").get("decision"), "SUCCESS", "应该SUCCESS")

                    # 验证点 2：审计逻辑的正确性
                    self.assertEqual(final_decision, "SUCCESS", "应该SUCCESS")

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

    import json

    def test_didi_v10_stability_run(self):
        """
        使用 V10 思维矫正提示词运行 10 次，统计准确率并监控取反情况。
        """
        total_runs = 3
        success_count = 0
        reversal_count = 0  # 专门记录取反错误

        # 根据你提供的截图信息设置预期
        #总运行: 3 次
        # 成功: 3 次
        # 取反错误: 0 次
        # 最终通过率: 100.00%
        target_start = "民发天地"
        target_dest = "勇士"
        image_path = "/Users/wufan/PycharmProjects/GitHub/Open-AutoGLM/logs_eval/20260131_1704_滴滴_并行生成多次_v17_p17_c1_p30_1/20260202_210459_滴滴_Task050_勇士篮球总部/screenshot_2026-02-02-75941-afd46a6e_6.png"

        print(f"\n🚀 开始 V10 稳定性测试 (共 {total_runs} 次)...")

        for i in range(total_runs):
            with self.subTest(iteration=i):
                try:
                    # 1. 发起请求 (确保 Prompt 类中已更新 DIDI_EVAL_V10_ANTI_REVERSAL)
                    prompt = Prompt.DIDI_EVAL_V10_ANTI_REVERSAL
                    print(f"prompt\n{prompt}")

                    result = llmServer.request({
                        "image_dir": image_path,
                        "app_name": "滴滴",
                        "LOG_TAG": "didi_eval_v10",
                        "prompt": prompt
                    })

                    # 2. 提取感知数据
                    perception = result.get("perception_logic", {})
                    actual_start = perception.get("extracted_start_text", "")
                    actual_dest = perception.get("extracted_end_text", "")
                    final_decision = result.get("final_decision", {}).get("decision")

                    # 3. 核心校验：监控【取反】幻觉
                    # 如果目标终点关键字跑到了起点字段，或者目标起点关键字跑到了终点字段
                    if (target_dest in actual_start) and (target_start in actual_dest):
                        reversal_count += 1
                        print(f"  ❌ 第 {i + 1} 次: 检测到感知取反！")
                        self.fail(f"Anti-Reversal Check Failed: Start and End are swapped.")

                    # 4. 正常断言 (使用 assertIn 提高宽容度)
                    self.assertIn(target_start, actual_start, f"起点感知错误: {actual_start}")
                    self.assertIn(target_dest, actual_dest, f"终点感知错误: {actual_dest}")
                    self.assertEqual(final_decision, "SUCCESS", "判定逻辑不匹配")

                    # 5. 计数成功
                    success_count += 1
                    print(f"  ✅ 第 {i + 1} 次: [PASS]")

                except Exception as e:
                    print(f"  ⚠️ 第 {i + 1} 次: [FAIL] -> {str(e)}")

        # --- 最终统计报告 ---
        pass_rate = (success_count / total_runs) * 100
        print(f"\n" + "=" * 40)
        print(f"📊 V10 稳定性测试报告")
        print(f"总运行: {total_runs} 次")
        print(f"成功: {success_count} 次")
        print(f"取反错误: {reversal_count} 次")
        print(f"最终通过率: {pass_rate:.2f}%")
        print("=" * 40)

        # 设定工业级稳定性阈值（如 90%）
        self.assertGreaterEqual(pass_rate, 90.0, f"稳定性未达标，当前通过率: {pass_rate}%")

    def test_didi_v10_stability_run_wuyue(self):
        """
        使用 V10 思维矫正提示词运行 10 次，统计准确率并监控取反情况。
        """
        total_runs = 3
        success_count = 0
        reversal_count = 0  # 专门记录取反错误

        # 根据你提供的截图信息设置预期
        #总运行: 3 次
        # 成功: 3 次
        # 取反错误: 0 次
        # 最终通过率: 100.00%
        target_start = "民发天地"
        target_dest = "吾悦广场1号门"
        img_start = "民发天地"
        img_des = "吾悦广场"

        image_path = "/Users/wufan/PycharmProjects/GitHub/Open-AutoGLM/logs_eval/20260129_1627_滴滴_解决寻找确认下车点_v15_1/20260129_171436_滴滴_Task023_吾悦广场1号门/screenshot_2026-01-29-62125-8308e801_6.png"

        print(f"\n🚀 开始 V10 稳定性测试 (共 {total_runs} 次)...")

        for i in range(total_runs):
            with self.subTest(iteration=i):
                try:
                    # 1. 发起请求 (确保 Prompt 类中已更新 DIDI_EVAL_V10_ANTI_REVERSAL)
                    prompt = Prompt.DIDI_EVAL_V10_ANTI_REVERSAL_format.format(target_destination=target_dest)
                    print(f"prompt\n{prompt}")

                    result = llmServer.request({
                        "image_dir": image_path,
                        "app_name": "滴滴",
                        "LOG_TAG": "didi_eval_v10",
                        "prompt": prompt
                    })

                    # 2. 提取感知数据
                    perception = result.get("perception_logic", {})
                    actual_start = perception.get("extracted_start_text", "")
                    actual_dest = perception.get("extracted_end_text", "")
                    final_decision = result.get("final_decision", {}).get("decision")

                    # 3. 核心校验：监控【取反】幻觉
                    # 如果目标终点关键字跑到了起点字段，或者目标起点关键字跑到了终点字段
                    if (img_des in actual_start) and (img_start in actual_dest):
                        reversal_count += 1
                        print(f"  ❌ 第 {i + 1} 次: 检测到感知取反！")
                        self.fail(f"Anti-Reversal Check Failed: Start and End are swapped.")

                    # 4. 正常断言 (使用 assertIn 提高宽容度)
                    self.assertIn(img_start, actual_start, f"起点感知错误: {actual_start}")
                    self.assertIn(img_des, actual_dest, f"终点感知错误: {actual_dest}")
                    self.assertEqual(final_decision, "SUCCESS", "判定逻辑不匹配")

                    # 5. 计数成功
                    success_count += 1
                    print(f"  ✅ 第 {i + 1} 次: [PASS]")

                except Exception as e:
                    print(f"  ⚠️ 第 {i + 1} 次: [FAIL] -> {str(e)}")

        # --- 最终统计报告 ---
        pass_rate = (success_count / total_runs) * 100
        print(f"\n" + "=" * 40)
        print(f"📊 V10 稳定性测试报告")
        print(f"总运行: {total_runs} 次")
        print(f"成功: {success_count} 次")
        print(f"取反错误: {reversal_count} 次")
        print(f"最终通过率: {pass_rate:.2f}%")
        print("=" * 40)

        # 设定工业级稳定性阈值（如 90%）
        self.assertGreaterEqual(pass_rate, 90.0, f"稳定性未达标，当前通过率: {pass_rate}%")
if __name__ == '__main__':
    unittest.main()