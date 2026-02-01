import subprocess
import os
import sys
import time
from datetime import datetime
# 需安装 python-dotenv: pip install python-dotenv
from dotenv import load_dotenv
from StandaloneEvaluator import StandaloneEvaluator
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
        prompt = f"""任务指令：
1. 启动与进入： 打开滴滴出行进入主页,请执行具体操作do(action="Launch", app="滴滴出行").
2. 触发搜索： 在主页点击“您想去哪儿”搜索框,请执行具体操作do(action="Tap", element=[272,509]).
  - 异常处理： 若进入“预约打车”或“立即选车”页面，请点击返回键回到主页重试，确保进入的是带键盘的“目的地搜索页面”。
3. 输入目的地： 在键盘已经显示意味着输入框已经处于激活状态的目的地搜索页面输入“{destination}”,请执行具体操作do(action="Type", text="{destination}").
4. 选择目标： 在搜索结果列表中，点击最匹配的选项（通常是第一项）。
5. 判断页面状态（关键步骤）：
  - 情况 A - 地址确认页： 如果页面底部出现“确认下车点”按钮，请点击它以进入下一步,如果没有就代表不需要确认下车点,不需要再找到和点击“确认下车点”,如果没有看到就进行任务完成检查。
  - 情况 B - 报价预览页： 如果页面已经显示了多种车型的实时价格（如：惊喜特价 ¥XX、滴滴快车 ¥XX）和底部的“呼叫x种车型”按钮且终点地址正确，则任务已全部成功完成,不需要再找到和点击“确认下车点”，即视为任务成功。
任务完成检查：
  - 成功标准： 只要屏幕上出现了实时报价列表且终点地址正确，即视为任务成功。
  - 终态动作： 停留在报价页面等待加载完成即可。
  - 严禁操作： 禁止点击底部的“呼叫x种车型”按钮，严禁代替用户下单呼叫。"""

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
    BASE_LOG_DIR = "./logs_eval/20260131_1704_滴滴_并行生成多次_v17_p17_c1_p30_1"
    RUN_COUNT = 20
    runner = BatchAgentRunner()
    runner.start()
    # 2. 任务结束后直接调用评估 (传入刚才定义的 BASE_LOG_DIR)
    print("\n[📊 正在启动自动评估...]")
    report_path = StandaloneEvaluator.quick_eval(BASE_LOG_DIR)
    print(f"✨ 所有流程已完成。报告：{report_path}")