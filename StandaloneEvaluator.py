import os
import json
import uuid
import time
import threading
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# ==================== 配置区 ====================
LOGS_ROOT = "./logs_eval/20260123_1610_滴滴_详细步骤_v4"  # 原始任务运行日志根目录
EVAL_STORE = "./logs_eval_reports"  # 存放评估状态和报告的目录
MAX_WORKERS = 10  # 并行评估线程数


# ===============================================

class StandaloneEvaluator:
    def __init__(self, run_uuid=None):
        self.log_root = LOGS_ROOT
        self.store_path = EVAL_STORE
        if not os.path.exists(self.store_path):
            os.makedirs(self.store_path)

        # 1. 初始化 UUID 和 状态文件
        self.run_uuid = run_uuid if run_uuid else str(uuid.uuid4())[:8]
        self.state_file = os.path.join(self.store_path, f"eval_state_{self.run_uuid}.json")
        self.html_file = os.path.join(self.store_path, f"report_{self.run_uuid}.html")

        self.state = self._load_state()
        self.lock = threading.Lock()

    def _load_state(self):
        """加载或初始化状态文件"""
        if os.path.exists(self.state_file):
            print(f"🔄 检测到现有评估记录 [{self.run_uuid}]，准备断点续传...")
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            print(f"🆕 开启全新评估任务，UUID: {self.run_uuid}")
            return {
                "uuid": self.run_uuid,
                "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "processed_dirs": [],  # 记录已处理的文件夹名
                "results": []
            }

    def _save_state(self):
        """持久化状态，防止中断"""
        with self.lock:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=4)

    def mock_llm_classify(self, img_path):
        """模拟调用 LLM 的分类逻辑"""
        time.sleep(1)  # 模拟 API 耗时
        import random
        return random.choice(["成功", "UI阻断", "搜索无结果", "定位偏差"])

    def process_task(self, dir_name):
        """处理单个文件夹的评估"""
        task_path = os.path.join(self.log_root, dir_name)
        result_json = os.path.join(task_path, "task_result.json")

        if not os.path.exists(result_json):
            return

        try:
            with open(result_json, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 模拟评估过程
            is_success = data.get("result_type") == 1
            category = "成功" if is_success else self.mock_llm_classify(data.get("final_img"))

            res = {
                "dir": dir_name,
                "status": "Success" if is_success else "Failed",
                "category": category,
                "duration": float(data.get("program_duration_seconds", 0)),
                "img": data.get("final_img", ""),
                "eval_at": datetime.now().strftime("%H:%M:%S")
            }

            with self.lock:
                self.state["results"].append(res)
                self.state["processed_dirs"].append(dir_name)

            # 每处理完一个就存一次盘，确保安全
            self._save_state()
            self.generate_html()
            print(f" ✅ 已评估: {dir_name}")

        except Exception as e:
            print(f" ❌ 评估出错 {dir_name}: {e}")

    def generate_html(self):
        """生成 HTML 报告：修正路径并增加平均耗时统计"""
        results = self.state["results"]
        total = len(results)

        # 统计逻辑
        successes = [r for r in results if r['status'] == "Success"]
        success_rate = (len(successes) / total * 100) if total > 0 else 0

        # 你的要求：所有运行耗时相加除以任务数 (Total Task Count)
        all_durations = sum([r.get('duration', 0) for r in results])
        avg_total_time = all_durations / total if total > 0 else 0

        # 构造表格行
        rows = ""
        for r in results:
            # 关键：路径处理。
            # r['img'] 里的路径通常是 './logs_eval/...'
            # 我们需要去掉开头的 './'，然后前面加 '../'
            # 这样路径就会变成 '../logs_eval/...'
            raw_img_path = r['img']
            if raw_img_path.startswith('./'):
                clean_img_path = raw_img_path[2:]  # 去掉前两个字符 './'
            else:
                clean_img_path = raw_img_path

            relative_img_path = f"../{clean_img_path}"

            rows += f"""
            <tr>
                <td>{r['dir']}</td>
                <td style="color:{'green' if r['status'] == 'Success' else 'red'}; font-weight:bold;">{r['status']}</td>
                <td>{r['category']}</td>
                <td>{r['duration']}s</td>
                <td>
                    <a href="{relative_img_path}" target="_blank">
                        <img src="{relative_img_path}" width="250" onerror="this.alt='图片加载失败';this.style.background='#eee';">
                    </a>
                </td>
            </tr>"""

        html = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <title>评估报告 - {self.run_uuid}</title>
            <style>
                body {{ font-family: "Microsoft YaHei", sans-serif; padding: 20px; background: #f5f5f5; }}
                .container {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .stat-box {{ display: flex; gap: 20px; margin-bottom: 20px; }}
                .stat-item {{ background: #e7f3ff; padding: 15px; border-radius: 8px; flex: 1; text-align: center; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #007bff; color: white; }}
                tr:hover {{ background-color: #f1f1f1; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 自动化评估报告</h1>
                <p><b>UUID:</b> {self.run_uuid}</p>
                <div class="stat-box">
                    <div class="stat-item"><b>总任务数:</b><br>{total}</div>
                    <div class="stat-item"><b>成功率:</b><br><span style="color:green">{success_rate:.1f}%</span></div>
                    <div class="stat-item"><b>全任务平均耗时:</b><br><span style="color:blue">{avg_total_time:.2f}s</span></div>
                </div>
                <table>
                    <thead>
                        <tr><th>任务目录</th><th>执行状态</th><th>失败分类</th><th>运行耗时</th><th>结果截图 (点击放大)</th></tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
            </div>
        </body>
        </html>
        """
        with open(self.html_file, 'w', encoding='utf-8') as f:
            f.write(html)

    def run(self):
        """扫描并开始并行评估"""
        all_dirs = [d for d in os.listdir(self.log_root) if os.path.isdir(os.path.join(self.log_root, d))]

        # 核心过滤逻辑：只处理没记录在状态文件中的目录
        to_process = [d for d in all_dirs if d not in self.state["processed_dirs"]]

        if not to_process:
            print("🙌 所有目录已评估完毕，无需操作。")
            return

        print(f"🚀 准备评估 {len(to_process)} 个新任务...")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(self.process_task, to_process)

        print(f"\n📊 评估任务完成！报告见: {self.html_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--uuid", type=str, help="传入上次的 UUID 以恢复评估")
    args = parser.parse_args()

    evaluator = StandaloneEvaluator(run_uuid=args.uuid)
    evaluator.run()