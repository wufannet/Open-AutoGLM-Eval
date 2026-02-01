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

llmServer = RideLlmServer(API_KEY, "https://open.bigmodel.cn/api/paas/v4",   "glm-4.6v-flash")
image_dir = "/Users/wufan/PycharmProjects/GitHub/MobileAgentV3Demo/MobileAgent/Mobile-Agent-v3/mobile_v3/logs/20251229_150502_滴滴花小猪_高层次_v2_多应用mvp_工作流_qwen3-vl-plus-2025-12-19导航_襄阳市第一人民医院东院区急诊/打开滴滴出行微信小程序设置目的地址为襄阳市第一人民医院东院区急诊来查看价格/images/screenshot_2025-12-29-54334-2450efc7_scaled_0.5_5.png"
result = llmServer.request({"image_dir": image_dir, "app_name": "滴滴","LOG_TAG": "didi_eval", "prompt": Prompt.didi_eval})
if not result:
    result = { 'final_decision': {'reason': 'request failed','decision': 'FAILED', 'error_type': 'request failed'}}


