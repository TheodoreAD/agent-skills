"""pip install pydantic

Data modeling defaults: frozen dataclass for internal records, Pydantic v2
for boundary/settings validation. NamedTuple only for the narrow escalation
cases documented in ../rationale.md §1.

The second half of this file is for a project taking the all-or-nothing
alternative (Pydantic for everything): the three traps a dataclass never had,
each with the spelling that closes it.
"""

from dataclasses import FrozenInstanceError, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, NamedTuple, TypeVar
from zoneinfo import ZoneInfo

import pytest
from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Strict,
    ValidationError,
)


@dataclass(frozen=True)
class OrderLine:
    """Internal record — no external validation needed."""

    sku: str
    quantity: int


class ApiOrderRequest(BaseModel):
    """Boundary data — parsing untrusted external input."""

    model_config = ConfigDict(frozen=True)

    sku: str
    quantity: int


class Point(NamedTuple):
    """Small, closed, order-is-the-meaning — the NamedTuple escalation case."""

    x: float
    y: float


def test_dataclass_is_frozen() -> None:
    line = OrderLine(sku="widget", quantity=2)
    with pytest.raises(FrozenInstanceError):
        line.quantity = 3  # type: ignore[misc]


def test_pydantic_model_validates_and_freezes() -> None:
    request = ApiOrderRequest.model_validate({"sku": "widget", "quantity": 2})
    assert request.quantity == 2
    with pytest.raises(ValidationError):
        request.quantity = 3


def test_namedtuple_unpacks_positionally() -> None:
    point = Point(1.0, 2.0)
    x, y = point
    assert (x, y) == (1.0, 2.0)


# --- The all-or-nothing alternative: Pydantic everywhere ---------------------

# The aware-UTC rule from the dates section, as one reusable annotation. It
# rejects a naive datetime and normalises an aware non-UTC one, on every
# construction path the model has.
Utc = Annotated[datetime, AwareDatetime, AfterValidator(lambda v: v.astimezone(UTC))]

# Strict() because lax mode coerces float into Decimal, silently removing the
# guarantee the Decimal was chosen for.
Exact = Annotated[Decimal, Strict()]

M = TypeVar("M", bound=BaseModel)


# Config on the line that names the class, not as an attribute assignment that
# looks like data. Verified equivalent to model_config = ConfigDict(frozen=True),
# and it composes with other keywords.
class Reading(BaseModel, frozen=True):
    """Internal record under the all-or-nothing rule — no longer a dataclass."""

    at: Utc
    amount: Exact


def replace(model: M, /, **updates: object) -> M:
    """Revalidating stand-in for dataclasses.replace.

    model_copy(update=...) performs NO validation -- its own docstring says so
    -- so it accepts values every other construction path rejects. Rebuilding
    through model_validate is what restores the guarantee.
    """
    return type(model).model_validate({**dict(model), **updates})


def test_utc_annotation_normalises_and_rejects() -> None:
    reading = Reading(at=datetime(2026, 3, 29, 1, 30, tzinfo=ZoneInfo("Europe/Bucharest")), amount=Decimal("2.5"))
    assert reading.at.tzinfo is UTC
    with pytest.raises(ValidationError):
        Reading(at=datetime(2026, 3, 29, 1, 30), amount=Decimal("2.5"))  # noqa: DTZ001


def test_strict_decimal_refuses_a_float() -> None:
    with pytest.raises(ValidationError):
        Reading(at=datetime.now(UTC), amount=2.5)  # pyright: ignore[reportArgumentType]


def test_model_copy_update_skips_validation_and_replace_does_not() -> None:
    reading = Reading(at=datetime.now(UTC), amount=Decimal("2.5"))

    # The trap: a naive datetime lands in a frozen, validated model.
    smuggled = reading.model_copy(update={"at": datetime(2026, 3, 29, 1, 30)})  # noqa: DTZ001
    assert smuggled.at.tzinfo is None

    with pytest.raises(ValidationError):
        replace(reading, at=datetime(2026, 3, 29, 1, 30))  # noqa: DTZ001
