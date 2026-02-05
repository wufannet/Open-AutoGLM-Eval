import datetime
# 程序开始时间
tag = "总总程序"
program_start_time = datetime.now()
print(f"{tag}开始时间：")
print(program_start_time.strftime("%Y-%m-%d %H:%M:%S"))
# 程序占位

program_end_time = datetime.now()
duration = program_end_time - program_start_time
print(f"{tag}开始时间: {program_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{tag}结束时间: {program_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{tag}运行耗时: {str(duration)[:-5]}")  # 时分秒格式
print(f"{tag}运行耗时秒: {duration.total_seconds():.1f} 秒")