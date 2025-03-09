from sqlalchemy import Column, Integer, String, DateTime, JSON, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class CallSimulation(Base):
    __tablename__ = "call_simulations"

    id = Column(String(36), primary_key=True)
    status = Column(String(20), default="in-progress")
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    transferred_to = Column(String(100), nullable=True)
    transfer_reason = Column(String(500), nullable=True)
    notes = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    quality_metrics = Column(JSON, default=dict)
    sentiment_score = Column(Float, default=0.0)
    resolution_time = Column(Integer, default=0)

    messages = relationship("Message", back_populates="simulation")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(String(36), ForeignKey("call_simulations.id"))
    content = Column(String(1000))
    sender = Column(String(20))  # "user" or "agent"
    timestamp = Column(DateTime, default=datetime.utcnow)

    simulation = relationship("CallSimulation", back_populates="messages") 