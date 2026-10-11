from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Sku(Base):
    __tablename__ = "skus"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    our_sku: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(80))
    our_price: Mapped[float] = mapped_column(Float)
    competitor: Mapped[str] = mapped_column(String(80))
    competitor_sku: Mapped[str] = mapped_column(String(64))
    source_url: Mapped[str] = mapped_column(String(400))
    price_selector: Mapped[str] = mapped_column(String(200))
    units_7d: Mapped[int] = mapped_column(Integer, default=0)

    snapshots: Mapped[list["Snapshot"]] = relationship(back_populates="sku", cascade="all, delete-orphan")


class Snapshot(Base):
    __tablename__ = "price_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id"))
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    price: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(40), default="seed")

    sku: Mapped[Sku] = relationship(back_populates="snapshots")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    old_price: Mapped[float] = mapped_column(Float)
    new_price: Mapped[float] = mapped_column(Float)
    drop_pct: Mapped[float] = mapped_column(Float)
    channel: Mapped[str] = mapped_column(String(40))
    body: Mapped[str] = mapped_column(Text)
