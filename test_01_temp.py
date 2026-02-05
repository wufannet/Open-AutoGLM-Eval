import unittest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED, FIRST_COMPLETED
from dataclasses import dataclass, field
from typing import Any, List, Optional


# --- 1. 模拟基础类 (Mock Classes) ---

@dataclass
class ModelResponse:
    """模拟的模型响应对象"""
    content: str
    action: str = ""
    action_obj: Any = None
    parse_action_ok: bool = True


class MockModelClient:
    """模拟 ModelClient，可以控制每个请求的延迟时间"""

    def __init__(self, delays: List[float]):
        self.delays = delays  # 这里的 delays 列表对应 request 的 index

    def request(self, context, is_print=False) -> ModelResponse:
        # 获取当前线程名或者通过某种方式传递 index，
        # 这里为了简化测试，利用 delays 列表和外部传参机制
        # 在实际 request_n 中，我们需要一种方式让 request 知道自己的 index
        # 为了测试方便，我们在 Agent 调用 request 时稍作修改，传入 index
        # 或者利用 ThreadLocal，但在本示例中，我将在 Agent.safe_request 中处理休眠逻辑
        # *注意*：为了让 mock 简单，真正的 sleep 放在 safe_request 的 mock 调用里
        return ModelResponse(content="mock_response")


# --- 2. 待测试的核心类 (Agent) ---

class Agent:
    def __init__(self, delays: List[float]):
        self.model_client = MockModelClient(delays)
        self.agent_config = type('Config', (), {'verbose': True})()
        self._context = {}
        self.delays = delays  # 用于测试控制延迟

    def log_model_message(self, *args):
        pass

    def request_n(self, messages: list[dict[str, Any]], n: int = 3) -> list[ModelResponse]:
        """
        并行请求 n 次。
        策略：软超时 15 秒。如果 15 秒后收集到 >= 2 个结果，则提前返回。
        """
        SOFT_TIMEOUT = 10
        MIN_REQUIRED = 2

        # 内部函数：模拟 safe_request
        def safe_request(index: int):
            # is_print = index == 0
            is_print = True
            if is_print:
                print(f"   [Mock] 请求 {index} 开始，预计耗时 {self.delays[index]}s...")

            # --- 模拟耗时 ---
            time.sleep(self.delays[index])
            # ----------------

            # 模拟调用
            response = self.model_client.request(self._context, is_print=is_print)
            response.content = f"Response from index {index}"

            # 模拟解析逻辑
            self.log_model_message(response, index)
            response.parse_action_ok = True

            if is_print:
                print(f"   [Mock] 请求 {index} 完成。time.sleep {self.delays[index]}")
            return response

        results = []

        print(f"\n[System] 开始并行请求 n={n} (超时={SOFT_TIMEOUT}s, 最少需要={MIN_REQUIRED})")
        start_time = time.time()

        # 【核心修改 1】手动创建 Executor，不使用 with 上下文管理器
        executor = ThreadPoolExecutor(max_workers=n)

        try:
            # 1. 提交任务
            futures = [executor.submit(safe_request, i) for i in range(n)]

            # 2. 第一次等待：尝试等待所有完成，但在 SOFT_TIMEOUT 截断,  全部完成或者等待到达 15秒返回.
            done, not_done = wait(futures, timeout=SOFT_TIMEOUT, return_when=ALL_COMPLETED)

            # 3. 决策逻辑
            if len(done) >= MIN_REQUIRED:
                if_time = time.time() - start_time
                print(f"[System] 软超时时间到或已全部完成。当前完成数: {len(done)} (>= {MIN_REQUIRED}) -> 决定：立即返回,耗时{if_time:.2f}s")
            else:
                print(f"[System] 软超时时间到。当前完成数: {len(done)} (< {MIN_REQUIRED}) -> 决定：继续等待直到满足数量")
                # 补救措施：必须等到满足最小数量
                while len(done) < MIN_REQUIRED and not_done:
                    # 使用 FIRST_COMPLETED 只要有一个新的完成就检查一次
                    new_done, not_done = wait(not_done, return_when=FIRST_COMPLETED)
                    done.update(new_done)

            # 4. 收集结果
            for f in done:
                try:
                    results.append(f.result())
                except Exception as e:
                    print(f"Task error: {e}")

            # 5. 取消剩余任务 (Best practice)
            for f in not_done:
                f.cancel()
        finally:
            # 【核心修改 3】关键！wait=False
            # 告诉 Python: "不要等后台那些慢线程了，直接向下执行，让它们自生自灭"
            # 这样如果 1s 完成了两个，主程序会在 1s 处直接 return，
            # 那个 20s 的线程会在后台默默跑完，不会拖慢主程序。
            executor.shutdown(wait=False)

        total_time = time.time() - start_time
        print(f"[System] 最终耗时: {total_time:.2f}s, 获取结果数: {len(results)}")
        return results, total_time


# --- 3. 测试用例类 (UnitTest) ---

class TestRequestN(unittest.TestCase):

    def test_case_1_all_fast(self):
        """
        测试用例 1: 3 个请求都 1 秒钟返回.
        预期: 整个 request_n 1 秒左右返回. 包含 3 个对象.
        """
        print("\n=== 测试用例 1: 全速模式 (1s, 1s, 1s) ===")
        delays = [1, 1, 1]
        agent = Agent(delays)

        responses, duration = agent.request_n([], n=3)

        self.assertEqual(len(responses), 3, "应该返回 3 个结果")
        # 允许 0.5s 的系统开销误差
        self.assertAlmostEqual(duration, 1.0, delta=0.5, msg="应该在 1 秒左右完成")








if __name__ == '__main__':
    unittest.main()