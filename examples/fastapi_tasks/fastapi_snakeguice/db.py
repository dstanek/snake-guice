"""Database access, bound separately for the reader and writer modules.

`Database` is constructed eagerly (outside the injector) and bound with
`to_instance=` rather than `in_scope=scopes.SINGLETON` — `SINGLETON`'s cache
is process-global and keyed only by `(interface, annotation)`, so binding the
unannotated `IDatabase` to `SINGLETON` in both `ReaderDatabaseModule` and
`WriterDatabaseModule` would collide and one would silently get the other's
`Database`.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


class IDatabase:
    def get_session(self) -> Session:
        raise NotImplementedError


class Database(IDatabase):
    def __init__(self, db_path: str) -> None:
        engine = create_engine(
            f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
        )
        self._session_factory: sessionmaker[Session] = sessionmaker(bind=engine)

    def get_session(self) -> Session:
        return self._session_factory()
