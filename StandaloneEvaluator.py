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
    def __init__(self, logs_root=None, run_uuid=None, time_threshold=50.0, step_threshold=8):
        self.log_root = (logs_root or DEFAULT_LOGS_ROOT).rstrip('/')
        self.store_path = EVAL_STORE
        if not os.path.exists(self.store_path):
            os.makedirs(self.store_path)

        self.time_threshold = time_threshold
        self.step_threshold = step_threshold

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

        # 统计
        successes = [r for r in results if r['status'] == 'Success']
        fails_count = total - len(successes)
        success_rate = (len(successes) / total * 100)
        avg_total_time = sum([r.get('duration', 0) for r in results]) / total
        over_time_tasks = [r for r in results if r.get('duration', 0) > self.time_threshold]
        avg_steps = sum([r.get('steps', 0) for r in results]) / total
        over_step_tasks = [r for r in results if r.get('steps', 0) > self.step_threshold]

        # 提取所有分类供筛选使用
        all_categories = sorted(list(set([r['category'] for r in results])))
        cat_options = "".join([f'<option value="{c}">{c}</option>' for c in all_categories])

        rows = ""
        report_dir_abs = os.path.dirname(os.path.abspath(self.html_file))
        for r in results:
            try:
                img_abs_path = os.path.abspath(r['img'])
                relative_img_path = os.path.relpath(img_abs_path, report_dir_abs)
            except:
                relative_img_path = r['img']

            is_over_time = r['duration'] > self.time_threshold
            is_over_step = r['steps'] > self.step_threshold

            rows += f"""
            <tr data-status="{r['status']}" data-category="{r['category']}" data-overtime="{'是' if is_over_time else '否'}" data-overstep="{'是' if is_over_step else '否'}">
                <td class="copyable" onclick="copyAndNotify(this, '{r['dir']}')">
                    <code>{r['dir']}</code><span class="status-tip">📋</span>
                </td>
                <td>
                    <a href="{relative_img_path}" target="_blank">
                        <img src="{relative_img_path}" width="180" onerror="this.alt='无图';this.style.background='#eee';">
                    </a>
                </td>
                <td class="cell-status" style="color:{'green' if r['status'] == 'Success' else 'red'};">{r['status']}</td>
                <td class="cell-category">{r['category']}</td>
                <td class="cell-duration" data-val="{r['duration']}">{r['duration']:.1f}s</td>
                <td class="cell-overtime">{'是' if is_over_time else '否'}</td>
                <td class="cell-steps" data-val="{r['steps']}">{r['steps']}</td>
                <td class="cell-overstep">{'是' if is_over_step else '否'}</td>
            </tr>"""

        html = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <title>评估报告 - {self.root_dir_name}</title>
            <style>
                body {{ font-family: "Segoe UI", sans-serif; padding: 20px; background: #f0f2f5; }}
                .container {{ background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }}

                /* 统计区域 */
                .stat-box {{ display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }}
                .stat-item {{ background: #f8f9fa; border: 1px solid #e1e4e8; padding: 12px; border-radius: 8px; flex: 1; min-width: 120px; text-align: center; }}
                .stat-label {{ font-size: 12px; color: #666; }}
                .stat-value {{ font-size: 18px; font-weight: bold; color: #1a73e8; }}
                .val-fail {{ color: #d93025; }}

                /* 筛选区域 */
                .filter-bar {{ 
                    background: #f1f3f4; padding: 15px; border-radius: 8px; margin-bottom: 20px;
                    display: flex; gap: 15px; align-items: center; flex-wrap: wrap; font-size: 13px;
                }}
                .filter-group {{ display: flex; align-items: center; gap: 5px; }}
                select {{ padding: 5px; border-radius: 4px; border: 1px solid #ccc; }}

                .btn-reset {{
                    padding: 6px 12px; background: #5f6368; color: white; border: none; 
                    border-radius: 4px; cursor: pointer; transition: background 0.2s;
                }}
                .btn-reset:hover {{ background: #3c4043; }}

                /* 表格样式 */
                table {{ border-collapse: collapse; width: 100%; font-size: 13px; table-layout: fixed; }}
                th, td {{ border: 1px solid #eef0f2; padding: 10px; text-align: left; word-break: break-all; }}
                th {{ background-color: #1a73e8; color: white; position: sticky; top: 0; z-index: 10; user-select: none; }}
                .sortable {{ cursor: pointer; position: relative; }}
                .sortable:hover {{ background-color: #1557b0; }}
                .sort-icon {{ font-size: 10px; margin-left: 4px; opacity: 0.8; }}

                tr:nth-child(even) {{ background-color: #fafafa; }}
                tr:hover {{ background-color: #f1f7ff; }}

                .copyable {{ cursor: pointer; }}
                .status-tip {{ margin-left: 5px; font-size: 12px; opacity: 0.5; }}

                #backToTop {{
                    position: fixed; bottom: 30px; right: 30px; width: 45px; height: 45px;
                    background: #1a73e8; color: white; border: none; border-radius: 50%;
                    cursor: pointer; box-shadow: 0 2px 10px rgba(0,0,0,0.2); display: none; z-index: 100;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 自动化评估报告</h1>
                <p style="color: #666;">项目目录: {self.root_dir_name} | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

                <div class="stat-box">
                    <div class="stat-item"><div class="stat-label">总任务</div><div class="stat-value">{total}</div></div>
                    <div class="stat-item"><div class="stat-label">失败任务</div><div class="stat-value val-fail">{fails_count}</div></div>
                    <div class="stat-item"><div class="stat-label">成功率</div><div class="stat-value">{success_rate:.1f}%</div></div>
                    <div class="stat-item"><div class="stat-label">平均耗时</div><div class="stat-value">{avg_total_time:.1f}s</div></div>
                    <div class="stat-item"><div class="stat-label">耗时过长(>{self.time_threshold}s)</div><div class="stat-value val-fail">{len(over_time_tasks)}</div></div>
                    <div class="stat-item"><div class="stat-label">平均步数</div><div class="stat-value">{avg_steps:.1f}</div></div>
                    <div class="stat-item"><div class="stat-label">步数过多(>{self.step_threshold})</div><div class="stat-value val-fail">{len(over_step_tasks)}</div></div>
                </div>

                <div class="filter-bar">
                    <strong>🔍 筛选:</strong>
                    <div class="filter-group">
                        状态: 
                        <select id="f_status" onchange="applyFilters()">
                            <option value="all">全部</option>
                            <option value="Success">Success</option>
                            <option value="Failed">Failed</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        分类结果: 
                        <select id="f_category" onchange="applyFilters()">
                            <option value="all">全部</option>
                            {cat_options}
                        </select>
                    </div>
                    <div class="filter-group">
                        耗时过长: 
                        <select id="f_overtime" onchange="applyFilters()">
                            <option value="all">全部</option>
                            <option value="是">是</option>
                            <option value="否">否</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        步数过多: 
                        <select id="f_overstep" onchange="applyFilters()">
                            <option value="all">全部</option>
                            <option value="是">是</option>
                            <option value="否">否</option>
                        </select>
                    </div>
                    <button class="btn-reset" onclick="resetAll()">🔄 重置全部</button>
                    <span style="color:#888; margin-left:10px;">(点击表头列名可进行排序)</span>
                </div>

                <table id="resultTable">
                    <thead>
                        <tr>
                            <th class="sortable" onclick="sortTable(0, 'string')" style="width: 25%;">任务目录 <span class="sort-icon">↕</span></th>
                            <th style="width: 15%;">最后截图</th>
                            <th style="width: 8%;">状态</th>
                            <th style="width: 12%;">分类结果</th>
                            <th class="sortable" onclick="sortTable(4, 'float')" style="width: 10%;">总耗时 <span class="sort-icon">↕</span></th>
                            <th style="width: 10%;">耗时过长</th>
                            <th class="sortable" onclick="sortTable(6, 'int')" style="width: 10%;">总步数 <span class="sort-icon">↕</span></th>
                            <th style="width: 10%;">步数过多</th>
                        </tr>
                    </thead>
                    <tbody id="tableBody">{rows}</tbody>
                </table>
            </div>

            <button id="backToTop" onclick="window.scrollTo({{top: 0, behavior: 'smooth'}})">↑</button>

            <script>
                // 记录排序状态
                let sortDirections = {{}};

                // --- 筛选功能 ---
                function applyFilters() {{
                    const status = document.getElementById('f_status').value;
                    const category = document.getElementById('f_category').value;
                    const overtime = document.getElementById('f_overtime').value;
                    const overstep = document.getElementById('f_overstep').value;

                    const rows = document.querySelectorAll('#tableBody tr');
                    rows.forEach(row => {{
                        const matchStatus = (status === 'all' || row.getAttribute('data-status') === status);
                        const matchCategory = (category === 'all' || row.getAttribute('data-category') === category);
                        const matchOvertime = (overtime === 'all' || row.getAttribute('data-overtime') === overtime);
                        const matchOverstep = (overstep === 'all' || row.getAttribute('data-overstep') === overstep);

                        row.style.display = (matchStatus && matchCategory && matchOvertime && matchOverstep) ? '' : 'none';
                    }});
                }}

                // --- 排序功能 ---
                function sortTable(colIdx, type) {{
                    const tbody = document.getElementById('tableBody');
                    const rows = Array.from(tbody.rows);

                    // 切换方向
                    sortDirections[colIdx] = !sortDirections[colIdx];
                    const dir = sortDirections[colIdx] ? 1 : -1;

                    rows.sort((a, b) => {{
                        let valA = a.cells[colIdx].getAttribute('data-val') || a.cells[colIdx].innerText.trim();
                        let valB = b.cells[colIdx].getAttribute('data-val') || b.cells[colIdx].innerText.trim();

                        if (type === 'float' || type === 'int') {{
                            return (parseFloat(valA) - parseFloat(valB)) * dir;
                        }}
                        // 字符串排序
                        return valA.localeCompare(valB, 'zh-CN') * dir;
                    }});

                    rows.forEach(row => tbody.appendChild(row));
                }}

                // --- 重置功能 ---
                function resetAll() {{
                    // 1. 恢复下拉框
                    document.getElementById('f_status').value = 'all';
                    document.getElementById('f_category').value = 'all';
                    document.getElementById('f_overtime').value = 'all';
                    document.getElementById('f_overstep').value = 'all';

                    // 2. 应用筛选（显示所有行）
                    applyFilters();

                    // 3. 恢复初始排序（按任务目录升序）
                    sortDirections = {{}}; // 清空状态
                    sortDirections[0] = false; // 设置为即将变为 true (升序)
                    sortTable(0, 'string');
                }}

                // --- 通用辅助 ---
                function copyAndNotify(el, text) {{
                    navigator.clipboard.writeText(text).then(() => {{
                        const tip = el.querySelector('.status-tip');
                        const old = tip.innerText;
                        tip.innerText = '✅';
                        setTimeout(() => tip.innerText = old, 1000);
                    }});
                }}

                window.onscroll = function() {{
                    const btn = document.getElementById("backToTop");
                    btn.style.display = (document.body.scrollTop > 300 || document.documentElement.scrollTop > 300) ? "block" : "none";
                }};
            </script>
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
            print("🙌 所有目录已评估完毕。")
            return

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(self.process_task, to_process)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--logs_root", type=str)
    parser.add_argument("--uuid", type=str)
    args = parser.parse_args()

    evaluator = StandaloneEvaluator(logs_root=args.logs_root, run_uuid=args.uuid)
    evaluator.run()