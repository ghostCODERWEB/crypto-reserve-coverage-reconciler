"""Reconcile asset-level reserves and customer liabilities with encumbrance exclusions and valuation scenarios."""

from .common import (
    number,
    integer,
    identity,
    records,
    chronology,
    allocate,
    result,
    validate_document,
)
from decimal import Decimal


def _analyze(d):
    prices = {identity(k): number(v) for k, v in d["prices"].items()}
    reserves = records(d["reserves"], "id")
    liabilities = records(d["liabilities"], "id")
    assets = {k: 0 for k in prices}
    debts = {k: 0 for k in prices}
    excluded = {k: 0 for k in prices}
    for r in reserves:
        asset = identity(r["asset"])
        amount = integer(r["amount"])
        encumbered = integer(r["encumbered"])
        if asset not in prices or encumbered > amount:
            raise ValueError("invalid reserve asset or encumbrance")
        assets[asset] += amount - encumbered
        excluded[asset] += encumbered
    for r in liabilities:
        asset = identity(r["asset"])
        if asset not in prices:
            raise ValueError("unknown liability asset")
        debts[asset] += integer(r["amount"])
    rows = [
        {
            "asset": a,
            "available": assets[a],
            "liabilities": debts[a],
            "surplus": assets[a] - debts[a],
            "coverage": number(assets[a]) / debts[a] if debts[a] else None,
            "excluded": excluded[a],
        }
        for a in sorted(prices)
    ]
    reserve_value = sum((prices[a] * assets[a] for a in prices), number(0))
    liability_value = sum((prices[a] * debts[a] for a in prices), number(0))
    return result(
        {
            "assets": rows,
            "reserve_value": reserve_value,
            "liability_value": liability_value,
            "value_surplus": reserve_value - liability_value,
            "every_asset_covered": all(assets[a] >= debts[a] for a in prices),
        }
    )


def analyze(document):
    validate_document(document)
    try:
        return result(_analyze(document))
    except (KeyError, TypeError, ArithmeticError, RecursionError) as error:
        raise ValueError("invalid domain input: " + str(error)) from error
