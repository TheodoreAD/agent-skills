"""pip install sqlalchemy alembic

Real multi-table joins + migrations. Alembic is a CLI scaffold, not importable inline:

    alembic init migrations
    alembic revision --autogenerate -m "..."
    alembic upgrade head

driven by migrations/env.py pointed at this file's Base.metadata.

The column vocabulary below is defined once -- type_annotation_map for the
plain types, Annotated aliases for the ones needing per-column arguments -- and
it exists because SQLAlchemy's own defaults are wrong for Decimal and datetime
on the SQLite tier. See the SKILL.md entry; each TypeDecorator says which trap
it closes.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from sqlalchemy import String, Text, TypeDecorator, create_engine, select
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, registry


class ExactNumeric(TypeDecorator[Decimal]):
    """Decimal stored as exact text.

    Numeric round-trips a Decimal through a float on SQLite, silently:
    1234567890123456789.000000001 comes back 1234567890123456768.0000000000.
    supports_native_decimal is False in engine/default.py and the SQLite
    dialect does not override it.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Decimal | None, dialect: Dialect) -> str | None:
        return None if value is None else str(value)

    def process_result_value(self, value: str | None, dialect: Dialect) -> Decimal | None:
        return None if value is None else Decimal(value)


class UtcDateTime(TypeDecorator[datetime]):
    """Aware datetime stored as ISO-8601 UTC; naive input refused.

    dialects/sqlite/base.py's DATETIME.bind_processor never reads tzinfo at
    all, so an aware datetime comes back naive. That is the dialect's code,
    not a SQLite limitation.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime rejected at the column boundary")
        return value.astimezone(UTC).isoformat()

    def process_result_value(self, value: str | None, dialect: Dialect) -> datetime | None:
        return None if value is None else datetime.fromisoformat(value)


# STRICT tables accept only INT/INTEGER/REAL/TEXT/BLOB/ANY, so VARCHAR(64) is
# rejected outright -- with_variant keeps the real length bound on Postgres and
# falls back to TEXT on SQLite, where the bound was never enforced anyway.
Name = Annotated[str, mapped_column(String(64).with_variant(Text(), "sqlite"))]


class Base(DeclarativeBase):
    # Define the vocabulary once; every Mapped[Decimal]/Mapped[datetime] in
    # every model picks these up, so no column can opt out by being written
    # from memory somewhere else.
    registry = registry(type_annotation_map={Decimal: ExactNumeric, datetime: UtcDateTime})


class Reading(Base):
    __tablename__ = "readings"
    # sqlite_strict is not a free extra keyword: it enforces the type
    # vocabulary above. Adopting it and fixing the Decimal/datetime traps are
    # the same piece of work, which is the argument for doing both.
    __table_args__ = ({"sqlite_strict": True},)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[Name]
    amount: Mapped[Decimal]
    at: Mapped[datetime]


def test_insert_and_query() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Reading(name="widget", amount=Decimal("2.5"), at=datetime.now(UTC)))
        session.commit()
        # select()/scalar_one() is the current SQLAlchemy 2.0 style — prefer it over the legacy
        # session.query(...) API in new code.
        reading = session.execute(select(Reading).filter_by(name="widget")).scalar_one()
        assert reading.name == "widget"


def test_decimal_survives_and_datetime_stays_aware() -> None:
    # Wide enough to fail through a float. A ten-digit probe passes even with
    # the bug, which is how the bug ships.
    wide = Decimal("1234567890123456789.000000001")
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Reading(name="probe", amount=wide, at=datetime(2026, 3, 29, 1, 30, tzinfo=UTC)))
        session.commit()
    with Session(engine) as session:
        reading = session.execute(select(Reading)).scalar_one()
        assert reading.amount == wide
        assert reading.at.tzinfo is not None
