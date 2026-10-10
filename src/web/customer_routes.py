"""Customer workspace UI and ownership-checked product previews."""
from pathlib import Path
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from src.company.control_center.routes import get_control_center
from src.company.control_center.service import CompanyControlCenter
from src.security.customer_authorization import require_customer_workspace

router = APIRouter(tags=["customer-web"])
STATIC_DIR = Path(__file__).resolve().parent / "static"
PRODUCTS_DIR = Path(__file__).resolve().parents[2] / "generated-products"
LEGACY_PRODUCTS_DIR = Path(__import__("tempfile").gettempdir()) / "ai-software-company-workspaces"


@router.get("/customer", include_in_schema=False)
async def customer_app() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "customer-app.html",
        media_type="text/html",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


def _entrypoint(root: Path) -> tuple[Path, Path] | None:
    resolved = root.resolve()
    for relative in ("index.html", "frontend/index.html", "public/index.html", "dist/index.html", "build/index.html"):
        candidate = (resolved / relative).resolve()
        try:
            candidate.relative_to(resolved)
        except ValueError:
            continue
        if candidate.is_file():
            return candidate, candidate.parent
    return None


async def _owned_product_root(mission_id: str, context: tuple, center: CompanyControlCenter) -> tuple[Path, Path]:
    _, workspace = context
    if not mission_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in mission_id):
        raise HTTPException(status_code=404, detail="Product not found")
    job = center.mission_job(mission_id)
    if job is None or job.workspace_id != workspace.id or job.status.value != "completed":
        raise HTTPException(status_code=404, detail="Product not found")
    for candidate, base in (
        ((PRODUCTS_DIR / mission_id).resolve(), PRODUCTS_DIR.resolve()),
        ((LEGACY_PRODUCTS_DIR / mission_id).resolve(), LEGACY_PRODUCTS_DIR.resolve()),
    ):
        try:
            candidate.relative_to(base)
        except ValueError:
            continue
        if candidate.is_dir():
            found = _entrypoint(candidate)
            if found:
                return candidate, found[0]
    raise HTTPException(status_code=404, detail="Completed browser preview not found")


@router.get("/customer/products/{mission_id}", include_in_schema=False)
async def customer_product(
    mission_id: str,
    context=Depends(require_customer_workspace),
    center: CompanyControlCenter = Depends(get_control_center),
) -> HTMLResponse:
    root, index = await _owned_product_root(mission_id, context, center)
    html = index.read_text(encoding="utf-8")
    asset_root = index.parent.relative_to(root).as_posix()
    base_path = f"/customer/products/{mission_id}/"
    if asset_root != ".":
        base_path += asset_root.rstrip("/") + "/"
    base_tag = f'<base href="{base_path}">'
    pattern = r"(<head(?:\s[^>]*)?>)"
    if re.search(pattern, html, flags=re.IGNORECASE):
        html = re.sub(pattern, lambda match: match.group(1) + base_tag, html, count=1, flags=re.IGNORECASE)
    else:
        html = base_tag + html
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


@router.get("/customer/products/{mission_id}/{file_path:path}", include_in_schema=False)
async def customer_product_asset(
    mission_id: str,
    file_path: str,
    context=Depends(require_customer_workspace),
    center: CompanyControlCenter = Depends(get_control_center),
) -> FileResponse:
    root, _ = await _owned_product_root(mission_id, context, center)
    target = (root / file_path).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Product file not found") from exc
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Product file not found")
    return FileResponse(target, headers={"Cache-Control": "no-store"})
