import os
import json
import uuid
import time
import threading
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# ==================== 配置区 ====================
LOGS_ROOT = "./logs_eval/20260123_1610_滴滴_详细步骤_v4"  # 你的任务根目录
EVAL_STORE = "./eval_reports"
MAX_WORKERS = 10


# ===============================================

class StandaloneEvaluator:
    def __init__(self, run_uuid=None):
        self.log_root = LOGS_ROOT
        self.store_path = EVAL_STORE
        if not os.path.exists(self.store_path):
            os.makedirs(self.store_path)

        self.run_uuid = run_uuid if run_uuid else str(uuid.uuid4())[:8]
        self.state_file = os.path.join(self.store_path, f"eval_state_{self.run_uuid}.json")
        self.html_file = os.path.join(self.store_path, f"report_{self.run_uuid}.html")

        self.state = self._load_state()
        self.lock = threading.Lock()

    def _load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "uuid": self.run_uuid,
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "processed_dirs": [],
            "results": []
        }

    def _save_state(self):
        with self.lock:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=4)

    def process_task(self, dir_name):
        task_path = os.path.join(self.log_root, dir_name)
        result_json = os.path.join(task_path, "task_result.json")

        if not os.path.exists(result_json): return

        try:
            with open(result_json, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 提取数据
            is_success = data.get("result_type") == 1
            duration = float(data.get("program_duration_seconds", 0))
            step_count = int(data.get("step_count", 0))  # 提取步数
            img_path = data.get("final_img", "")

            res = {
                "dir": dir_name,
                "status": "Success" if is_success else "Failed",
                "category": "成功" if is_success else "失败(待分类)",
                "duration": duration,
                "steps": step_count,
                "img": img_path,
                "eval_at": datetime.now().strftime("%H:%M:%S")
            }

            with self.lock:
                self.state["results"].append(res)
                self.state["processed_dirs"].append(dir_name)

            self._save_state()
            self.generate_html()
        except Exception as e:
            print(f"❌ 出错 {dir_name}: {e}")

    def generate_html(self):
        results = self.state["results"]
        total = len(results)
        if total == 0: return

        # --- 统计计算 ---
        successes = [r for r in results if r['status'] == "Success"]
        success_rate = (len(successes) / total * 100)

        # 平均耗时 (全任务)
        avg_time = sum([r['duration'] for r in results]) / total

        # 平均步数 (使用 step_count 加和求平均，保留1位小数)
        avg_steps = sum([r['steps'] for r in results]) / total

        # --- 表格行构造 ---
        rows = ""
        report_dir_abs = os.path.dirname(os.path.abspath(self.html_file))

        for r in results:
            # 路径安全转换逻辑
            try:
                img_abs = os.path.abspath(r['img'])
                rel_img_path = os.path.relpath(img_abs, report_dir_abs)
            except:
                rel_img_path = r['img']

            rows += f"""
            <tr>
                <td>{r['dir']}</td>
                <td class="{r['status']}">{r['status']}</td>
                <td>{r['category']}</td>
                <td>{r['duration']:.1f}s</td>
                <td>{r['steps']}</td>
                <td>
                    <a href="{rel_img_path}" target="_blank">
                        <img src="{rel_img_path}" width="120" onerror="this.alt='图片路径错误';">
                    </a>
                </td>
            </tr>"""

        # --- 完整 HTML 模板 ---
        html = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <title>Agent 评估报告 {self.run_uuid}</title>
            <style>
                body {{ font-family: 'Segoe UI', "Microsoft YaHei", sans-serif; background: #f8f9fa; padding: 30px; }}
                .container {{ max-width: 1200px; margin: auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
                .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #eee; padding-bottom: 15px; }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
                .stat-card {{ background: #fff; border: 1px solid #e9ecef; padding: 15px; border-radius: 8px; text-align: center; }}
                .stat-label {{ font-size: 14px; color: #6c757d; }}
                .stat-value {{ font-size: 22px; font-weight: bold; color: #0d6efd; margin-top: 5px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th {{ background: #f1f3f5; padding: 12px; text-align: left; border-bottom: 2px solid #dee2e6; }}
                td {{ padding: 12px; border-bottom: 1px solid #eee; font-size: 14px; }}
                .Success {{ color: #198754; font-weight: bold; }}
                .Failed {{ color: #dc3545; font-weight: bold; }}
                img {{ border: 1px solid #ddd; border-radius: 4px; transition: 0.2s; }}
                img:hover {{ transform: scale(1.1); }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>📊 自动化任务评估报告</h2>
                    <span style="color:#999">ID: {self.run_uuid}</span>
                </div>

                <div class="stats-grid">
                    <div class="stat-card"><div class="stat-label">总任务数</div><div class="stat-value">{total}</div></div>
                    <div class="stat-card"><div class="stat-label">成功率</div><div class="stat-value" style="color:#198754">{success_rate:.1f}%</div></div>
                    <div class="stat-card"><div class="stat-label">平均耗时</div><div class="stat-value">{avg_time:.1f}s</div></div>
                    <div class="stat-card"><div class="stat-label">平均步数</div><div class="stat-value">{avg_steps:.1f} 步</div></div>
                </div>

                <table>
                    <thead>
                        <tr>
                            <th>任务目录</th>
                            <th>状态</th>
                            <th>失败分类</th>
                            <th>执行耗时</th>
                            <th>步数</th>
                            <th>最终截图</th>
                        </tr>
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
        all_dirs = sorted([d for d in os.listdir(self.log_root) if os.path.isdir(os.path.join(self.log_root, d))])
        to_process = [d for d in all_dirs if d not in self.state["processed_dirs"]]

        if not to_process:
            print("✨ 所有任务已评估完毕。")
            return

        print(f"🚀 开始评估 {len(to_process)} 个新任务...")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(self.process_task, to_process)
        print(f"📊 评估报告已更新: {self.html_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--uuid", type=str, help="恢复之前的评估任务")
    args = parser.parse_args()

    evaluator = StandaloneEvaluator(run_uuid=args.uuid)
    evaluator.run()