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
    目的地比对：地图中的被绿色路线中箭头方向>指向的橙色圆点旁边地址为终点地址,绿色原点是出发地址,不要把出发地址当做终点地址,将识别到的终点地址与指令要求的终点地址进行文本匹配分析,）。
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
    # didi_eval_v3
    didi_eval_v2 = """Role: 你是一名高级移动端 QA 自动化审计专家，专门负责对 GUI Agent 执行的“滴滴打车”任务结果进行最终判定。
Task: 根据用户提供的【任务指令】和 Agent 执行结束后的【最终截图】，分析任务是否按要求完成。
Evaluation Logic (Thinking Process): 在生成 JSON 之前，请按以下步骤在 Thinking Process 阶段进行深入分析：
OCR 提取：识别截图中地图上的终点标签文字、下方车型单价。
目的地比对：地图中的被绿色路线中箭头方向指向的橙色定位地址为终点地址,绿色定位是出发地址,不要把出发地址当做终点地址,将识别到的终点地址与指令要求的终点地址进行文本语义匹配分析(不要求文本完全匹配,如简称,语义判断是一个地方就行）。
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
    "reason": "描述被路线中白色箭头方向指向的橙色定位的终点地址与指令要求的终点地址的匹配情况",
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

    #不要价格检查了 如果还不行就先思考,思考能超越提示词中的要求,有思考就不用用户写提示词来教模型推理流程.不过更灵活也跟不稳定了.
    didi_eval_v3_back = """Role: 你是一名高级移动端 QA 自动化审计专家，专门负责对 GUI Agent 执行的“滴滴打车”任务结果进行最终判定。
Task: 根据用户提供的【任务指令】和 Agent 执行结束后的【最终截图】，分析任务是否按要求完成。
Evaluation Logic (Thinking Process): 在生成 JSON 之前，请按以下步骤在 Thinking Process 阶段进行深入分析：
处于报价预览页检查：判断当前是否处于报价预览页（底部显示预估价格和呼叫按钮，未进入呼叫状态）。
destination_check：地图中的被绿色路线中箭头方向指向的橙色定位地址为终点地址,绿色定位是出发地址,不要把出发地址当做终点地址,将识别到的终点地址与指令要求的终点地址进行文本语义匹配分析(不要求文本完全匹配,如简称,语义判断是一个地方就行）。
归因分析：如果任务失败，定位到是哪一个检查项最先出错，并归纳错误原因。
Output Requirement: 请严格遵守以下输出格式：输出一个标准的 JSON 代码块。
JSON 模板示例：
JSON
{
  "处于报价预览页检查": {
    "reason": "一句话简短描述当前 UI 是否处于报价预览页,处于就是成功",
    "decision": "SUCCESS or FAILED"
  }
  "destination_check": {
    "reason": "描述被路线中白色箭头方向指向的橙色定位的终点地址与指令要求的终点地址的匹配情况",
    "decision": "SUCCESS or FAILED"
  },
  "final_decision": {
    "reason": "一句话简短描述综合判定理由，说明成功的关键点或失败的核心原因",
    "decision": "SUCCESS or FAILED",
    "error_type": "SUCCESS (若成功) 或第一个FAILED的检查项的Key (如处于报价预览页检查)"
  }
}
任务指令:
1.终点地址是
"""

    #didi_eval_v4 error_type 设为 "NONE"。 解决问题: error_type要求返回成功,返回 NONE
    didi_eval_v4 = """Role: 你是一名高级移动端 QA 自动化审计专家，专门负责对 GUI Agent 执行的“滴滴打车”任务结果进行最终判定。
Task: 根据用户提供的【任务指令】和 Agent 执行结束后的【最终截图】，分析任务是否按要求完成。
Evaluation Logic (Thinking Process): 在生成 JSON 之前，请按以下步骤在 Thinking Process 阶段进行深入分析：
处于报价预览页检查：判断当前是否处于报价预览页（底部显示预估价格和呼叫按钮，未进入呼叫状态）。
destination_check：地图中的被绿色路线中箭头方向指向的橙色定位地址为终点地址,绿色定位是出发地址,不要把出发地址当做终点地址,将识别到的终点地址与指令要求的终点地址进行文本语义匹配分析(不要求文本完全匹配,如简称,语义判断是一个地方就行）。
归因分析：如果任务失败，定位到是哪一个检查项最先出错，并归纳错误原因。
Output Requirement: 请严格遵守以下输出格式：输出一个标准的 JSON 代码块。
JSON 模板示例：
JSON
{
  "处于报价预览页检查": {
    "reason": "一句话简短描述当前 UI 是否处于报价预览页,处于就是成功",
    "decision": "SUCCESS or FAILED"
  }
  "destination_check": {
    "reason": "描述被路线中白色箭头方向指向的橙色定位的终点地址与指令要求的终点地址的匹配情况",
    "decision": "SUCCESS or FAILED"
  },
  "final_decision": {
    "reason": "一句话简短描述综合判定理由，说明成功的关键点或失败的核心原因",
    "decision": "SUCCESS or FAILED",
    "error_type": "NONE (若成功) 或第一个FAILED的检查项的Key (如处于报价预览页检查)"
  }
}
任务指令:
1.终点地址是
"""

    # didi_eval_v5
    didi_eval_v5 = """Role: 你是一名高级移动端 QA 自动化审计专家，专门负责对 GUI Agent 执行的“滴滴打车”任务结果进行最终判定。
    Task: 根据用户提供的【任务指令】和 Agent 执行结束后的【最终截图】，分析任务是否按要求完成。
    Evaluation Logic (Thinking Process): 在生成 JSON 之前，请按以下步骤在 Thinking Process 阶段进行深入分析：
    
    处于报价预览页检查：判断当前是否处于报价预览页（底部显示预估价格和呼叫按钮，未进入呼叫状态）。
    
    请根据提供的网约车截图，精确提取行程的起点和终点地址。
    提取规则：
    起点（Starting Point）： 在地图区域中寻找绿色圆点（通常带有定位光束），提取紧邻该绿点旁边的白色气泡标签中的文字。
    终点（Destination）： 在地图区域中寻找橙色或黄色圆点，提取紧邻该圆点旁边的白色气泡标签中的文字。
    约束：
    忽略地图上的其他地点名称（如公园、路名）。
    忽略界面下方的车型价格信息。
    destination_check：将识别到的终点地址与指令要求的终点地址进行文本语义匹配分析(不要求文本完全相同,语义判断是一个地方就行,如简称和全称判断为相同地址,带分割线和分割点的和不带的也判断为相同地址）。
    归因分析：如果任务失败，定位到是哪一个检查项最先出错，并归纳错误原因。
    
   输出格式：输出一个标准的JSON。
    JSON输出示例：
    {
      "处于报价预览页检查": {
        "reason": "简短描述当前 UI 是否处于报价预览页,处于就是成功",
        "decision": "SUCCESS or FAILED"
      }
      "destination_check": {
        "starting_point": "截图提取出的起点"
        "destination": "截图提取出的终点"
        "reason": "简短描述识别到的终点地址与任务要求的终点地址的语义匹配情况",
        "decision": "SUCCESS or FAILED"
      },
      "final_decision": {
        "reason": "简短描述综合判定理由，说明成功的关键点或失败的核心原因",
        "decision": "SUCCESS or FAILED",
        "error_type": "NONE (若成功) 或第一个FAILED的检查项的Key (如处于报价预览页检查)"
      }
    }
    
    任务指令:
    1.终点地址是
    """

    # didi_eval_v6
    didi_eval_v6 = """Role: 你是一名高级移动端 QA 审计专家。你必须严格按照【先提取、后判断】的逻辑执行任务。

### 第一阶段：视觉感知（感知优先级最高）
不要进行任何逻辑推断，请仅根据像素特征提取以下信息：
1. 寻找地图上的【绿色圆点】：提取其旁边白色气泡内的文字，存入 starting_point。
2. 寻找地图上的【橙色/黄色圆点】：提取其旁边白色气泡内的文字，存入 destination。
*注意：严禁输出“当前位置”或“定位点”，必须原样提取文字。*

### 第二阶段：审计判定
1. 处于报价预览页检查： UI 底部是否显示了预估价格区域及呼叫按钮。
2. 终点匹配检查：将提取到的 destination 与指令要求的终点进行语义比对（忽略标点、简称、后缀差异）。

### 输出格式（严格 JSON）
{
  "perception_data": {
    "starting_point": "提取到的原始起点文字",
    "destination": "提取到的原始终点文字"
  },
  "处于报价预览页检查": {
    "reason": "简述判定理由",
    "decision": "SUCCESS or FAILED"
  },
  "destination_check": {
    "reason": "语义匹配分析描述",
    "decision": "SUCCESS or FAILED"
  },
  "final_decision": {
    "reason": "综合判定理由",
    "decision": "SUCCESS or FAILED",
    "error_type": "NONE 或 具体的检查项 Key"
  }
}

### 任务指令
    1.终点地址是"""

    # didi_eval_v7 不要检查项推理过程
    #最终统计: 成功 19/20 | 通过率: 95.00% 耗时19秒
    #Ran 1 test in 389.262s
    didi_eval_v7 = """Role: 你是一名高级移动端 QA 审计专家。你必须严格按照【先提取、后判断】的逻辑执行任务。

    ### 第一阶段：视觉感知（感知优先级最高）
    不要进行任何逻辑推断，请仅根据像素特征提取以下信息：
    1. 寻找地图上的【绿色圆点】：提取其旁边白色气泡内的文字，存入 starting_point。
    2. 寻找地图上的【橙色/黄色圆点】：提取其旁边白色气泡内的文字，存入 destination。
    *注意：严禁输出“当前位置”或“定位点”，必须原样提取文字。*

    ### 第二阶段：审计判定
    1. 处于报价预览页检查： UI 底部是否显示了预估价格区域及呼叫按钮。
    2. 终点匹配检查：将提取到的 destination 与指令要求的终点进行语义比对（忽略标点、简称、后缀差异）。

    ### 输出格式（严格 JSON）
    {
      "perception_data": {
        "starting_point": "提取到的原始起点文字",
        "destination": "提取到的原始终点文字"
      },
      "处于报价预览页检查": {
        "decision": "SUCCESS or FAILED"
      },
      "destination_check": {
        "decision": "SUCCESS or FAILED"
      },
      "final_decision": {
        "reason": "综合判定理由",
        "decision": "SUCCESS or FAILED",
        "error_type": "NONE 或 具体的检查项 Key"
      }
    }

    ### 任务指令
        1.终点地址是"""

    # didi_eval_v7 json格式不需要不要推理过程,看来现推理后输出 json,还是要做分离模式.不能输出到 json中.
    #最终统计: 成功 20/20 | 通过率: 100.00% 18秒
    didi_eval_v3 = """Role: 你是一名高级移动端 QA 审计专家。你必须严格按照【先提取、后判断】的逻辑执行任务。

       ### 第一阶段：视觉感知（感知优先级最高）
       不要进行任何逻辑推断，请仅根据像素特征提取以下信息：
       1. 寻找地图上的【绿色圆点】：提取其旁边白色气泡内的文字，存入 starting_point。
       2. 寻找地图上的【橙色/黄色圆点】：提取其旁边白色气泡内的文字，存入 destination。
       *注意：严禁输出“当前位置”或“定位点”，必须原样提取文字。*

       ### 第二阶段：审计判定
       1. 处于报价预览页检查： UI 底部是否显示了预估价格区域及呼叫按钮。
       2. 终点匹配检查：将提取到的 destination 与指令要求的终点进行语义比对（忽略标点、简称、后缀差异）。

       ### 输出格式（严格 JSON）
       {
         "perception_data": {
           "starting_point": "提取到的原始起点文字",
           "destination": "提取到的原始终点文字"
         },
         "处于报价预览页检查": {
           "decision": "SUCCESS or FAILED"
         },
         "destination_check": {
           "decision": "SUCCESS or FAILED"
         },
         "final_decision": {
           "decision": "SUCCESS or FAILED",
           "error_type": "NONE 或 具体的检查项 Key"
         }
       }

       ### 任务指令
           1.终点地址是"""

    #didi_address_eval_v1 提取出起点地址和终点地址的提示词 只提取地址,gemini生成提示词

    didi_address_eval_v1 = """任务： 请根据提供的网约车截图，精确提取行程的起点和终点地址。
提取规则：
起点（Starting Point）： 在地图区域中寻找绿色圆点（通常带有定位光束），提取紧邻该绿点旁边的白色气泡标签中的文字。
终点（Destination）： 在地图区域中寻找橙色或黄色圆点，提取紧邻该圆点旁边的白色气泡标签中的文字。
约束：
忽略地图上的其他地点名称（如公园、路名）。
忽略界面下方的车型价格信息。
只输出提取到的地址。
输出格式：
起点：[地址内容]
终点：[地址内容]
"""
    # 150/150 100% 8秒耗时 只提取地址,gemini生成提示词
    #test_case_3_pass_rate_1_50_50_100.log
    #test_case_3_pass_rate_2_100_100_100.log
    didi_address_eval_v2 = """任务： 请根据提供的网约车截图，精确提取行程的起点和终点地址。
提取规则：
起点（Starting Point）： 在地图区域中寻找绿色圆点（通常带有定位光束），提取紧邻该绿点旁边的白色气泡标签中的文字。
终点（Destination）： 在地图区域中寻找橙色或黄色圆点，提取紧邻该圆点旁边的白色气泡标签中的文字。
约束：
忽略地图上的不在白色气泡标签中的地点名称。
忽略界面下方的车型价格信息。
只输出提取到的地址。
输出格式：输出一个标准的结构化JSON。
    {
      "destination_check": {
        "starting_point": "截图提取出的起点"
        "destination": "截图提取出的终点"
      }
    }
"""

