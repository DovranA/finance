import pytest
from app.domain.value_objects.money import Money
from app.domain.value_objects.enums import Currency

def test_money_creation():
    m = Money(100, Currency.USD)
    assert m.amount == 100
    assert m.currency == Currency.USD

def test_money_addition():
    m1 = Money(100, Currency.USD)
    m2 = Money(50, Currency.USD)
    res = m1 + m2
    assert res.amount == 150
    assert res.currency == Currency.USD

def test_money_addition_different_currency():
    m1 = Money(100, Currency.USD)
    m2 = Money(50, Currency.EUR)
    with pytest.raises(ValueError, match="different currencies"):
        _ = m1 + m2

def test_money_subtraction():
    m1 = Money(100, Currency.USD)
    m2 = Money(30, Currency.USD)
    res = m1 - m2
    assert res.amount == 70

def test_money_comparison():
    m1 = Money(100, Currency.USD)
    m2 = Money(50, Currency.USD)
    assert m1 > m2
    assert m2 < m1
    assert m1 != m2
    assert m1 == Money(100, Currency.USD)
