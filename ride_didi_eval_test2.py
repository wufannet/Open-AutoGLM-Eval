import os
import sys

from ride.ride_llm_server import RideLlmServer

# 需安装 python-dotenv: pip install python-dotenv
from dotenv import load_dotenv
load_dotenv()


# 从环境变量中读取，如果读取不到则报错
API_KEY = os.getenv("ZP_API_KEY")
# print(f"读取到的API_KEY: {API_KEY}")
if not API_KEY:
    print("❌ 错误: 未在环境变量或 .env 文件中找到 API_KEY")
    sys.exit(1)
llmServer = RideLlmServer(API_KEY, "https://open.bigmodel.cn/api/paas/v4",   "glm-4.6v-flash")

image_dir = "/Users/wufan/PycharmProjects/GitHub/MobileAgentV3Demo/MobileAgent/Mobile-Agent-v3/mobile_v3/logs/20251229_150502_滴滴花小猪_高层次_v2_多应用mvp_工作流_qwen3-vl-plus-2025-12-19导航_襄阳市第一人民医院东院区急诊/打开滴滴出行微信小程序设置目的地址为襄阳市第一人民医院东院区急诊来查看价格/images/screenshot_2025-12-29-54334-2450efc7_scaled_0.5_5.png"

prompt = """Role: 你是一名高级移动端 QA 自动化审计专家，专门负责对 GUI Agent 执行的“滴滴打车”任务结果进行最终判定。
Task: 根据用户提供的【任务指令】和 Agent 执行结束后的【最终截图】，分析任务是否按要求完成。
Evaluation Logic (Thinking Process): 在生成 JSON 之前，请按以下步骤在 Thinking Process 阶段进行深入分析：
状态判定：判断当前是否处于报价预览页（是否有多个打车选项的价格列表），并确认 Agent 是否停留在该页（未误触呼叫按钮）。
目的地比对：截图上部分地图中的橙色小圆环旁边地址为终点地址,将识别到的终点地址与指令要求的终点地址进行文本匹配分析,）。
归因分析：如果任务失败，定位到是哪一个检查项最先出错，并归纳错误原因。
Output Requirement: 请严格遵守以下输出格式：输出一个标准的 JSON 代码块。
JSON 模板示例：
JSON
{
  "is_on_call_page": {
    "decision": "SUCCESS or FAILED"
  }
  ,
    "price_list_check": {
    "decision": "SUCCESS or FAILED"
  },
  "destination_check": {
    "decision": "SUCCESS or FAILED"
  },
  "final_decision": {
    "reason": "一句话简短描述综合判定理由，说明成功的关键点或失败的核心原因",
    "decision": "SUCCESS or FAILED",
    "error_type": "None (若成功) 或第一个失败检查项的 Key (如 is_on_call_page)"
  }
}
要求:
1. 输出必须是标准 JSON 格式。
2.终点地址是民发天地东门
"""
# 这已经是最简单了,好像也不用封装层一个http请求方法了.应该参考js或者python的同步http请求写法.或者有需要异步http请求吗?
result = llmServer.request({"image_dir": image_dir,
                            "app_name": "滴滴",
                            "LOG_TAG": "didi_eval",
                            "prompt": prompt})

# ###=== 点击你想去哪 滴滴 qwen3-vl-plus === ###
# 点击你想去哪 请求开始时间: 2025-11-30 18:37:02
# 点击你想去哪 请求结束时间: 2025-11-30 18:37:04
# 点击你想去哪 请求耗时秒: 1.6 秒
# 点击你想去哪 prompt_tokens: 539
# 点击你想去哪 completion_tokens: 23
# 点击你想去哪 total_tokens: 562
# result: {'has': True, 'coordinate': [249, 507]}

