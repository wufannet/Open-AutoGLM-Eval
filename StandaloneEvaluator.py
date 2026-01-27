import os
import json
import uuid
import time
import threading
import argparse
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# ==================== 默认配置 ====================
DEFAULT_LOGS_ROOT = "./logs_eval/20260124_1234_滴滴_详细步骤_v4"
EVAL_STORE = "./logs_eval_reports"
MAX_WORKERS = 10


class StandaloneEvaluator:
    def __init__(self, logs_root=None, run_uuid=None):
        # 允许外部传入 logs_root
        self.log_root = (logs_root or DEFAULT_LOGS_ROOT).rstrip('/')
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

    @staticmethod
    def quick_eval(logs_path):
        """ 提供给其他 py 文件调用的简单接口 """
        print(f"🚀 开始评估目录: {logs_path}")
        evaluator = StandaloneEvaluator(logs_root=logs_path)
        evaluator.run()
        print(f"🏁 评估完成! 报告位于: {evaluator.html_file}")
        return evaluator.html_file

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
            self.state["results"].sort(key=lambda x: x['dir'])
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=4)

    def extract_task_name(self, dir_name):
        """ 从目录名中提取目的地 (例如: ..._Task001_勇士篮球总部 -> 勇士篮球总部) """
        parts = dir_name.split('_')
        return parts[-1] if parts else dir_name

    def mock_llm_classify(self, img_path):
        time.sleep(0.3)
        import random
        return random.choice(["UI阻断", "搜索无结果", "定位偏差"])

    def process_task(self, dir_name):
        task_path = os.path.join(self.log_root, dir_name)
        result_json = os.path.join(task_path, "task_result.json")
        if not os.path.exists(result_json): return

        try:
            with open(result_json, 'r', encoding='utf-8') as f:
                data = json.load(f)

            is_success = data.get("result_type") == 1
            category = "成功" if is_success else self.mock_llm_classify(data.get("final_img"))

            res = {
                "dir": dir_name,
                "task_name": self.extract_task_name(dir_name),
                "status": "Success" if is_success else "Failed",
                "category": category,
                "duration": float(data.get("program_duration_seconds", 0)),
                "steps": int(data.get("step_count", 0)),
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
                <td class="copyable" onclick="copyAndNotify(this, '{r['dir']}')" title="点击复制目录名">
                    <code>{r['dir']}</code>
                    <span class="status-tip">📋</span>
                </td>
                <td>
                    <a href="{relative_img_path}" target="_blank">
                        <img src="{relative_img_path}" width="300" onerror="this.alt='无图';this.style.background='#eee';">
                    </a>
                </td>
                <td style="color:{'green' if r['status'] == 'Success' else 'red'}; font-weight:bold;">{r['status']}</td>
                <td>{r['category']}</td>
                <td>{r['duration']:.1f}s</td>
                <td>{r['steps']}</td>
            </tr>"""

        html = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <title>评估报告 - {self.root_dir_name}</title>
            <style>
                body {{ font-family: "Segoe UI", system-ui, sans-serif; padding: 20px; background: #f0f2f5; color: #333; }}
                .container {{ background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }}
                .stat-box {{ display: flex; gap: 15px; margin-bottom: 25px; }}
                .stat-item {{ background: #ffffff; border: 1px solid #e1e4e8; padding: 15px; border-radius: 8px; flex: 1; text-align: center; }}
                .stat-value {{ font-size: 24px; font-weight: bold; margin-top: 5px; color: #1a73e8; }}

                table {{ border-collapse: collapse; width: 100%; margin-top: 10px; font-size: 13px; table-layout: fixed; }}
                th, td {{ border: 1px solid #eef0f2; padding: 12px; text-align: left; word-break: break-all; }}
                th {{ background-color: #1a73e8; color: white; position: sticky; top: 0; z-index: 10; }}
                tr:nth-child(even) {{ background-color: #fafafa; }}
                tr:hover {{ background-color: #f1f7ff; }}

                /* 复制列交互 */
                .copyable {{ cursor: pointer; transition: all 0.2s ease; position: relative; }}
                .copyable:hover {{ background: #e8f0fe !important; }}
                .copyable code {{ font-family: Consolas, monospace; color: #555; }}
                .status-tip {{ margin-left: 8px; font-size: 12px; transition: all 0.2s; }}

                img {{ border-radius: 4px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); transition: transform 0.2s; cursor: zoom-in; }}
                img:hover {{ transform: scale(1.05); }}

                /* 统计颜色 */
                .val-success {{ color: #34a853; }}
            </style>

            <script>
                function copyAndNotify(el, text) {{
                    navigator.clipboard.writeText(text).then(() => {{
                        const tip = el.querySelector('.status-tip');
                        const code = el.querySelector('code');

                        // 保存原始状态
                        const oldTip = tip.innerText;
                        const oldColor = code.style.color;

                        // 切换反馈状态
                        tip.innerText = '✅ 已复制';
                        tip.style.color = '#34a853';
                        code.style.color = '#34a853';
                        el.style.backgroundColor = '#e6f4ea';

                        // 1.2秒后恢复
                        setTimeout(() => {{
                            tip.innerText = oldTip;
                            tip.style.color = '';
                            code.style.color = oldColor;
                            el.style.backgroundColor = '';
                        }}, 1200);
                    }}).catch(err => {{
                        console.error('复制失败:', err);
                    }});
                }}
            </script>
        </head>
        <body>
            <div class="container">
                <h1>📊 自动化评估报告</h1>
                <p style="color: #666;">项目目录: {self.root_dir_name} | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

                <div class="stat-box">
                    <div class="stat-item">总任务<div class="stat-value">{total}</div></div>
                    <div class="stat-item">成功率<div class="stat-value val-success">{success_rate:.1f}%</div></div>
                    <div class="stat-item">平均耗时<div class="stat-value">{avg_total_time:.1f}s</div></div>
                    <div class="stat-item">平均步数<div class="stat-value">{avg_steps:.1f}</div></div>
                </div>

                <table>
                    <colgroup>
                        <col style="width: 35%;">
                        <col style="width: 20%;">
                        <col style="width: 10%;">
                        <col style="width: 15%;">
                        <col style="width: 10%;">
                        <col style="width: 10%;">
                    </colgroup>
                    <thead>
                        <tr>
                            <th>任务目录 (点击复制)</th>
                            <th>最后截图</th>
                            <th>状态</th>
                            <th>分类结果</th>
                            <th>总耗时</th>
                            <th>总步数</th>
                        </tr>
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
        if not os.path.exists(self.log_root):
            print(f"❌ 目录不存在: {self.log_root}")
            return

        all_dirs = sorted([d for d in os.listdir(self.log_root) if os.path.isdir(os.path.join(self.log_root, d))])
        to_process = [d for d in all_dirs if d not in self.state["processed_dirs"]]

        if not to_process:
            print("🙌 所有目录已评估完毕，无需重复执行。")
            return

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(self.process_task, to_process)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--logs_root", type=str, help="指定需要评估的日志根目录")
    parser.add_argument("--uuid", type=str)
    args = parser.parse_args()

    evaluator = StandaloneEvaluator(logs_root=args.logs_root, run_uuid=args.uuid)
    evaluator.run()