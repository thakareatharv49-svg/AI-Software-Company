from __future__ import annotations

from sqlalchemy import JSON, String, create_engine
from sqlalchemy.orm import Mapped, Session, mapped_column

from src.company.review_workflow import ProductReview
from src.config.settings import settings
from src.db.base import Base


class ProductReviewRow(Base):
    __tablename__ = 'product_reviews'

    mission_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    review: Mapped[dict] = mapped_column(JSON, nullable=False)


class ProductReviewStore:
    """Persist review state independently from transient web-process memory."""

    def __init__(self) -> None:
        url = settings.database_url.replace('postgresql+asyncpg://', 'postgresql+psycopg://')
        self._engine = create_engine(url, pool_pre_ping=True)
        Base.metadata.create_all(self._engine, tables=[ProductReviewRow.__table__])

    def get(self, mission_id: str) -> ProductReview | None:
        with Session(self._engine) as session:
            row = session.get(ProductReviewRow, mission_id)
            if row is None:
                return None
            return ProductReview.model_validate(row.review)

    def save(self, review: ProductReview) -> None:
        with Session(self._engine) as session:
            row = session.get(ProductReviewRow, review.mission_id)
            payload = review.model_dump(mode='json')
            if row is None:
                session.add(ProductReviewRow(mission_id=review.mission_id, review=payload))
            else:
                row.review = payload
            session.commit()

    def close(self) -> None:
        self._engine.dispose()
