import os
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine


default_file = Path(__file__).resolve().parents[1] / "progressgate.db"
database_url = os.environ.get("PROGRESSGATE_DATABASE_URL", f"sqlite:///{default_file}")
engine = create_engine(database_url, connect_args={"check_same_thread": False})


def create_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
