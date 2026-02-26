import subprocess
import os
import sys
import time
from datetime import datetime
# 需安装 python-dotenv: pip install python-dotenv
from dotenv import load_dotenv
from StandaloneEvaluator import StandaloneEvaluator
from ride.ride_didi_prompt import RideDidiPrompt
# 加载 .env 文件中的变量
load_dotenv()
# 从环境变量中读取，如果读取不到则报错
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    print("❌ 错误: 未在环境变量或 .env 文件中找到 API_KEY")
    sys.exit(1)
# ==================== 配置区 ====================
# destination="勇士篮球总部"
# #测试顺序,先跑5次. 一次5分钟.每次复原.先拿plus最先进模型测试,后面还有开源模型.  自己免费服务器智能部署8B模型.32B模型都部署不了.
# #民发天地东门
# #万达广场1号门
# #襄阳市第一人民医院东院区门诊
# #襄阳市第一人民医院东院区急诊
# #襄阳火车站出站口
# #襄阳东站北进站口
# #襄阳东站北出站口
# #勇士篮球总部
# #吾悦广场1号门
# #吾悦广场3号门
# #襄阳刘集机场国内出发
# #国投襄阳著
# #国投襄阳府
DESTINATIONS= [
    "民发天地东门",
    "万达广场1号门",
    "襄阳市第一人民医院东院区门诊",
    "襄阳市第一人民医院东院区急诊",
    "襄阳火车站出站口",
    "襄阳东站北进站口",
    "襄阳东站北出站口",
    "勇士篮球总部",
    "吾悦广场1号门",
    "吾悦广场3号门",
    "襄阳刘集机场国内出发",
    "国投襄阳著",
    "国投襄阳府",
    "白马广场",
]
RUN_COUNT = 1
# 20260123_104918_滴滴_详细步骤_v4_单应用mvp_autoglm-phone_勇士篮球总部
BASE_LOG_DIR = "./logs_eval/20260124_1131_滴滴_详细步骤_v4"



# ===============================================

class BatchAgentRunner:
    def __init__(self):
        # 严格判断：如果目录已存在，强制停止程序，防止数据覆盖或混淆
        if os.path.exists(BASE_LOG_DIR):
            print(f"🛑 停止运行: 目录 {BASE_LOG_DIR} 已存在。")
            print("💡 请删除该目录或修改脚本中的 'BASE_LOG_DIR' 以开始新的测试。")
            sys.exit(1)

        os.makedirs(BASE_LOG_DIR)
        print(f"✨ 成功创建评估任务根目录: {BASE_LOG_DIR}")

    def run_single_agent(self, destination, index):
        """
        纯执行逻辑：执行任务并保持 log 文件
        """
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 构造符合你要求的 log 目录名
        log_tag = f"{current_time}_滴滴_Task{index:03d}_{destination}"
        log_name = os.path.join(BASE_LOG_DIR, log_tag)
        os.makedirs(log_name, exist_ok=True)

        # 捕获日志的文件路径 (模拟 tee)
        terminal_log = os.path.join(log_name, f"{log_tag}.log")
        # 三段步骤,在什么页面 + 做什么操作/要操作的元素描述和位置描述,位置坐标 +进入什么页面成功和进入什么页面失败
        # 需要结构化语言和强关键字标签语言,比如要求生成地址的元素和生成工具函数的标签.从语言到规则语法.
        # prompt = f"1.打开滴滴\n2. 点击您想去哪儿\n3. 输入{destination}\n4. 点击最匹配的选项\n5. 在最终页面看到终点地址正确,看到报价以及看到底部的呼叫按钮代表任务完成请执行完成"
        prompt = RideDidiPrompt.ride_didi_p18.format(destination=destination)

        cmd = [
            "python", "-u", "main.py",
            "--base-url", "https://open.bigmodel.cn/api/paas/v4",
            "--model", "autoglm-phone",
            "--apikey", API_KEY,
            "--log_name", log_name,
            "--app", "滴滴",
            "--eval", "1",
            "--max-steps", "15",
            prompt
        ]

        print(f"\n[🚀 RUNNING] {index}/{RUN_COUNT}: {destination}")

        # 执行并保存日志 (模拟 tee)
        with open(terminal_log, "w", encoding="utf-8") as f:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                print(f"  {line.strip()}")
                f.write(line)

        process.wait()
        print(f"✅ 任务完成，原始数据保存在: {log_name}")

    def start(self):
        for i in range(1, RUN_COUNT + 1):
            dest = DESTINATIONS[(i - 1) % len(DESTINATIONS)]
            self.run_single_agent(dest, i)

        print("\n🏁 所有 Agent 任务运行完毕！")
        print("💡 现在你可以运行 `python standalone_evaluator.py` 来开始并行评估。")


if __name__ == "__main__":
    tag = "总总程序"
    program_start_time = datetime.now()
    print(f"{tag}开始时间：")
    print(program_start_time.strftime("%Y-%m-%d %H:%M:%S"))
    # 程序占位

    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 构造符合你要求的 log 目录名
    BASE_LOG_DIR = f"./logs_eval/{current_time}_滴滴_压缩截图_v21_p18_c4_p30_360p_5"
    RUN_COUNT = 50
    runner = BatchAgentRunner()
    runner.start()
    # 2. 任务结束后直接调用评估 (传入刚才定义的 BASE_LOG_DIR)
    print("\n[📊 正在启动自动评估...]")
    report_path = StandaloneEvaluator.quick_eval(BASE_LOG_DIR)
    print(f"✨ 所有流程已完成。报告：{report_path}")

    program_end_time = datetime.now()
    duration = program_end_time - program_start_time
    print(f"{tag}开始时间: {program_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{tag}结束时间: {program_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{tag}运行耗时: {str(duration)[:-5]}")  # 时分秒格式
    print(f"{tag}运行耗时秒: {duration.total_seconds():.1f} 秒")