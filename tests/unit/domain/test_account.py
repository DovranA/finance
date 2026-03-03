import pytest
import uuid
from app.domain.entities.account import Account
from app.domain.value_objects.enums import Currency
from app.domain.exceptions import AccountInactive


def test_account_creation():
    user_id = uuid.uuid4()
    acc = Account.create(user_id=user_id, currency=Currency.USD)
    assert acc.user_id == user_id
    assert acc.balance == 0
    assert acc.is_active is True


def test_account_default_currency():
    acc = Account.create(uuid.uuid4())
    assert acc.currency == "TMT"


def test_account_credit():
    acc = Account.create(uuid.uuid4())
    acc.credit(100)
    assert acc.balance == 100

    acc.credit(50)
    assert acc.balance == 150


def test_account_debit_success():
    acc = Account.create(uuid.uuid4())
    acc.credit(100)
    acc.debit(30)
    assert acc.balance == 70


def test_account_debit_insufficient_funds():
    acc = Account.create(uuid.uuid4())
    acc.credit(50)
    with pytest.raises(ValueError, match="Insufficient balance"):
        acc.debit(100)


def test_account_negative_credit():
    acc = Account.create(uuid.uuid4())
    with pytest.raises(ValueError, match="Credit amount must be positive"):
        acc.credit(-10)


def test_account_negative_debit():
    acc = Account.create(uuid.uuid4())
    with pytest.raises(ValueError, match="Debit amount must be positive"):
        acc.debit(-10)


def test_account_ensure_active_ok():
    acc = Account.create(uuid.uuid4())
    acc.ensure_active()  # should not raise


def test_account_ensure_active_raises():
    acc = Account.create(uuid.uuid4())
    acc.is_active = False
    with pytest.raises(AccountInactive):
        acc.ensure_active()
