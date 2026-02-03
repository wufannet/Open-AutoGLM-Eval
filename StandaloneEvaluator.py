import os
import json
import uuid
import time
import threading
import argparse
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
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

# ==================== 默认配置 ====================
DEFAULT_LOGS_ROOT = "./logs_eval/20260131_1704_滴滴_并行生成多次_v17_p17_c1_p30_1"
EVAL_STORE = "./logs_eval_reports"
MAX_WORKERS = 1


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
        self.llmServer = RideLlmServer(API_KEY, "https://open.bigmodel.cn/api/paas/v4", "glm-4.6v-flash")

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

    def llm_eval(self, img_path,data):
        task = data.get("task")
        # 使用正则表达式提取引号内的内容
        # 这里的逻辑是：匹配 “输入“ 之后，到下一个 ” 结束之前的所有字符
        match = re.search(r'输入“([^”]+)”', task)

        if match:
            destination = match.group(1)
            print(f"提取的目的地为: {destination}")
            result = self.llmServer.request(
                {"image_dir": img_path, "app_name": "滴滴", "LOG_TAG": "didi_eval", "prompt": Prompt.didi_eval_v3+destination})
            if not result:
                result = {
                    'final_decision': {'reason': 'request failed', 'decision': 'FAILED',
                                       'error_type': 'request failed'}}
        else:
            print("未找到目的地信息")
            result = {
                'final_decision': {'reason': '未找到目的地信息', 'decision': 'FAILED',
                                   'error_type': '未找到目的地信息'}}

        return result

    def llm_eval_mock(self, img_path, data):
        result = {
            'final_decision': {'reason': 'llm_eval_mock', 'decision': 'SUCCESS',
                               'error_type': 'llm_eval_mock'}}


        return result

    def process_task(self, dir_name):
        task_path = os.path.join(self.log_root, dir_name)
        result_json = os.path.join(task_path, "task_result.json")
        if not os.path.exists(result_json): return

        try:
            with open(result_json, 'r', encoding='utf-8') as f:
                data = json.load(f)

            is_success = data.get("result_type") == 1
            # category = "成功" if is_success else self.mock_llm_classify(data.get("final_img"))
            # llm_eval_result = self.llm_eval(data.get("final_img"),data)
            llm_eval_result = self.llm_eval(data.get("final_img"),data)
            # {'is_on_call_page': {'decision': 'SUCCESS'}, 'price_list_check': {'decision': 'SUCCESS'}, 'destination_check': {'decision': 'FAILED'},
            # 'final_decision': {'reason': '', 'decision': 'FAILED', 'error_type': 'destination_check'}}
            res = {
                "dir": dir_name,
                "task_name": self.extract_task_name(dir_name),
                "status": "Success" if is_success else "Failed",
                "category": llm_eval_result.get("final_decision").get("error_type"),
                "duration": float(data.get("program_duration_seconds", 0)),
                "steps": int(data.get("step_count", 0)),
                "img": data.get("final_img", ""),
                "eval_at": datetime.now().strftime("%H:%M:%S"),
                "llm_eval_result": llm_eval_result,
                "llm_eval_result_decision": llm_eval_result.get("final_decision").get("decision"),
                # "llm_eval_result_error_type": llm_eval_result,
            }

            with self.lock:
                self.state["results"].append(res)
                self.state["processed_dirs"].append(dir_name)

            self._save_state()
            self.generate_html()
            print(f" ✅ 已评估: {dir_name}")

        except Exception as e:
            print(f" ❌ 评估出错 {dir_name}: {e}")

    def syntax_highlight_json(self, json_str):
        """为 JSON 字符串添加 HTML 颜色标签"""
        import re
        # 转义 HTML 基本字符防止冲突
        json_str = json_str.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        # 正则替换：
        # 1. 键 (Key) -> 紫色
        json_str = re.sub(r'("(.*?)")\s*:', r'<span style="color: #92278f; font-weight:bold;">\1</span>:', json_str)
        # 2. 字符串值 (String Value) -> 绿色
        json_str = re.sub(r':\s*("(.*?)")', r': <span style="color: #2a9d8f;">\1</span>', json_str)
        # 3. 数字/布尔值 (Numbers/Booleans) -> 蓝色
        json_str = re.sub(r'\b(true|false|null|\d+(\.\d+)?)\b', r'<span style="color: #25aae2;">\1</span>', json_str)

        return json_str

    def generate_html(self):
        results = sorted(self.state["results"], key=lambda x: x['dir'])
        total = len(results)
        if total == 0: return

        # --- 统计逻辑 ---
        successes = [r for r in results if r['status'] == 'Success']
        successes_count=len(successes)
        fails_count = total - successes_count
        success_rate = (len(successes) / total * 100)
        avg_total_time = sum([r.get('duration', 0) for r in results]) / total
        over_time_tasks = [r for r in results if r.get('duration', 0) > self.time_threshold]
        avg_steps = sum([r.get('steps', 0) for r in results]) / total
        over_step_tasks = [r for r in results if r.get('steps', 0) > self.step_threshold]

        # 统计分类数据用于饼图
        cat_counts = {}
        for r in results:
            cat = r['category']
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        # 提取所有分类供筛选使用
        all_categories = sorted(list(cat_counts.keys()))
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


            # 假设 r['llm_eval_result'] 是一个字典或 JSON 字符串
            raw_data = r['llm_eval_result']
            if isinstance(raw_data, str):
                # 如果是字符串，先转成对象再格式化，确保缩进有效
                import ast
                try:
                    raw_data = json.loads(raw_data.replace("'", '"'))  # 尝试处理单引号问题
                except:
                    raw_data = ast.literal_eval(raw_data)

            # 转换为带缩进的漂亮格式
            formatted_json = json.dumps(raw_data, indent=4, ensure_ascii=False)
            # 获取高亮版本
            highlighted_json = self.syntax_highlight_json(formatted_json)

            rows += f"""
            <tr data-status="{r['status']}" data-category="{r['category']}" data-overtime="{'是' if is_over_time else '否'}" data-overstep="{'是' if is_over_step else '否'}">
                <td class="copyable" onclick="copyAndNotify(this, `{r['dir']}`)">
                    <code>{r['dir']}</code><span class="status-tip">📋</span>
                </td>
                <td>
                    <a href="{relative_img_path}" target="_blank">
                        <img src="{relative_img_path}" width="240" onerror="this.alt='无图';this.style.background='#eee';">
                    </a>
                </td>
                <td class="cell-status" style="color:{'green' if r['status'] == 'Success' else 'red'}; font-weight:bold;">{r['status']}</td>
                <td class="cell-category">{r['category']}</td>
                <td class="copyable" 
                    onclick="copyAndNotify(this, this.querySelector('code').innerText)" 
                    style="vertical-align: top; max-width: 400px;">
                    <pre style="margin: 0; font-family: 'Consolas', monospace; font-size: 12px; background: #fdfdfd; padding: 10px; border: 1px solid #eee; border-radius: 4px; overflow-x: auto;"><code>{highlighted_json}</code></pre>
                    <span class="status-tip">📋</span>
                </td>
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
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{ font-family: "Segoe UI", sans-serif; padding: 20px; background: #f0f2f5; margin: 0; }}
                .container {{ background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); max-width: 1600px; margin: auto; }}

                /* 顶部统计和饼图布局 */
                .top-section {{ display: flex; gap: 20px; margin-bottom: 25px; align-items: flex-start; }}
                .stat-grid {{ flex: 3; display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 10px; }}
                .stat-item {{ background: #f8f9fa; border: 1px solid #e1e4e8; padding: 10px; border-radius: 8px; text-align: center; }}
                .stat-label {{ font-size: 12px; color: #666; margin-bottom: 5px; }}
                .stat-value {{ font-size: 20px; font-weight: bold; color: #1a73e8; }}
                .val-fail {{ color: #d93025; }}

                .chart-container {{ flex: 1; background: #f8f9fa; border: 1px solid #e1e4e8; padding: 15px; border-radius: 8px; max-height: 280px; display: flex; flex-direction: column; align-items: center; }}

                /* 筛选区域 */
                .filter-bar {{ 
                    background: #f1f3f4; padding: 15px; border-radius: 8px; margin-bottom: 20px;
                    display: flex; gap: 15px; align-items: center; flex-wrap: wrap; font-size: 13px;
                }}
                .filter-group {{ display: flex; align-items: center; gap: 5px; }}
                select {{ padding: 6px; border-radius: 4px; border: 1px solid #ccc; background: white; }}

                .btn-reset {{ padding: 6px 12px; background: #5f6368; color: white; border: none; border-radius: 4px; cursor: pointer; }}
                .btn-reset:hover {{ background: #3c4043; }}

                /* 表格及固定表头 */
                .table-wrapper {{ overflow: visible; }}
                table {{ border-collapse: separate; border-spacing: 0; width: 100%; font-size: 13px; table-layout: fixed; }}

                /* 关键修复：固定表头所有列 */
                th {{ 
                    position: sticky; 
                    top: 0; 
                    background-color: #1a73e8; 
                    color: white; 
                    z-index: 100; 
                    padding: 12px 10px;
                    text-align: left;
                    border-bottom: 2px solid #1557b0;
                    user-select: none;
                }}

                td {{ border-bottom: 1px solid #eef0f2; padding: 12px 10px; word-break: break-all; vertical-align: top; background: white; }}

                .sortable {{ cursor: pointer; }}
                .sortable:hover {{ background-color: #1557b0; }}

                tr:nth-child(even) td {{ background-color: #fafafa; }}
                tr:hover td {{ background-color: #f1f7ff; }}

                img {{ border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); transition: transform 0.2s; }}
                img:hover {{ transform: scale(1.02); }}

                .copyable {{ cursor: pointer; color: #1a73e8; }}
                .status-tip {{ margin-left: 5px; font-size: 12px; opacity: 0.6; }}

                #backToTop {{
                    position: fixed; bottom: 30px; right: 30px; width: 50px; height: 50px;
                    background: #1a73e8; color: white; border: none; border-radius: 50%;
                    cursor: pointer; box-shadow: 0 4px 12px rgba(0,0,0,0.3); display: none; z-index: 1000;
                    font-size: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 自动化评估报告</h1>
                <p class="copyable" 
                   style="color: #666; margin-top: -10px; cursor: pointer;" 
                   onclick="copyAndNotify(this, '项目: {self.root_dir_name} | 生成于: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}')">
                   项目: {self.root_dir_name} | 生成于: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                   <span class="status-tip">📋</span>
                </p>

                <div class="top-section">
                    <div class="stat-grid">
                        <div class="stat-item"><div class="stat-label">总任务</div><div class="stat-value">{total}</div></div>
                        <div class="stat-item"><div class="stat-label">成功任务</div><div class="stat-value">{successes_count}</div></div>
                        <div class="stat-item"><div class="stat-label">失败任务</div><div class="stat-value val-fail">{fails_count}</div></div>
                        <div class="stat-item"><div class="stat-label">成功率</div><div class="stat-value">{success_rate:.1f}%</div></div>
                        <div class="stat-item"><div class="stat-label">平均耗时</div><div class="stat-value">{avg_total_time:.1f}s</div></div>
                        <div class="stat-item"><div class="stat-label">耗时过长</div><div class="stat-value val-fail">{len(over_time_tasks)}</div></div>
                        <div class="stat-item"><div class="stat-label">平均步数</div><div class="stat-value">{avg_steps:.1f}</div></div>
                        <div class="stat-item"><div class="stat-label">步数过多</div><div class="stat-value val-fail">{len(over_step_tasks)}</div></div>
                    </div>

                    <div class="chart-container">
                        <div style="font-size: 14px; font-weight: bold; margin-bottom: 10px;">分类结果分布</div>
                        <canvas id="categoryChart"></canvas>
                    </div>
                </div>

                <div class="filter-bar">
                    <strong>🔍 筛选:</strong>
                    <div class="filter-group">状态: <select id="f_status" onchange="applyFilters()"><option value="all">全部</option><option value="Success">Success</option><option value="Failed">Failed</option></select></div>
                    <div class="filter-group">分类: <select id="f_category" onchange="applyFilters()"><option value="all">全部</option>{cat_options}</select></div>
                    <div class="filter-group">耗时过长: <select id="f_overtime" onchange="applyFilters()"><option value="all">全部</option><option value="是">是</option><option value="否">否</option></select></div>
                    <div class="filter-group">步数过多: <select id="f_overstep" onchange="applyFilters()"><option value="all">全部</option><option value="是">是</option><option value="否">否</option></select></div>
                    <button class="btn-reset" onclick="resetAll()">🔄 重置全部</button>
                </div>

                <div class="table-wrapper">
                    <table id="resultTable">
                        <thead>
                            <tr>
                                <th class="sortable" onclick="sortTable(0, 'string')" style="width: 20%;">任务目录 ↕</th>
                                <th style="width: 250px;">最后截图</th>
                                <th style="width: 60px;">状态</th>
                                <th style="width: 100px;">分类结果</th>
                                <th style="width: 35%;">模型评判</th>
                                <th class="sortable" onclick="sortTable(4, 'float')" style="width: 60px;">总耗时 ↕</th>
                                <th style="width: 50px;">耗时过长</th>
                                <th class="sortable" onclick="sortTable(6, 'int')" style="width: 50px;">总步数 ↕</th>
                                <th style="width: 50px;">步数过多</th>
                            </tr>
                        </thead>
                        <tbody id="tableBody">{rows}</tbody>
                    </table>
                </div>
            </div>

            <button id="backToTop" onclick="window.scrollTo({{top: 0, behavior: 'smooth'}})">↑</button>

            <script>
                // --- 饼图初始化 ---
                const catData = {json.dumps(cat_counts, ensure_ascii=False)};
                const ctx = document.getElementById('categoryChart').getContext('2d');
                new Chart(ctx, {{
                    type: 'pie',
                    data: {{
                        labels: Object.keys(catData),
                        datasets: [{{
                            data: Object.values(catData),
                            backgroundColor: ['#34a853', '#ea4335', '#fbbc05', '#4285f4', '#9b59b6', '#34495e'],
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{ legend: {{ position: 'right', labels: {{ boxWidth: 12, font: {{ size: 11 }} }} }} }}
                    }}
                }});

                // --- 逻辑功能 ---
                let sortDirections = {{}};

                function applyFilters() {{
                    const status = document.getElementById('f_status').value;
                    const category = document.getElementById('f_category').value;
                    const overtime = document.getElementById('f_overtime').value;
                    const overstep = document.getElementById('f_overstep').value;

                    document.querySelectorAll('#tableBody tr').forEach(row => {{
                        const mStatus = (status === 'all' || row.getAttribute('data-status') === status);
                        const mCategory = (category === 'all' || row.getAttribute('data-category') === category);
                        const mOvertime = (overtime === 'all' || row.getAttribute('data-overtime') === overtime);
                        const mOverstep = (overstep === 'all' || row.getAttribute('data-overstep') === overstep);
                        row.style.display = (mStatus && mCategory && mOvertime && mOverstep) ? '' : 'none';
                    }});
                }}

                function sortTable(colIdx, type) {{
                    const tbody = document.getElementById('tableBody');
                    const rows = Array.from(tbody.rows);
                    sortDirections[colIdx] = !sortDirections[colIdx];
                    const dir = sortDirections[colIdx] ? 1 : -1;

                    rows.sort((a, b) => {{
                        let valA = a.cells[colIdx].getAttribute('data-val') || a.cells[colIdx].innerText.trim();
                        let valB = b.cells[colIdx].getAttribute('data-val') || b.cells[colIdx].innerText.trim();
                        if (type !== 'string') return (parseFloat(valA) - parseFloat(valB)) * dir;
                        return valA.localeCompare(valB, 'zh-CN') * dir;
                    }});
                    rows.forEach(row => tbody.appendChild(row));
                }}

                function resetAll() {{
                    ['f_status', 'f_category', 'f_overtime', 'f_overstep'].forEach(id => document.getElementById(id).value = 'all');
                    applyFilters();
                    sortDirections = {{0: false}};
                    sortTable(0, 'string');
                }}

                function copyAndNotify(el, text) {{
                    navigator.clipboard.writeText(text).then(() => {{
                        const tip = el.querySelector('.status-tip');
                        tip.innerText = '✅ 已复制';
                        setTimeout(() => tip.innerText = '📋', 1000);
                    }});
                }}

                window.onscroll = () => {{
                    document.getElementById("backToTop").style.display = (window.scrollY > 300) ? "block" : "none";
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