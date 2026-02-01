#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片分辨率缩放工具（单图或批量）

用法:
    python resize_img.py <输入路径> [缩放比例] [输出目录]
示例:
    python resize_img.py screenshot.png 0.5
    python resize_img.py ./screenshots 0.5 ./scaled_output
"""

from PIL import Image
import os
import sys

def resize_img_file(input_path, output_path=None, scale=0.5, step=0):
    """
    缩放单张图片
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    img = Image.open(input_path)
    width, height = img.size
    new_width = int(width * scale)
    new_height = int(height * scale)
    resized_img = img.resize((new_width, new_height), Image.LANCZOS)

    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_scaled_{scale}_{step}{ext}"

    resized_img.save(output_path)
    print(f"✅ 已保存: {output_path} ({new_width}x{new_height})")
    return output_path

def resize_img_folder(folder_path, output_folder=None, scale=0.5):
    """
    批量缩放文件夹下所有图片
    """
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"输入目录不存在: {folder_path}")

    if output_folder is None:
        output_folder = os.path.join(folder_path, "scaled")
    os.makedirs(output_folder, exist_ok=True)

    supported_ext = (".png", ".jpg", ".jpeg", ".bmp", ".webp")
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(supported_ext):
            input_path = os.path.join(folder_path, filename)
            output_path = os.path.join(output_folder, filename)
            resize_img_file(input_path, output_path, scale)

    print(f"✅ 批量缩放完成，输出目录: {output_folder}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ 用法: python resize_img.py <输入路径> [缩放比例] [输出目录]")
        sys.exit(1)

    input_path = sys.argv[1]
    scale = float(sys.argv[2]) if len(sys.argv) >= 3 else 0.5
    output_dir = sys.argv[3] if len(sys.argv) >= 4 else None

    if os.path.isfile(input_path):
        # 单张图片
        resize_img_file(input_path, output_dir, scale)
    elif os.path.isdir(input_path):
        # 批量处理文件夹
        resize_img_folder(input_path, output_dir, scale)
    else:
        print("❌ 输入路径不是文件也不是目录")
        sys.exit(1)