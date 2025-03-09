from typing import Dict, Optional, List
from datetime import datetime
from app.services.llm_service import LLMService
from app.core.logger import logger
import uuid
import random
from ..models.models import CallSimulation, Message
from ..database import SessionLocal
from sqlalchemy.orm import Session

class SimulationService:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.db = SessionLocal()

    def __del__(self):
        self.db.close()

    def start_simulation(self) -> str:
        """Start a new call simulation"""
        simulation_id = str(uuid.uuid4())
        simulation = CallSimulation(
            id=simulation_id,
            status="in-progress",
            start_time=datetime.utcnow(),
            quality_metrics={
                "network_latency": 50,  # ms
                "packet_loss": 0.01,    # 1%
                "jitter": 5,            # ms
                "sentiment_score": 0.0
            }
        )
        
        try:
            self.db.add(simulation)
            self.db.commit()
            return simulation_id
        except Exception as e:
            logger.error(f"Error starting simulation: {str(e)}")
            self.db.rollback()
            return None

    def end_simulation(self, simulation_id: str) -> bool:
        """End an active call simulation"""
        simulation = self.db.query(CallSimulation).filter(CallSimulation.id == simulation_id).first()
        if not simulation or simulation.status != "in-progress":
            return False
        
        try:
            simulation.status = "completed"
            simulation.end_time = datetime.utcnow()
            simulation.resolution_time = int((simulation.end_time - simulation.start_time).total_seconds())
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error ending simulation: {str(e)}")
            self.db.rollback()
            return False

    def process_message(self, simulation_id: str, message: str) -> Optional[str]:
        """Process a message in the simulation"""
        simulation = self.db.query(CallSimulation).filter(CallSimulation.id == simulation_id).first()
        if not simulation or simulation.status != "in-progress":
            logger.warning(f"Attempted to process message for invalid simulation ID: {simulation_id}")
            return None
        
        try:
            # Log incoming message
            logger.info(f"Processing message for simulation {simulation_id}: {message[:100]}...")
            
            # Add user message to database
            user_message = Message(
                simulation_id=simulation_id,
                content=message,
                sender="user",
                timestamp=datetime.utcnow()
            )
            self.db.add(user_message)
            
            # Get AI response
            try:
                response = self.llm_service.get_response(message)
                logger.info(f"Received LLM response for simulation {simulation_id}")
            except Exception as llm_error:
                logger.error(f"LLM service error for simulation {simulation_id}: {str(llm_error)}")
                return "I apologize, but I'm experiencing technical difficulties. Please try again in a moment."
            
            # Add AI response to database
            agent_message = Message(
                simulation_id=simulation_id,
                content=response,
                sender="agent",
                timestamp=datetime.utcnow()
            )
            self.db.add(agent_message)
            
            # Update sentiment score
            simulation.quality_metrics["sentiment_score"] = self._analyze_sentiment(message)
            
            self.db.commit()
            return response
        except Exception as e:
            logger.error(f"Error processing message for simulation {simulation_id}: {str(e)}")
            self.db.rollback()
            return "I apologize, but I'm having trouble processing your message. Could you please try again?"

    def get_simulation_details(self, simulation_id: str) -> Optional[Dict]:
        """Get details about a specific simulation"""
        simulation = self.db.query(CallSimulation).filter(CallSimulation.id == simulation_id).first()
        if not simulation:
            return None
        
        messages = self.db.query(Message).filter(Message.simulation_id == simulation_id).all()
        
        return {
            "id": simulation.id,
            "status": simulation.status,
            "start_time": simulation.start_time.isoformat(),
            "end_time": simulation.end_time.isoformat() if simulation.end_time else None,
            "resolution_time": simulation.resolution_time,
            "quality_metrics": simulation.quality_metrics,
            "messages": [
                {
                    "content": msg.content,
                    "sender": msg.sender,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in messages
            ],
            "notes": simulation.notes,
            "tags": simulation.tags,
            "sentiment_score": simulation.quality_metrics.get("sentiment_score", 0.0)
        }

    def get_all_simulations(self) -> List[Dict]:
        """Get all simulations"""
        simulations = self.db.query(CallSimulation).all()
        return [
            {
                "id": sim.id,
                "status": sim.status,
                "start_time": sim.start_time.isoformat(),
                "end_time": sim.end_time.isoformat() if sim.end_time else None,
                "resolution_time": sim.resolution_time,
                "sentiment_score": sim.quality_metrics.get("sentiment_score", 0.0)
            }
            for sim in simulations
        ]

    def transfer_call(self, simulation_id: str, agent: str, reason: str) -> bool:
        """Transfer a call to another agent"""
        simulation = self.db.query(CallSimulation).filter(CallSimulation.id == simulation_id).first()
        if not simulation or simulation.status != "in-progress":
            return False
        
        try:
            simulation.transferred_to = agent
            simulation.transfer_reason = reason
            simulation.status = "transferred"
            simulation.end_time = datetime.utcnow()
            simulation.resolution_time = int((simulation.end_time - simulation.start_time).total_seconds())
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error transferring call: {str(e)}")
            self.db.rollback()
            return False

    def add_note(self, simulation_id: str, note: str) -> bool:
        """Add a note to the call"""
        simulation = self.db.query(CallSimulation).filter(CallSimulation.id == simulation_id).first()
        if not simulation:
            return False
        
        try:
            if not simulation.notes:
                simulation.notes = []
            simulation.notes.append({
                "content": note,
                "timestamp": datetime.utcnow().isoformat()
            })
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding note: {str(e)}")
            self.db.rollback()
            return False

    def add_tag(self, simulation_id: str, tag: str) -> bool:
        """Add a tag to the call"""
        simulation = self.db.query(CallSimulation).filter(CallSimulation.id == simulation_id).first()
        if not simulation:
            return False
        
        try:
            if not simulation.tags:
                simulation.tags = []
            if tag not in simulation.tags:
                simulation.tags.append(tag)
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding tag: {str(e)}")
            self.db.rollback()
            return False

    def _analyze_sentiment(self, message: str) -> float:
        """Basic sentiment analysis"""
        positive_words = ["happy", "great", "excellent", "good", "thanks", "helpful"]
        negative_words = ["bad", "poor", "terrible", "unhappy", "frustrated", "angry"]
        
        words = message.lower().split()
        positive_count = sum(1 for w in words if w in positive_words)
        negative_count = sum(1 for w in words if w in negative_words)
        
        if positive_count + negative_count > 0:
            return (positive_count - negative_count) / (positive_count + negative_count)
        return 0.0 