"""Read-only checks for the current IdeaFlow stage; never creates an archive."""

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md", ".gitignore", "docs/proposal/IdeaFlow-立项报告.docx",
    "docs/meetings/第一次组会纪要.md",
    "docs/requirements/决策与任务跟踪-需求分析.md",
    "docs/weekly/第1周-唐逸飞-决策与任务跟踪.md",
    "docs/testing/ProgressGate-第一阶段验证记录.md",
    "docs/coordination/仓库现状与集成待办.md",
    "docs/样例/跨模块样例数据.json", "progressgate/README.md",
    "progressgate/backend/app/main.py", "progressgate/backend/requirements.txt",
    "progressgate/backend/uv.lock", "progressgate/frontend/src/App.vue",
    "progressgate/frontend/package-lock.json",
]
EXCLUDED_DIRS = {
    "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache",
    "dist", "build", "target", ".codex", ".aws", ".ssh", "outputs", "delivery",
}
PRIVATE_KEY = re.compile(rb"-----BEGIN (?:OPENSSH|RSA|EC|DSA|ENCRYPTED)?\s*PRIVATE KEY-----")


def git(*args, input_text=None, check=True):
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], input=input_text,
        capture_output=True, text=True, check=check,
    )


def excluded(path):
    p = PurePosixPath(path)
    return (
        bool(set(p.parts[:-1]) & EXCLUDED_DIRS)
        or (p.name.startswith(".env") and p.name not in {".env.example", ".env.sample"})
        or p.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".pem", ".key", ".save", ".pyc", ".log", ".zip"}
        or p.name.endswith((".db-wal", ".db-shm", ".sqlite-wal", ".sqlite-shm"))
    )


def inspect():
    errors, warnings = [], []
    git("rev-parse", "--git-dir")
    tracked = git("ls-files", "-z").stdout.split("\0")
    tracked = {name for name in tracked if name}
    for name in REQUIRED:
        if not (ROOT / name).is_file():
            errors.append(f"缺少阶段材料：{name}")
        elif name not in tracked:
            warnings.append(f"阶段材料尚未加入 Git：{name}")
    for name in sorted(tracked):
        path = ROOT / name
        if excluded(name):
            errors.append(f"Git 跟踪了应排除的文件：{name}")
        if path.is_symlink():
            errors.append(f"需人工核对的符号链接：{name}")
        elif path.is_file() and path.stat().st_size > 10 * 1024 * 1024:
            errors.append(f"超过 10 MiB，需确认是否应交付：{name}")
        elif path.is_file() and PRIVATE_KEY.search(path.read_bytes()):
            errors.append(f"当前文件疑似含私钥，仅报告路径：{name}")
    # Check real branch/tag history. Local application checkpoints are not
    # delivery refs and must be excluded by making a clean Git copy later.
    refs = git("for-each-ref", "--format=%(refname)").stdout.splitlines()
    auxiliary_refs = [
        ref for ref in refs
        if not ref.startswith(("refs/heads/", "refs/remotes/", "refs/tags/"))
    ]
    for ref in auxiliary_refs:
        if not ref.startswith("refs/codex/"):
            warnings.append(f"正式分支以外的引用需人工确认：{ref}")
    objects = {}
    for line in git("rev-list", "--objects", "--branches", "--remotes", "--tags").stdout.splitlines():
        sha, _, name = line.partition(" ")
        objects.setdefault(sha, set())
        if name:
            objects[sha].add(name)
            if excluded(name):
                errors.append(f"Git 历史包含应排除的路径：{name}")
    metadata = git(
        "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
        input_text="\n".join(objects) + "\n",
    ).stdout.splitlines()
    for row in metadata:
        sha, kind, raw_size = row.split()
        if kind != "blob":
            continue
        names = ", ".join(sorted(objects[sha])) or sha[:12]
        if int(raw_size) > 10 * 1024 * 1024:
            errors.append(f"Git 历史含大于 10 MiB 的对象：{names}")
            continue
        blob = subprocess.run(
            ["git", "-C", str(ROOT), "cat-file", "blob", sha],
            capture_output=True, check=True,
        ).stdout
        if PRIVATE_KEY.search(blob):
            errors.append(f"Git 历史疑似含私钥，仅报告路径：{names}")
    integrity = git("fsck", "--full", "--no-dangling", check=False)
    if integrity.returncode:
        errors.append("Git 对象完整性检查失败：" + integrity.stderr.strip())
    status = git("-c", "core.quotepath=false", "status", "--porcelain").stdout.splitlines()
    if status:
        warnings.append(f"工作区仍有 {len(status)} 项未提交变化；归档前需核对。")
    branches = []
    for row in git(
        "for-each-ref", "--format=%(refname:short)\t%(objectname)\t%(subject)",
        "refs/remotes/origin/",
    ).stdout.splitlines():
        name, sha, subject = row.split("\t", 2)
        if name.endswith("/HEAD"):
            continue
        branches.append({"branch": name, "commit": sha, "subject": subject})
    return {
        "group": 7,
        "scope": "第四模块阶段成果及本地仓库材料检查，不是全组验收",
        "archive_created": False,
        "whole_repository_packaging": "暂缓，等待组员完成提交和组长指示",
        "current_branch": git("branch", "--show-current").stdout.strip(),
        "head": git("rev-parse", "HEAD").stdout.strip(),
        "remote_refs_note": "本地缓存；运行此脚本前按需手动 git fetch origin",
        "remote_branches": branches,
        "history_scope": "本地分支、远程分支和标签可达的历史；不含本地应用检查点",
        "local_auxiliary_ref_count": len(auxiliary_refs),
        "packaging_requires_clean_git_copy": bool(auxiliary_refs),
        "packaging_note": "未来从已确认分支制作干净 Git 副本并保留 .git；不能直接压缩含本地工具快照的工作目录",
        "tracked_file_count": len(tracked),
        "errors": sorted(set(errors)),
        "warnings": warnings,
        "repository_checks_passed": not errors and not warnings,
        "overall_submission_ready": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="输出 JSON；仍不生成压缩包")
    args = parser.parse_args()
    try:
        result = inspect()
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        print(f"检查未完成：{exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"第 {result['group']} 组 | 分支 {result['current_branch']} | {result['head'][:12]}")
        for branch in result["remote_branches"]:
            print(f"  {branch['branch']}: {branch['commit'][:12]} {branch['subject']}")
        for message in result["errors"]:
            print("错误：" + message)
        for message in result["warnings"]:
            print("待核对：" + message)
        if result["local_auxiliary_ref_count"]:
            print(f"本地另有 {result['local_auxiliary_ref_count']} 个工具快照引用，不属于正式分支交付范围。")
            print(result["packaging_note"])
        print("仓库检查：" + ("通过" if result["repository_checks_passed"] else "有待处理项"))
        print("整体打包暂缓；本脚本没有生成压缩包，也不表示全组交付已完成。")
    return 0 if result["repository_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
