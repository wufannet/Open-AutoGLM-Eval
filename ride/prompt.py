class Prompt:
    """应用名称常量类"""
    click = """请分析提供的安卓手机截图，判断当前界面是否存在匹配目标的坐标。若存在，请识别其位置，并输出以下结构化数据：
    {
      "has": true|false,
      "coordinate": [x, y]
    }

    字段说明:
    - `has`:  
      - `true`：存在。  
      - `false`：不存在。
    - `coordinate`:  
      - 若 `has == true`，则为目标中心点坐标 `[x, y]`（单位：像素，基于截图分辨率）。  
      - 若 `has == false`，则设为 `[-1, -1]`。

    要求:
    1. 输出必须是标准 JSON 格式，仅包含上述两个字段。
    2. 坐标 `(x, y)` 应为整数

    示例输出（存在目标）：
    {
      "has": true,
      "coordinate": [930, 85]
    }

    示例输出（不存在目标）：
    {
      "has": false,
      "coordinate": [-1, -1]
    }

    目标: """

    click_destination = """请分析提供的安卓手机截图，判断当前界面是否存在匹配目标的坐标。若存在，请识别其位置，并输出以下结构化数据：
    {
      "has": true|false,
      "coordinate": [x, y]
    }

    字段说明:
    - `has`:  
      - `true`：存在。  
      - `false`：不存在。
    - `coordinate`:  
      - 若 `has == true`，则为目标中心点坐标 `[x, y]`（单位：像素，基于截图分辨率）。  
      - 若 `has == false`，则设为 `[-1, -1]`。

    要求:
    1. 输出必须是标准 JSON 格式，仅包含上述两个字段。
    2. 坐标 `(x, y)` 应为整数

    示例输出（存在目标）：
    {
      "has": true,
      "coordinate": [930, 85]
    }

    示例输出（不存在目标）：
    {
      "has": false,
      "coordinate": [-1, -1]
    }

    目标:
    “您想去哪儿？”文字区域的左侧部分，以确保不误触右侧的推荐地址。"""

    didi_eval = """Role: 你是一名高级移动端 QA 自动化审计专家，专门负责对 GUI Agent 执行的“滴滴打车”任务结果进行最终判定。
    Task: 根据用户提供的【任务指令】和 Agent 执行结束后的【最终截图】，分析任务是否按要求完成。
    Evaluation Logic (Thinking Process): 在生成 JSON 之前，请按以下步骤在 Thinking Process 阶段进行深入分析：
    状态判定：判断当前是否处于报价预览页（是否有多个打车选项的价格列表），并确认 Agent 是否停留在该页（未误触呼叫按钮）。
    目的地比对：截图上部分地图中的橙色小圆环旁边地址为终点地址,将识别到的终点地址与指令要求的终点地址进行文本匹配分析,）。
    归因分析：如果任务失败，定位到是哪一个检查项最先出错，并归纳错误原因。
    Output Requirement: 请严格遵守以下输出格式：输出一个标准的 JSON 代码块。
    JSON 模板示例：
    JSON
    {
      "is_on_call_page": {
        "decision": "SUCCESS or FAILED"
      }
      ,
        "price_list_check": {
        "decision": "SUCCESS or FAILED"
      },
      "destination_check": {
        "decision": "SUCCESS or FAILED"
      },
      "final_decision": {
        "reason": "一句话简短描述综合判定理由，说明成功的关键点或失败的核心原因",
        "decision": "SUCCESS or FAILED",
        "error_type": "SUCCESS (若成功) 或第一个失败检查项的 Key (如 is_on_call_page)"
      }
    }
    要求:
    1. 输出必须是标准 JSON 格式。
    2.终点地址是
    """

    didi_eval_v1 = """Role: 你是一名高级移动端 QA 自动化审计专家，专门负责对 GUI Agent 执行的“滴滴打车”任务结果进行最终判定。
Task: 根据用户提供的【任务指令】和 Agent 执行结束后的【最终截图】，分析任务是否按要求完成。
Evaluation Logic (Thinking Process): 在生成 JSON 之前，请按以下步骤在 Thinking Process 阶段进行深入分析：
OCR 提取：识别截图中地图上的终点标签文字、下方车型单价。
目的地比对：截图上部分地图中的橙色小圆环旁边地址为终点地址,将识别到的终点地址与指令要求的终点地址进行文本语义匹配分析(不要求文本完全匹配,如简称,语义判断是一个地方就行）。
状态判定：判断当前是否处于报价预览页（是否有具体价格）。
归因分析：如果任务失败，定位到是哪一个检查项最先出错，并归纳错误原因。
Output Requirement: 请严格遵守以下输出格式：输出一个标准的 JSON 代码块。
JSON 模板示例：
JSON
{
  "is_on_call_page": {
    "reason": "一句话简短描述当前 UI 是否处于预览页及底部按钮状态是否符合合规要求（未下单）",
    "decision": "SUCCESS or FAILED"
  }
  ,
    "price_list_check": {
    "reason": "一句话简短描述是否看到了具体的车型价格列表",
    "decision": "SUCCESS or FAILED"
  },
  "destination_check": {
    "reason": "一句话简短描述识别到的地址与目标地址的匹配情况",
    "decision": "SUCCESS or FAILED"
  },
  "final_decision": {
    "reason": "一句话简短描述综合判定理由，说明成功的关键点或失败的核心原因",
    "decision": "SUCCESS or FAILED",
    "error_type": "SUCCESS (若成功) 或第一个失败检查项的 Key (如 is_on_call_page)"
  }
}
要求:
1. 输出必须是标准 JSON 格式。
2.终点地址是
"""

    didi_eval_v2 = """Role: 你是一名高级移动端 QA 自动化审计专家，专门负责对 GUI Agent 执行的“滴滴打车”任务结果进行最终判定。
Task: 根据用户提供的【任务指令】和 Agent 执行结束后的【最终截图】，分析任务是否按要求完成。
Evaluation Logic (Thinking Process): 在生成 JSON 之前，请按以下步骤在 Thinking Process 阶段进行深入分析：
OCR 提取：识别截图中地图上的终点标签文字、下方车型单价。
目的地比对：截图上部分地图中的橙色小圆环旁边地址为终点地址,将识别到的终点地址与指令要求的终点地址进行文本语义匹配分析(不要求文本完全匹配,如简称,语义判断是一个地方就行）。
处于报价预览页检查：判断当前是否处于报价预览页（底部显示预估价格和呼叫按钮，未进入呼叫状态）。
归因分析：如果任务失败，定位到是哪一个检查项最先出错，并归纳错误原因。
Output Requirement: 请严格遵守以下输出格式：输出一个标准的 JSON 代码块。
JSON 模板示例：
JSON
{
  "处于报价预览页检查": {
    "reason": "一句话简短描述当前 UI 是否处于报价预览页,处于就是成功",
    "decision": "SUCCESS or FAILED"
  }
  ,
    "price_list_check": {
    "reason": "一句话简短描述是否看到了具体的车型价格列表",
    "decision": "SUCCESS or FAILED"
  },
  "destination_check": {
    "reason": "一句话简短描述识别到的地址与目标地址的匹配情况",
    "decision": "SUCCESS or FAILED"
  },
  "final_decision": {
    "reason": "一句话简短描述综合判定理由，说明成功的关键点或失败的核心原因",
    "decision": "SUCCESS or FAILED",
    "error_type": "SUCCESS (若成功) 或第一个失败检查项的 Key (如 is_on_call_page)"
  }
}
要求:
1. 输出必须是标准 JSON 格式。
2.终点地址是
"""