from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProductIteration:
    product: str
    version: str
    changes: tuple[str, ...]
    status: str


class ProductIterationService:
    """Creates explicit product iteration plans without silently shipping changes."""

    def plan(self, product: str, version: str, changes: list[str]) -> ProductIteration:
        if not product.strip() or not version.strip():
            raise ValueError("product and version must not be empty")
        return ProductIteration(product, version, tuple(changes), "planned")
