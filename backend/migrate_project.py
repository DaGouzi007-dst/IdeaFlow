"""把演示数据从 demo-project 迁移到真实项目编号。

用法（在 backend 目录）：
    ..\\.venv\\Scripts\\python.exe migrate_project.py <第一部分的项目UUID>

出处里的 projectId 同步修改，否则第四部分的项目校验不通过。
"""

import json
import sys

from sqlmodel import Session, select

import models
from models import Idea, IdeaSource

OLD = "demo-project"


def main(new_id: str) -> None:
    with Session(models.engine) as session:
        ideas = session.exec(select(Idea).where(Idea.project_id == OLD)).all()
        for idea in ideas:
            idea.project_id = new_id
            rows = session.exec(select(IdeaSource).where(IdeaSource.idea_id == idea.idea_id)).all()
            for row in rows:
                if row.source_ref and row.source_ref.startswith("{"):
                    data = json.loads(row.source_ref)
                    data["projectId"] = new_id
                    row.source_ref = json.dumps(data, ensure_ascii=False)
        session.commit()
        print(f"改了 {len(ideas)} 张卡片，出处里的 projectId 也一起换了")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法：python migrate_project.py <项目UUID>")
        raise SystemExit(1)
    main(sys.argv[1])
