from __future__ import annotations

import importlib
import pkgutil
from typing import Any


def __getattr__(name: str) -> Any:
    for module_info in pkgutil.iter_modules(__path__):
        module_name = module_info.name

        if module_name.startswith("_"):
            continue

        module = importlib.import_module(f"{__name__}.{module_name}")

        if hasattr(module, name):
            value = getattr(module, name)
            globals()[name] = value
            return value

    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}"
    )


def __dir__() -> list[str]:
    names = set(globals())

    for module_info in pkgutil.iter_modules(__path__):
        if module_info.name.startswith("_"):
            continue

        try:
            module = importlib.import_module(
                f"{__name__}.{module_info.name}"
            )
        except Exception:
            continue

        names.update(
            name
            for name in vars(module)
            if not name.startswith("_")
        )

    return sorted(names)
