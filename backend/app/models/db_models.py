import datetime
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.app.database import Base


class BillModel(Base):
    __tablename__ = "bills"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Unguessable UUID4 token for secure read-only sharing
    share_token = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    status = Column(String(32), default="extracted")  # "extracted", "confirmed", "calculated"
    
    raw_extraction = Column(Text, nullable=True)     # JSON of ExtractedBill with confidences
    confirmed_bill = Column(Text, nullable=True)     # JSON of ConfirmedBill with stable IDs
    provenance = Column(Text, nullable=True)         # JSON detailing provider, attempts, timestamps
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    people = relationship("PersonModel", back_populates="bill", cascade="all, delete-orphan")
    assignments = relationship("AssignmentModel", back_populates="bill", cascade="all, delete-orphan")
    calculation = relationship("CalculationResultModel", back_populates="bill", uselist=False, cascade="all, delete-orphan")


class PersonModel(Base):
    __tablename__ = "people"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    bill_id = Column(String(36), ForeignKey("bills.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    email = Column(String(128), nullable=True)
    phone = Column(String(32), nullable=True)

    bill = relationship("BillModel", back_populates="people")


class AssignmentModel(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bill_id = Column(String(36), ForeignKey("bills.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(String(64), nullable=False, index=True)  # Stable ID of confirmed item
    person_id = Column(String(36), nullable=False, index=True)

    bill = relationship("BillModel", back_populates="assignments")


class CalculationResultModel(Base):
    __tablename__ = "calculation_results"

    bill_id = Column(String(36), ForeignKey("bills.id", ondelete="CASCADE"), primary_key=True)
    result_data = Column(Text, nullable=False)  # JSON serialized SplitResult
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    bill = relationship("BillModel", back_populates="calculation")
