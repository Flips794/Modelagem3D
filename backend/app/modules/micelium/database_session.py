from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.orm import Session, sessionmaker


class MiceliumDatabaseUnavailable(RuntimeError):
    pass


def _session_from_app_db_session() -> Generator[Session, None, None] | None:
    try:
        from app.db.session import get_db
    except Exception:
        return None

    return get_db()


def _session_from_core_database() -> Session | None:
    try:
        from app.core.database import SessionLocal
    except Exception:
        SessionLocal = None

    if SessionLocal is not None:
        return SessionLocal()

    try:
        from app.core.database import engine
    except Exception:
        return None

    LocalSession = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    return LocalSession()


@contextmanager
def open_micelium_db_session() -> Generator[Session, None, None]:
    generator = _session_from_app_db_session()

    if generator is not None:
        try:
            db = next(generator)
        except StopIteration as exc:
            raise MiceliumDatabaseUnavailable(
                "app.db.session.get_db não retornou uma sessão válida."
            ) from exc

        try:
            yield db
        finally:
            try:
                next(generator)
            except StopIteration:
                pass
            except Exception:
                pass

        return

    db = _session_from_core_database()

    if db is None:
        raise MiceliumDatabaseUnavailable(
            "Nenhuma sessão de banco disponível. Crie app.db.session.get_db, "
            "ou exponha SessionLocal/engine em app.core.database."
        )

    try:
        yield db
    finally:
        db.close()


