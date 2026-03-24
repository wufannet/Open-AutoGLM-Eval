def _parse_response(content: str) -> tuple[str, str]:
    """
    Parse the model response into thinking and action parts.

    Parsing rules:
    1. If content contains 'finish(message=', everything before is thinking,
       everything from 'finish(message=' onwards is action.
    2. If rule 1 doesn't apply but content contains 'do(action=',
       everything before is thinking, everything from 'do(action=' onwards is action.
    3. Fallback: If content contains '<answer>', use legacy parsing with XML tags.
    4. Otherwise, return empty thinking and full content as action.

    Args:
        content: Raw response content.

    Returns:
        Tuple of (thinking, action).
    """
    # Rule 1: Check for finish(message=
    if "finish(message=" in content:
        parts = content.rsplit("finish(message=", 1)
        thinking = parts[0].strip()
        action = "finish(message=" + parts[1]
        return thinking, action

    # Rule 2: Check for do(action=
    if "do(action=" in content:
        parts = content.rsplit("do(action=", 1)
        thinking = parts[0].strip()
        action = "do(action=" + parts[1]
        return thinking, action

    # Rule 3: Fallback to legacy XML tag parsing
    if "<answer>" in content:
        parts = content.rsplit("<answer>", 1)
        thinking = parts[0].replace("<think>", "").replace("</think>", "").strip()
        action = parts[1].replace("</answer>", "").strip()
        return thinking, action

    # Rule 4: No markers found, return content as action
    return "", content

raw_content = """用户要求我执行以下任务：
1. 启动与进入：打开花小猪打车进入主页
2. 触发搜索：在主页点击"你要去哪儿"中的"你"字
3. 输入目的地：输入"襄阳东站北进站口"
4. 选择目标：在搜索结果列表中点击最匹配的选项
5. 判断页面状态并确认

当前屏幕显示的是系统桌面，我可以看到"花小猪打车"的图标在屏幕上（右下角位置）。

首先，我需要启动花小猪打车应用。根据允许的应用列表，花小猪打车是允许的应用之一。

我应该使用do(action="Launch", app="花小猪打车")来启动应用。
do(action="Launch", app="花小猪打车")"""
thinking, action = _parse_response(raw_content)
print(f"thinking: {thinking}")
print(f"####################")
print(f"action: {action}")