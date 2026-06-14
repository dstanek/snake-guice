"""Reader/writer SQLAlchemy engines and session factories."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


class Databases:
    def __init__(self, db_path: str) -> None:
        self.reader_engine = create_engine(
            f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
        )
        self.writer_engine = create_engine(
            f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
        )
        self.ReaderSession: sessionmaker[Session] = sessionmaker(
            bind=self.reader_engine
        )
        self.WriterSession: sessionmaker[Session] = sessionmaker(
            bind=self.writer_engine
        )
