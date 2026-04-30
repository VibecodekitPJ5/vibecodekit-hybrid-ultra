#!/usr/bin/env python3
"""Example: generate Vietnamese fake data (1 user profile + 1 shop catalog).

Run from the repo root:
    PYTHONPATH=./scripts python examples/04_vn_faker.py

Demonstrates ``vibecodekit.vn_faker.VnFaker``: realistic VN names,
phone prefixes (post-2018 migration), CCCD format, bank account
prefixes per issuer, and VND-formatted amounts (``1.500.000đ``).

Deterministic output (``seed=42``) so this script is snapshot-friendly.
"""
from __future__ import annotations

from vibecodekit.vn_faker import VnFaker


def user_profile(faker: VnFaker) -> dict:
    """Build 1 realistic VN user profile."""
    name = faker.name(gender="female")
    return {
        "name": name,
        "phone": faker.phone(),
        "phone_intl": faker.phone(international=True),
        "cccd": faker.cccd(),
        "email": faker.email(name),
        "address": faker.address(),
        "bank_account": faker.bank_account(),
    }


def shop_catalog(faker: VnFaker, n: int = 3) -> list:
    """Build a tiny shop catalog with VND-formatted prices."""
    items = ["Áo thun cotton", "Quần jean nam", "Giày sneaker"]
    return [
        {
            "sku": f"SKU-{i+1:03d}",
            "name": items[i],
            "price": faker.vnd_amount(min_amount=150_000, max_amount=2_000_000),
            "seller": faker.company(),
        }
        for i in range(min(n, len(items)))
    ]


if __name__ == "__main__":
    faker = VnFaker(seed=42)

    print("=== USER PROFILE (1) ===")
    profile = user_profile(faker)
    for k, v in profile.items():
        print(f"  {k:<14s} {v}")

    print("\n=== SHOP CATALOG (3 SKU) ===")
    for item in shop_catalog(faker):
        print(f"  {item['sku']}  {item['name']:<24s} {item['price']:>14s}  ({item['seller']})")

    print("\nOK")
