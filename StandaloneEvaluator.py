import os
import json
import uuid
import time
import threading
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# ==================== 配置区 ====================
LOGS_ROOT = "./logs_eval/20260123_1728_滴滴_详细步骤_v4"  # 原始任务运行日志根目录
EVAL_STORE = "./logs_eval_reports"  # 存放评估状态和报告的目录
MAX_WORKERS = 10  # 并行评估线程数


# ===============================================

class StandaloneEvaluator:
    def __init__(self, run_uuid=None):
        self.log_root = LOGS_ROOT.rstrip('/')
        self.store_path = EVAL_STORE
        if not os.path.exists(self.store_path):
            os.makedirs(self.store_path)

        self.root_dir_name = os.path.basename(self.log_root)
        self.start_run_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_uuid = run_uuid if run_uuid else str(uuid.uuid4())[:8]

        base_filename = f"{self.root_dir_name}_{self.start_run_time}"
        self.state_file = os.path.join(self.store_path, f"{base_filename}_eval_state_{self.run_uuid}.json")
        self.html_file = os.path.join(self.store_path, f"{base_filename}_report_{self.run_uuid}.html")

        self.state = self._load_state()
        self.lock = threading.Lock()

    def _load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "uuid": self.run_uuid,
            "start_time": self.start_run_time,
            "root_dir": self.root_dir_name,
            "processed_dirs": [],
            "results": []
        }

    def _save_state(self):
        with self.lock:
            # 【改进 1】：存入 JSON 前，对 results 列表按目录名排序
            self.state["results"].sort(key=lambda x: x['dir'])
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=4)

    def mock_llm_classify(self, img_path):
        time.sleep(0.3)
        import random
        return random.choice(["成功", "UI阻断", "搜索无结果", "定位偏差"])

    def process_task(self, dir_name):
        task_path = os.path.join(self.log_root, dir_name)
        result_json = os.path.join(task_path, "task_result.json")
        if not os.path.exists(result_json): return

        try:
            with open(result_json, 'r', encoding='utf-8') as f:
                data = json.load(f)

            is_success = data.get("result_type") == 1
            category = "成功" if is_success else self.mock_llm_classify(data.get("final_img"))
            step_count = data.get("step_count", 0)

            res = {
                "dir": dir_name,
                "status": "Success" if is_success else "Failed",
                "category": category,
                "duration": float(data.get("program_duration_seconds", 0)),
                "steps": int(step_count),
                "img": data.get("final_img", ""),
                "eval_at": datetime.now().strftime("%H:%M:%S")
            }

            with self.lock:
                self.state["results"].append(res)
                self.state["processed_dirs"].append(dir_name)

            self._save_state()
            self.generate_html()
            print(f" ✅ 已评估: {dir_name}")

        except Exception as e:
            print(f" ❌ 评估出错 {dir_name}: {e}")

    def generate_html(self):
        # 【改进 2】：生成 HTML 前，确保按 dir（Task 序号）排序
        results = sorted(self.state["results"], key=lambda x: x['dir'])
        total = len(results)
        if total == 0: return

        successes = [r for r in results if r['status'] == 'Success']
        success_rate = (len(successes) / total * 100)
        avg_total_time = sum([r.get('duration', 0) for r in results]) / total
        avg_steps = sum([r.get('steps', 0) for r in results]) / total

        rows = ""
        report_dir_abs = os.path.dirname(os.path.abspath(self.html_file))
        for r in results:
            try:
                img_abs_path = os.path.abspath(r['img'])
                relative_img_path = os.path.relpath(img_abs_path, report_dir_abs)
            except:
                relative_img_path = r['img']

            rows += f"""
            <tr>
                <td>{r['dir']}</td>
                <td style="color:{'green' if r['status'] == 'Success' else 'red'}; font-weight:bold;">{r['status']}</td>
                <td>{r['category']}</td>
                <td>{r['duration']:.1f}s</td>
                <td>{r['steps']}</td>
                <td>
                    <a href="{relative_img_path}" target="_blank">
                        <img src="{relative_img_path}" width="200" onerror="this.alt='图片不可用';this.style.background='#eee';">
                    </a>
                </td>
            </tr>"""

        html = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <title>评估报告 - {self.root_dir_name}</title>
            <style>
                body {{ font-family: "Microsoft YaHei", sans-serif; padding: 20px; background: #f5f5f5; }}
                .container {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .stat-box {{ display: flex; gap: 20px; margin-bottom: 20px; }}
                .stat-item {{ background: #e7f3ff; padding: 15px; border-radius: 8px; flex: 1; text-align: center; }}
                .stat-value {{ font-size: 20px; font-weight: bold; margin-top: 5px; color: #007bff; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #007bff; color: white; }}
                tr:hover {{ background-color: #f1f1f1; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 自动化评估报告</h1>
                <p><b>源数据:</b> {self.root_dir_name}</p>
                <p><b>运行时间:</b> {self.start_run_time} | <b>UUID:</b> {self.run_uuid}</p>
                <div class="stat-box">
                    <div class="stat-item"><b>总任务数</b><div class="stat-value">{total}</div></div>
                    <div class="stat-item"><b>成功率</b><div class="stat-value" style="color:green">{success_rate:.1f}%</div></div>
                    <div class="stat-item"><b>平均耗时</b><div class="stat-value">{avg_total_time:.1f}s</div></div>
                    <div class="stat-item"><b>平均步数</b><div class="stat-value">{avg_steps:.1f}</div></div>
                </div>
                <table>
                    <thead>
                        <tr><th>任务目录</th><th>状态</th><th>失败分类</th><th>耗时</th><th>步数</th><th>截图</th></tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
        </body>
        </html>
        """
        with open(self.html_file, 'w', encoding='utf-8') as f:
            f.write(html)

    def run(self):
        if not os.path.exists(self.log_root): return

        # 【改进 3】：显式排序所有目录名，确保线程池按顺序领任务
        all_dirs = sorted([d for d in os.listdir(self.log_root) if os.path.isdir(os.path.join(self.log_root, d))])

        to_process = [d for d in all_dirs if d not in self.state["processed_dirs"]]
        if not to_process:
            print("🙌 处理完毕。")
            return

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(self.process_task, to_process)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--uuid", type=str)
    args = parser.parse_args()
    evaluator = StandaloneEvaluator(run_uuid=args.uuid)
    evaluator.run()