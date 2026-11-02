from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base, TimestampMixin


class RuleOverrideRow(TimestampMixin, Base):
    __tablename__ = "rule_overrides"

    namespace: Mapped[str] = mapped_column(String(64), primary_key=True)
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[float] = mapped_column(Float)
