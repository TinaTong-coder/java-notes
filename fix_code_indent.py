#!/usr/bin/env python3
"""
修复markdown文件中代码块的缩进
支持Java、Python、JavaScript等语言
"""

import os
import re
import sys


def fix_java_indent(code_lines):
    """修复Java代码的缩进"""
    result = []
    indent_level = 0
    indent_str = "    "  # 4个空格

    for line in code_lines:
        stripped = line.strip()

        if not stripped:
            result.append("")
            continue

        # 处理右大括号：先减少缩进再添加
        if stripped.startswith('}'):
            indent_level = max(0, indent_level - 1)

        # 添加当前缩进
        indented_line = indent_str * indent_level + stripped
        result.append(indented_line)

        # 处理左大括号：增加缩进
        if stripped.endswith('{'):
            indent_level += 1
        elif stripped.endswith('}'):
            # 已经在前面处理过了
            pass
        # 处理 } else { 或 } catch { 等情况
        elif stripped.startswith('}') and '{' in stripped:
            indent_level += 1

    return result


def fix_python_indent(code_lines):
    """修复Python代码的缩进"""
    result = []
    indent_level = 0
    indent_str = "    "  # 4个空格

    for line in code_lines:
        stripped = line.strip()

        if not stripped or stripped.startswith('#'):
            result.append(stripped)
            continue

        # 添加当前缩进
        indented_line = indent_str * indent_level + stripped
        result.append(indented_line)

        # 处理缩进增加的情况
        if stripped.endswith(':') and not stripped.startswith('#'):
            indent_level += 1

        # 处理缩进减少的情况（如 return, break, continue 后面可能需要减少）
        # 这个比较复杂，暂时不处理

    return result


def process_markdown_file(file_path, dry_run=False):
    """处理单个markdown文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"错误：无法读取文件 {file_path}: {e}")
        return False

    # 分割内容为行
    lines = content.split('\n')
    result_lines = []
    in_code_block = False
    code_lang = None
    code_block_lines = []
    modified = False

    for line in lines:
        # 检测代码块开始
        if line.strip().startswith('```'):
            if not in_code_block:
                # 代码块开始
                in_code_block = True
                match = re.match(r'```(\w+)', line.strip())
                code_lang = match.group(1).lower() if match else None
                code_block_lines = []
                result_lines.append(line)
            else:
                # 代码块结束
                in_code_block = False

                # 检查是否需要修复缩进
                needs_fix = False
                if code_lang in ['java', 'c', 'cpp', 'c++', 'javascript', 'js', 'go']:
                    # 检查是否有行完全没有缩进但应该有缩进
                    for code_line in code_block_lines:
                        stripped = code_line.strip()
                        if stripped and code_line == stripped:  # 没有任何缩进
                            if any(kw in stripped for kw in [
                                'return ', 'if (', 'for (', 'while (',
                                'throw ', 'case ', 'break;', 'continue;'
                            ]):
                                needs_fix = True
                                break

                if needs_fix and code_lang in ['java', 'c', 'cpp', 'c++', 'javascript', 'js', 'go']:
                    fixed_lines = fix_java_indent(code_block_lines)
                    result_lines.extend(fixed_lines)
                    modified = True
                elif needs_fix and code_lang in ['python', 'py']:
                    fixed_lines = fix_python_indent(code_block_lines)
                    result_lines.extend(fixed_lines)
                    modified = True
                else:
                    result_lines.extend(code_block_lines)

                result_lines.append(line)
                code_lang = None
                code_block_lines = []
        elif in_code_block:
            code_block_lines.append(line)
        else:
            result_lines.append(line)

    if modified:
        if dry_run:
            print(f"[DRY RUN] 将修改: {file_path}")
        else:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(result_lines))
                print(f"✓ 已修复: {file_path}")
            except Exception as e:
                print(f"错误：无法写入文件 {file_path}: {e}")
                return False
        return True

    return False


def main():
    # 查找所有需要修复的markdown文件
    files_to_fix = [
        "./docs/JVM学习笔记.md",
        "./docs/设计模式.md",
        "./docs/Java 8 新特性.md",
        "./docs/多线程和高并发.md",
        "./docs/Socket.md",
        "./docs/Java基础笔记.md",
        "./docs/Java并发包/ThreadLocal源码解析.md",
        "./docs/Java并发包/ReentrantLock源码解析.md",
        "./docs/Java并发包/Thread源码解析.md",
        "./docs/Java并发包/AQS源码详解.md",
        "./docs/剑指Offer/随机刷题(三).md",
        "./docs/剑指Offer/位运算和哈希表.md",
        "./docs/剑指Offer/排序、回溯和分治.md",
        "./docs/剑指Offer/树.md",
        "./docs/剑指Offer/链表.md",
        "./docs/LeetCode/data_structure/stack_queue.md",
    ]

    dry_run = '--dry-run' in sys.argv
    modified_count = 0

    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if process_markdown_file(file_path, dry_run):
                modified_count += 1

    print(f"\n完成! 共修复 {modified_count} 个文件")


if __name__ == '__main__':
    main()
