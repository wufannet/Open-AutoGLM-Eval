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
DEFAULT_LOGS_ROOT = "./logs_eval/20260129_1627_滴滴_解决寻找确认下车点_v15_1"
EVAL_STORE = "./logs_eval_reports"
MAX_WORKERS = 10


class StandaloneEvaluator:
    def __init__(self, logs_root=None, run_uuid=None, time_threshold=50.0, step_threshold=8 ):
        self.log_root = (logs_root or DEFAULT_LOGS_ROOT).rstrip('/')
        self.store_path = EVAL_STORE
        if not os.path.exists(self.store_path):
            os.makedirs(self.store_path)

        # --- 新增：阈值设置 ---
        self.time_threshold = time_threshold  # 耗时阈值（秒）
        self.step_threshold = step_threshold  # 步数阈值
        # --------------------

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

        # --- 统计计算 ---
        successes = [r for r in results if r['status'] == 'Success']
        fails_count = total - len(successes)
        success_rate = (len(successes) / total * 100)

        avg_total_time = sum([r.get('duration', 0) for r in results]) / total
        over_time_tasks = [r for r in results if r.get('duration', 0) > self.time_threshold]

        avg_steps = sum([r.get('steps', 0) for r in results]) / total
        over_step_tasks = [r for r in results if r.get('steps', 0) > self.step_threshold]

        rows = ""
        report_dir_abs = os.path.dirname(os.path.abspath(self.html_file))
        for r in results:
            try:
                img_abs_path = os.path.abspath(r['img'])
                relative_img_path = os.path.relpath(img_abs_path, report_dir_abs)
            except:
                relative_img_path = r['img']

            # 判断是否超过阈值
            is_over_time = r['duration'] > self.time_threshold
            is_over_step = r['steps'] > self.step_threshold

            rows += f"""
            <tr>
                <td class="copyable" onclick="copyAndNotify(this, '{r['dir']}')" title="点击复制目录名">
                    <code>{r['dir']}</code>
                    <span class="status-tip">📋</span>
                </td>
                <td>
                    <a href="{relative_img_path}" target="_blank">
                        <img src="{relative_img_path}" width="200" onerror="this.alt='无图';this.style.background='#eee';">
                    </a>
                </td>
                <td style="color:{'green' if r['status'] == 'Success' else 'red'}; font-weight:bold;">{r['status']}</td>
                <td>{r['category']}</td>
                <td>{r['duration']:.1f}s</td>
                <td style="color:{'#d93025' if is_over_time else '#5f6368'};">{'是' if is_over_time else '否'}</td>
                <td>{r['steps']}</td>
                <td style="color:{'#d93025' if is_over_step else '#5f6368'};">{'是' if is_over_step else '否'}</td>
            </tr>"""

        html = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <title>评估报告 - {self.root_dir_name}</title>
            <style>
                body {{ font-family: "Segoe UI", system-ui, sans-serif; padding: 20px; background: #f0f2f5; color: #333; }}
                .container {{ background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); position: relative; }}
                .stat-box {{ display: flex; gap: 10px; margin-bottom: 25px; flex-wrap: wrap; }}
                .stat-item {{ background: #ffffff; border: 1px solid #e1e4e8; padding: 12px; border-radius: 8px; flex: 1; min-width: 120px; text-align: center; }}
                .stat-label {{ font-size: 13px; color: #666; margin-bottom: 5px; }}
                .stat-value {{ font-size: 20px; font-weight: bold; color: #1a73e8; }}

                table {{ border-collapse: collapse; width: 100%; margin-top: 10px; font-size: 13px; table-layout: fixed; }}
                th, td {{ border: 1px solid #eef0f2; padding: 10px; text-align: left; word-break: break-all; }}
                th {{ background-color: #1a73e8; color: white; position: sticky; top: 0; z-index: 10; }}
                tr:nth-child(even) {{ background-color: #fafafa; }}
                tr:hover {{ background-color: #f1f7ff; }}

                .copyable {{ cursor: pointer; transition: all 0.2s ease; position: relative; }}
                .copyable:hover {{ background: #e8f0fe !important; }}
                .status-tip {{ margin-left: 8px; font-size: 12px; transition: all 0.2s; }}

                img {{ border-radius: 4px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); transition: transform 0.2s; cursor: zoom-in; }}
                img:hover {{ transform: scale(1.05); }}

                /* 颜色 */
                .val-success {{ color: #34a853; }}
                .val-fail {{ color: #d93025; }}

                /* 回到顶部按钮 */
                #backToTop {{
                    position: fixed; bottom: 30px; right: 30px; 
                    width: 50px; height: 50px; background: #1a73e8; color: white;
                    border: none; border-radius: 50%; cursor: pointer;
                    box-shadow: 0 4px 10px rgba(0,0,0,0.2); display: none;
                    font-size: 20px; z-index: 1000;
                }}
                #backToTop:hover {{ background: #1557b0; }}
            </style>

            <script>
                function copyAndNotify(el, text) {{
                    navigator.clipboard.writeText(text).then(() => {{
                        const tip = el.querySelector('.status-tip');
                        const code = el.querySelector('code');
                        const oldTip = tip.innerText;
                        tip.innerText = '✅ 已复制';
                        tip.style.color = '#34a853';
                        el.style.backgroundColor = '#e6f4ea';
                        setTimeout(() => {{
                            tip.innerText = oldTip;
                            tip.style.color = '';
                            el.style.backgroundColor = '';
                        }}, 1200);
                    }});
                }}

                // 回到顶部逻辑
                window.onscroll = function() {{
                    const btn = document.getElementById("backToTop");
                    if (document.body.scrollTop > 300 || document.documentElement.scrollTop > 300) {{
                        btn.style.display = "block";
                    }} else {{
                        btn.style.display = "none";
                    }}
                }};

                function scrollToTop() {{
                    window.scrollTo({{ top: 0, behavior: 'smooth' }});
                }}
            </script>
        </head>
        <body>
            <div class="container">
                <h1>📊 自动化评估报告</h1>
                <p style="color: #666;">项目目录: {self.root_dir_name} | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

                <div class="stat-box">
                    <div class="stat-item"><div class="stat-label">总任务</div><div class="stat-value">{total}</div></div>
                    <div class="stat-item"><div class="stat-label">失败任务</div><div class="stat-value val-fail">{fails_count}</div></div>
                    <div class="stat-item"><div class="stat-label">成功率</div><div class="stat-value val-success">{success_rate:.1f}%</div></div>
                    <div class="stat-item"><div class="stat-label">平均耗时</div><div class="stat-value">{avg_total_time:.1f}s</div></div>
                    <div class="stat-item"><div class="stat-label">耗时过长(>{self.time_threshold}s)</div><div class="stat-value val-fail">{len(over_time_tasks)}</div></div>
                    <div class="stat-item"><div class="stat-label">平均步数</div><div class="stat-value">{avg_steps:.1f}</div></div>
                    <div class="stat-item"><div class="stat-label">步数过多(>{self.step_threshold})</div><div class="stat-value val-fail">{len(over_step_tasks)}</div></div>
                </div>

                <table>
                    <colgroup>
                        <col style="width: 25%;">
                        <col style="width: 15%;">
                        <col style="width: 8%;">
                        <col style="width: 12%;">
                        <col style="width: 10%;">
                        <col style="width: 10%;">
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
                            <th>耗时过长</th>
                            <th>总步数</th>
                            <th>步数过多</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
            <button id="backToTop" onclick="scrollToTop()" title="回到顶部">↑</button>
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