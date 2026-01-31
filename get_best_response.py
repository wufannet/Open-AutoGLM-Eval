import copy

from phone_agent.model.client import ModelResponse
# from phone_agent.agent import get_best_response




import json
from dataclasses import dataclass

# --- 模拟环境定义 ---
# @dataclass
# class ModelResponse:
#     thinking: str
#     action: str
#     raw_content: str
#     parse_action_ok: bool = False
#     action_obj: dict = None

@staticmethod
def get_best_response(responses: list[ModelResponse]) -> ModelResponse:
    """
    从多个并行响应中选出最优结果。
    逻辑：
    1. 校验解析状态
    2. 优先返回非 'do' 动作 (如 finish)
    3. 优先返回非 'Tap' 动作 (如 Scroll, Input)
    4. 对多个 Tap 动作进行坐标平滑处理 (去掉最大值取平均)
    """
    if not responses:
        return None

    # --- 1. 遍历校验解析状态 ---
    ok_responses = [r for r in responses if r.parse_action_ok is True]

    if not ok_responses:
        return responses[0]  # 全部失败，返回第一个
    if len(ok_responses) == 1:
        return ok_responses[0]  # 只有一个解析成功
    #  {
    #   "_metadata": "do",
    #   "action": "Tap",
    #   "element": [
    #     499,
    #     165
    #   ]
    # }
    # action_type = action.get("_metadata")
    # element = action.get("element")

    # --- 2. 遍历检查 _metadata (非 do 优先) ---
    # 例如：finish(message="xxx") 通常解析后的 _metadata 为 "finish"
    for r in ok_responses:
        if r.action_obj and r.action_obj.get("_metadata") != "do":
            return r

    # --- 3. 遍历检查 action 类型 (非 Tap 优先) ---
    # 如果有输入、滑动等复杂操作，不进行投票，直接取第一个遇到的
    for r in ok_responses:
        if r.action_obj and r.action_obj.get("action") != "Tap":
            return r

    # --- 4. 坐标平滑处理 (针对全为 Tap 的情况) ---
    # 5. 坐标去噪 (X:[300,320,500]->310, Y:[500,600,520]->510)
    # 提取所有有效的坐标
    coords_x = []  # x的坐标如[300,320,500]
    coords_y = []
    old_elements = []

    for r in ok_responses:
        element = r.action_obj.get("element")
        old_elements.append(element)
        if isinstance(element, list) and len(element) >= 2:
            coords_x.append(float(element[0]))
            coords_y.append(float(element[1]))

    if len(coords_x) >= 2:
        # 逻辑：丢弃最大值，计算剩余的平均值
        def get_denoised_avg(data_list):
            if not data_list: return 0
            if len(data_list) == 1: return data_list[0]

            sorted_data = sorted(data_list)
            # 丢弃最大值（最后一个）
            trimmed_data = sorted_data[:-1]
            return sum(trimmed_data) / len(trimmed_data)

        avg_x = get_denoised_avg(coords_x)
        avg_y = get_denoised_avg(coords_y)

        # 构建最终返回对象
        # 深拷贝第一个 OK 的响应，防止修改原始数据
        best_res = copy.deepcopy(ok_responses[0])  # 到5. 坐标去噪,只有全部是 tap类型才可能.非 do,和非 tap都返回了
        best_res.action_obj["element"] = [int(avg_x), int(avg_y)]

        # 同步更新 action 字符串描述（可选，保持数据一致性）
        new_coords_str = f"({int(avg_x)}, {int(avg_y)})"
        # 假设原始 action 是 do(action=Tap(element=[x, y]))
        # 这里进行简单的字符串替换，或者重新生成
        best_res.action = f"do(action=Tap(element=[{int(avg_x)}, {int(avg_y)}]))"
        best_res.action_obj["old_elements"] = old_elements  # 方便排错,保留原始坐标数据
        return best_res

    return ok_responses[0]

# --- 测试用例生成函数 ---
def run_test_case(name, responses,result_expect):
    print(f"\n--- 测试场景: {name} ---")
    result = get_best_response(responses)
    print(f"选出的 result: {result}")
    if result == result_expect:
        print("成功")
        # print(f"选出的 Action: {result.action}")
        # print(f"Action Object: {result.action_obj}")
    else:
        print("失败")


def run_test_case(name, responses, result_expect):
    print(f"\n--- 测试场景: {name} ---")
    result = get_best_response(responses)
    # 打印关键字段用于调试
    if result:
        print(f"Result action_obj: {result.action_obj}")
        # 由于 dataclass 支持 == 比较，这里对比内容
        if result == result_expect:
            print("✅ 成功")
        else:
            print("❌ 失败 (内容不匹配)")
    else:
        print("❌ 失败 (未返回结果)")

# --- 准备测试数据 ---

# 1. 全部解析失败
case_all_failed_ex = ModelResponse(thinking="think 1", action="err1", raw_content="raw1", parse_action_ok=False)
case_all_failed = [
    case_all_failed_ex,
    ModelResponse(thinking="think 2", action="err2", raw_content="raw2", parse_action_ok=False)
]

# 2. 只有一个解析成功
case_only_one_ok_ex = ModelResponse(
    thinking="think 1", action="do(Tap)", raw_content="raw1",
    parse_action_ok=True, action_obj={"_metadata": "do", "action": "Tap", "element": [100, 100]}
)
case_only_one_ok = [
    case_only_one_ok_ex,
    ModelResponse(thinking="think 2", action="err2", raw_content="raw2", parse_action_ok=False)
]

# 3. 包含非 do 动作 (例如 finish)
case_contains_finish_ex = ModelResponse(
    thinking="think 2", action="finish(msg)", raw_content="raw2",
    parse_action_ok=True, action_obj={"_metadata": "finish", "message": "任务完成"}
)
case_contains_finish = [
    ModelResponse(thinking="think 1", action="do(Tap)", raw_content="raw1", parse_action_ok=True, action_obj={"_metadata": "do", "action": "Tap", "element": [100, 100]}),
    case_contains_finish_ex,
    ModelResponse(thinking="think 3", action="do(Tap)", raw_content="raw3", parse_action_ok=True, action_obj={"_metadata": "do", "action": "Tap", "element": [110, 110]}),
]

# 4. 包含非 Tap 动作 (例如 Scroll)
case_contains_non_tap_ex = ModelResponse(
    thinking="think 2", action="do(Scroll)", raw_content="raw2",
    parse_action_ok=True, action_obj={"_metadata": "do", "action": "Scroll", "direction": "up"}
)
case_contains_non_tap = [
    ModelResponse(thinking="think 1", action="do(Tap)", raw_content="raw1", parse_action_ok=True, action_obj={"_metadata": "do", "action": "Tap", "element": [100, 100]}),
    case_contains_non_tap_ex,
]

# 5. 坐标去噪平均
# 注意：由于 get_best_response 内部用了 deepcopy，返回的是新对象。
# 我们需要构造一个和预期计算结果完全一致的对象进行比较。
case_tap_averaging_ex = ModelResponse(
    thinking="think 1",
    action="do(action=Tap(element=[310, 510]))",
    raw_content="r1",
    parse_action_ok=True,
    action_obj={"_metadata": "do", "action": "Tap", "element": [310, 510], 'old_elements': [[300, 500], [320, 600], [500, 520]]}
)
case_tap_averaging = [
    ModelResponse(thinking="think 1", action="do(Tap1)", raw_content="r1", parse_action_ok=True, action_obj={"_metadata": "do", "action": "Tap", "element": [300, 500]}),
    ModelResponse(thinking="think 2", action="do(Tap2)", raw_content="r2", parse_action_ok=True, action_obj={"_metadata": "do", "action": "Tap", "element": [320, 600]}),
    ModelResponse(thinking="think 3", action="do(Tap3)", raw_content="r3", parse_action_ok=True, action_obj={"_metadata": "do", "action": "Tap", "element": [500, 520]}),
]

# 5. 坐标去噪平均 (3个 Tap)
# X: [500, 100, 110] -> 丢弃 500, 剩 100, 110 -> 均值 105
# Y: [165, 800, 175] -> 丢弃 800, 剩 165, 175 -> 均值 170
# case_tap_averaging_ex= ModelResponse("think 1", "do(Tap1)", "r1", True, {"_metadata": "do", "action": "Tap", "element": [310, 510]})
# case_tap_averaging = [
#     ModelResponse("think 1", "do(Tap1)", "r1", True, {"_metadata": "do", "action": "Tap", "element": [300, 500]}),
#     ModelResponse("think 1", "do(Tap1)", "r1", True, {"_metadata": "do", "action": "Tap", "element": [320, 600]}),
#     ModelResponse("think 1", "do(Tap1)", "r1", True, {"_metadata": "do", "action": "Tap", "element": [500, 520]}),
# ]

# --- 执行测试 ---
if __name__ == "__main__":
    # 确保 get_best_response 已定义（使用上一条回复的代码）
    run_test_case("1. 全部解析失败", case_all_failed, case_all_failed_ex)
    run_test_case("2. 仅一个成功", case_only_one_ok, case_only_one_ok_ex)
    run_test_case("3. 包含 finish (优先级最高)", case_contains_finish, case_contains_finish_ex)
    run_test_case("4. 包含非 Tap (优先级次之)", case_contains_non_tap, case_contains_non_tap_ex)
    run_test_case("5. 坐标去噪 (X:[300,320,500]->310, Y:[500,600,520]->510)", case_tap_averaging, case_tap_averaging_ex)