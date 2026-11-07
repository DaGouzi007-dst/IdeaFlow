#!/usr/bin/env python3
"""IdeaFlow · 第一模块（会话导入与管理）—— 会话读取演示脚本

第一周交付，对齐《开工方案与接口约定（讨论稿）》：
  1. 读取组内聚合样例 docs/样例/跨模块样例数据.json，展示项目、会话标题、消息角色和内容；
  2. 读取并校验导入格式样例 docs/样例/会话导入样例.json，
     逐项检查《会话导入与管理-格式说明》第 4 节的规则。

仅使用 Python 标准库，无需安装任何依赖：

    python demo.py
    python demo.py --file 某个导入格式文件.json
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROLES = ("user", "assistant", "system")


# ---------- 工具函数 ----------

def repo_root() -> Path:
    """demo.py 位于 仓库根/sessionhub/ 下，向上两级即仓库根。"""
    return Path(__file__).resolve().parent.parent


def find_first(candidates):
    for p in candidates:
        if p.is_file():
            return p
    return None


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fmt_time(value):
    if not value:
        return "时间未知"
    return str(value).replace("T", " ")


def show_message(index: int, msg: dict) -> None:
    role = str(msg.get("role", "?"))
    time_text = fmt_time(msg.get("created_at"))
    content = str(msg.get("content", ""))
    print(f"    消息 {index} [{role:<9}] {time_text}  {content}")


def show_conversation(title, source, source_conversation_id, messages):
    scid = source_conversation_id if source_conversation_id is not None else "null"
    print(f"  会话: {title}")
    print(f"  来源: {source}    source_conversation_id: {scid}")
    for offset, msg in enumerate(messages, start=1):
        show_message(offset, msg)


# ---------- 第 1 部分：组内聚合样例 ----------

def run_aggregate_demo(data: dict, label: str) -> None:
    print(f"\n[1/2] 读取组内聚合样例（{label}）")
    print("-" * 56)
    projects = {
        p.get("project_id"): p.get("name", "未命名项目")
        for p in data.get("projects", [])
    }
    messages_all = data.get("messages", [])
    conversations = data.get("conversations", [])
    if not conversations:
        print("  （样例中没有会话数据）")
        return
    for conv in conversations:
        project_name = projects.get(conv.get("project_id"), "未知项目")
        print(f"  项目: {project_name}")
        own = [
            m for m in messages_all
            if m.get("conversation_id") == conv.get("conversation_id")
        ]
        show_conversation(
            conv.get("title"),
            conv.get("source"),
            conv.get("source_conversation_id"),
            own,
        )
        print()


# ---------- 第 2 部分：导入格式校验 ----------

def check_import_body(data):
    """按《会话导入与管理-格式说明》第 4 节校验导入请求体。

    返回 (checks, errors)：
      checks 为 (检查项, 是否通过, 备注) 列表；
      errors 为不通过的明细信息。
    """
    checks, errors = [], []

    def record(name, ok, err_note="", ok_note="", to_errors=True):
        # err_note：未通过时显示；ok_note：通过时展示的备注；to_errors：是否并入明细列表
        checks.append((name, ok, err_note if not ok else ok_note))
        if not ok and err_note and to_errors:
            errors.append(err_note)

    if not isinstance(data, dict):
        record("请求体为 JSON 对象", False, "请求体必须是 JSON 对象")
        return checks, errors
    record("请求体为 JSON 对象", True)

    title = data.get("title")
    record(
        "title 非空字符串",
        isinstance(title, str) and bool(title.strip()),
        err_note="title 必须是非空字符串",
    )

    source = data.get("source")
    record(
        "source 非空字符串",
        isinstance(source, str) and bool(source.strip()),
        err_note="source 必须是非空字符串",
    )

    scid = data.get("source_conversation_id")
    record(
        "source_conversation_id 为字符串或 null",
        scid is None or (isinstance(scid, str) and bool(scid.strip())),
        err_note="source_conversation_id 必须是非空字符串或 null",
    )

    messages = data.get("messages")
    if not isinstance(messages, list) or len(messages) == 0:
        record("messages 非空数组", False, err_note="messages 必须是非空数组")
        return checks, errors
    record("messages 非空数组", True, ok_note=f"共 {len(messages)} 条")

    role_ok = content_ok = time_ok = True
    null_time_count = 0
    for i, msg in enumerate(messages, start=1):
        if not isinstance(msg, dict):
            role_ok = content_ok = time_ok = False
            errors.append(f"第 {i} 条消息必须是 JSON 对象")
            continue
        if msg.get("role") not in ROLES:
            role_ok = False
            errors.append(
                f"第 {i} 条消息的 role 取值无效：{msg.get('role')!r}"
                f"（允许：user、assistant、system）"
            )
        content = msg.get("content")
        if not isinstance(content, str) or not content.strip():
            content_ok = False
            errors.append(f"第 {i} 条消息的 content 必须是非空字符串")
        created = msg.get("created_at")
        if created is None:
            null_time_count += 1
        elif isinstance(created, str):
            try:
                parsed = datetime.fromisoformat(created)
                if parsed.tzinfo is None:
                    time_ok = False
                    errors.append(
                        f"第 {i} 条消息的 created_at 缺少时区信息：{created}"
                    )
            except ValueError:
                time_ok = False
                errors.append(
                    f"第 {i} 条消息的 created_at 不是合法的 ISO 8601 时间：{created}"
                )
        else:
            time_ok = False
            errors.append(f"第 {i} 条消息的 created_at 必须是字符串或 null")

    record(
        "role 取值合法",
        role_ok,
        err_note="" if role_ok else "存在非法 role（明细见下）",
        to_errors=False,
    )
    record(
        "content 非空",
        content_ok,
        err_note="" if content_ok else "存在空 content（明细见下）",
        to_errors=False,
    )
    time_note = f"{null_time_count} 条为 null，其余均带时区" if null_time_count else "均带时区"
    record(
        "created_at 为带时区 ISO 8601 或 null",
        time_ok,
        err_note="" if time_ok else "存在不合法的 created_at（明细见下）",
        ok_note=time_note,
        to_errors=False,
    )

    return checks, errors


def run_import_demo(data: dict, label: str, banner: str = "[2/2]") -> bool:
    header = f"导入格式样例（{label}）"
    if banner:
        print(f"\n{banner} 校验并读取{header}")
    else:
        print(f"\n校验并读取{header}")
    print("-" * 56)

    checks, errors = check_import_body(data)
    for name, ok, note in checks:
        mark = "通过" if ok else "未通过"
        suffix = f"（{note}）" if note else ""
        print(f"  [{mark}] {name}{suffix}")
    if errors:
        print("\n  格式检查发现问题：")
        for err in errors:
            print(f"    - {err}")
        return False

    print()
    show_conversation(
        data.get("title"),
        data.get("source"),
        data.get("source_conversation_id"),
        data.get("messages", []),
    )
    return True


# ---------- 入口 ----------

def main() -> int:
    parser = argparse.ArgumentParser(description="IdeaFlow 会话读取演示（第一模块）")
    parser.add_argument("--file", help="校验并展示一个符合导入格式的 JSON 文件")
    args = parser.parse_args()

    root = repo_root()
    samples_dir = Path(__file__).resolve().parent / "samples"

    print("=" * 56)
    print(" IdeaFlow 会话读取演示 —— 第一模块：会话导入与管理")
    print("=" * 56)

    if args.file:
        target = Path(args.file)
        if not target.is_file():
            print(f"找不到文件：{target}")
            return 1
        data = load_json(target)
        ok = run_import_demo(data, str(target), banner="")
        print("\n演示完成。" if ok else "\n演示结束：文件未通过格式检查。")
        return 0 if ok else 1

    # 1) 组内聚合样例：优先仓库 docs/样例/，找不到时用本目录 samples/ 副本
    fixture = find_first([
        root / "docs" / "样例" / "跨模块样例数据.json",
        samples_dir / "跨模块样例数据.json",
    ])
    if fixture:
        run_aggregate_demo(load_json(fixture), fixture.name)
    else:
        print("\n[1/2] 未找到聚合样例（docs/样例/跨模块样例数据.json），跳过。")

    # 2) 导入格式样例
    sample = find_first([
        root / "docs" / "样例" / "会话导入样例.json",
        samples_dir / "会话导入样例.json",
    ])
    ok = True
    if sample:
        ok = run_import_demo(load_json(sample), sample.name)
    else:
        print("\n[2/2] 未找到导入格式样例（docs/样例/会话导入样例.json），跳过。")
        print("      请确认已按《交付操作指南》把 docs 下的文件复制进仓库。")

    print("\n演示完成。" if ok else "\n演示结束：存在未通过的检查项。")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
