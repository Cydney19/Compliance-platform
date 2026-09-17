import enum
from datetime import date, timedelta
from sqlalchemy import String, Integer, Date, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db import Base


class Category(str, enum.Enum):
    fire = "Fire"
    electrical = "Electrical"
    water = "Water/Legionella"
    gas = "Gas"
    asbestos = "Asbestos"
    lifts = "Lifts"
    other = "Other"


class School(Base):
    __tablename__ = "schools"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)

    checks: Mapped[list["Check"]] = relationship(back_populates="school")


class Check(Base):
    __tablename__ = "checks"
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"))
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[Category] = mapped_column(Enum(Category), default=Category.other)
    frequency_days: Mapped[int] = mapped_column(Integer)
    last_completed: Mapped[date] = mapped_column(Date)

    school: Mapped["School"] = relationship(back_populates="checks")

    @property
    def next_due(self) -> date:
        return self.last_completed + timedelta(days=self.frequency_days)

    @property
    def rag(self) -> str:
        today = date.today()
        if self.next_due < today:
            return "Red"
        if self.next_due <= today + timedelta(days=30):
            return "Amber"
        return "Green"
