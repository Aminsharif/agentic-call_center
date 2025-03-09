from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.database import Call, Message
from app.core.logger import logger
from datetime import datetime, timedelta
from ..models.models import CallSimulation

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def get_call_statistics(db: Session) -> Dict[str, Any]:
        """Get general call statistics."""
        try:
            total_calls = db.query(Call).count()
            avg_duration = db.query(func.avg(Call.duration)).scalar() or 0
            total_messages = db.query(Message).count()
            
            return {
                "total_calls": total_calls,
                "average_duration": round(float(avg_duration), 2),
                "total_messages": total_messages
            }
        except Exception as e:
            logger.error(f"Error getting call statistics: {str(e)}")
            return {}
    
    @staticmethod
    def get_call_history(db: Session, call_id: int) -> Dict[str, Any]:
        """Get detailed history for a specific call."""
        try:
            call = db.query(Call).filter(Call.id == call_id).first()
            if not call:
                return {}
            
            messages = db.query(Message).filter(Message.call_id == call_id).all()
            
            return {
                "call_details": {
                    "from": call.from_number,
                    "to": call.to_number,
                    "duration": call.duration,
                    "status": call.status,
                    "created_at": call.created_at.isoformat()
                },
                "messages": [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.created_at.isoformat()
                    }
                    for msg in messages
                ]
            }
        except Exception as e:
            logger.error(f"Error getting call history: {str(e)}")
            return {}
    
    @staticmethod
    def analyze_conversation(messages: List[Message]) -> Dict[str, Any]:
        """Analyze conversation patterns and metrics."""
        try:
            user_messages = [msg for msg in messages if msg.role == "user"]
            assistant_messages = [msg for msg in messages if msg.role == "assistant"]
            
            return {
                "message_count": {
                    "user": len(user_messages),
                    "assistant": len(assistant_messages)
                },
                "average_response_length": {
                    "user": sum(len(msg.content) for msg in user_messages) / len(user_messages) if user_messages else 0,
                    "assistant": sum(len(msg.content) for msg in assistant_messages) / len(assistant_messages) if assistant_messages else 0
                }
            }
        except Exception as e:
            logger.error(f"Error analyzing conversation: {str(e)}")
            return {}

    def get_call_metrics(self, simulation_id: str) -> Dict:
        """Get metrics for a specific call"""
        simulation = self.db.query(CallSimulation).filter(CallSimulation.id == simulation_id).first()
        if not simulation:
            return {}

        return {
            "duration": simulation.resolution_time,
            "sentiment_score": simulation.sentiment_score,
            "quality_metrics": simulation.quality_metrics
        }

    def get_daily_stats(self) -> Dict:
        """Get daily statistics"""
        today = datetime.utcnow().date()
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())

        calls = self.db.query(CallSimulation).filter(
            CallSimulation.start_time >= start_of_day,
            CallSimulation.start_time <= end_of_day
        ).all()

        total_calls = len(calls)
        completed_calls = sum(1 for call in calls if call.status == "completed")
        avg_duration = sum(call.resolution_time or 0 for call in calls) / total_calls if total_calls > 0 else 0
        avg_sentiment = sum(call.sentiment_score or 0 for call in calls) / total_calls if total_calls > 0 else 0

        return {
            "total_calls": total_calls,
            "completed_calls": completed_calls,
            "avg_duration": round(avg_duration, 2),
            "avg_sentiment": round(avg_sentiment, 2)
        }

    def get_hourly_distribution(self) -> List[Dict]:
        """Get hourly call distribution"""
        today = datetime.utcnow().date()
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())

        calls = self.db.query(CallSimulation).filter(
            CallSimulation.start_time >= start_of_day,
            CallSimulation.start_time <= end_of_day
        ).all()

        hourly_counts = [0] * 24
        for call in calls:
            hour = call.start_time.hour
            hourly_counts[hour] += 1

        return [
            {"hour": hour, "count": count}
            for hour, count in enumerate(hourly_counts)
        ]

    def get_quality_trends(self, days: int = 7) -> List[Dict]:
        """Get quality metrics trends"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        calls = self.db.query(CallSimulation).filter(
            CallSimulation.start_time >= start_date,
            CallSimulation.start_time <= end_date
        ).all()

        daily_metrics = {}
        for call in calls:
            day = call.start_time.date()
            if day not in daily_metrics:
                daily_metrics[day] = {
                    "latency": [],
                    "packet_loss": [],
                    "jitter": [],
                    "sentiment": []
                }

            metrics = call.quality_metrics or {}
            if metrics.get("network_latency"):
                daily_metrics[day]["latency"].append(metrics["network_latency"])
            if metrics.get("packet_loss"):
                daily_metrics[day]["packet_loss"].append(metrics["packet_loss"])
            if metrics.get("jitter"):
                daily_metrics[day]["jitter"].append(metrics["jitter"])
            if call.sentiment_score is not None:
                daily_metrics[day]["sentiment"].append(call.sentiment_score)

        return [
            {
                "date": day.isoformat(),
                "avg_latency": sum(metrics["latency"]) / len(metrics["latency"]) if metrics["latency"] else 0,
                "avg_packet_loss": sum(metrics["packet_loss"]) / len(metrics["packet_loss"]) if metrics["packet_loss"] else 0,
                "avg_jitter": sum(metrics["jitter"]) / len(metrics["jitter"]) if metrics["jitter"] else 0,
                "avg_sentiment": sum(metrics["sentiment"]) / len(metrics["sentiment"]) if metrics["sentiment"] else 0
            }
            for day, metrics in sorted(daily_metrics.items())
        ] 