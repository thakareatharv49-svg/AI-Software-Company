from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProductPortfolio:
    products: tuple[str, ...]
    active_product: str | None


class ProductPortfolioService:
    def build(self, products: list[str], active_product: str | None = None) -> ProductPortfolio:
        unique = tuple(dict.fromkeys(product for product in products if product.strip()))
        if active_product is not None and active_product not in unique:
            raise ValueError("active_product must belong to products")
        return ProductPortfolio(unique, active_product)
