"""Database access, bound separately for the reader and writer modules.

`Database` is constructed eagerly (outside the injector) and bound with
`to_instance=` rather than `in_scope=scopes.SINGLETON`, because its
constructor needs a `db_path` that comes from `ReaderDatabaseModule`'s /
`WriterDatabaseModule`'s own `__init__` argument, not from anything the
injector can supply — `to=`/`SINGLETON` only help when the injector can build
the object itself.
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
