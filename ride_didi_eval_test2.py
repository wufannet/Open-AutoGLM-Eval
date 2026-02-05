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
image_dir = "/Users/wufan/PycharmProjects/GitHub/Open-AutoGLM/logs_eval/20260129_1627_滴滴_解决寻找确认下车点_v15_1/20260129_172253_滴滴_Task029_民发天地东门/screenshot_2026-01-29-62688-3041eeb7_15.png"
result = llmServer.request({"image_dir": image_dir, "app_name": "滴滴","LOG_TAG": "didi_eval", "prompt": Prompt.didi_eval_v3+"民发天地东门"})
if not result:
    result = { 'final_decision': {'reason': 'request failed','decision': 'FAILED', 'error_type': 'request failed'}}


