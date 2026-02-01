#!/usr/bin/env bash
# 上面这一行是核心：强制指定用 bash 执行脚本

# 示例：验证当前使用的 shell
echo "当前使用的 shell 解释器是：$BASH"
echo "bash 版本：$BASH_VERSION"

# 测试 bash 特有语法（比如 [[ 条件判断，sh 不支持）
if [[ "$BASH_VERSION" != "" ]]; then
    echo "✅ 脚本已成功使用 bash 执行"
else
    echo "❌ 脚本未使用 bash 执行"
fi