from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.responses import Response, JSONResponse, HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os
import uuid
from dotenv import load_dotenv
import json

from app.services.llm_service import LLMService
from app.services.simulation_service import SimulationService
from app.services.analytics_service import AnalyticsService
from app.core.auth import get_current_user, create_access_token, User, Token
from app.core.logger import logger
from app.database import get_db, init_db
from app.models.models import CallSimulation, Message

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="AI Call Center")

# Initialize database
init_db()

# Mount static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Initialize services
llm_service = LLMService()
simulation_service = SimulationService(llm_service)

# Web interface routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the home page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/simulator", response_class=HTMLResponse)
async def simulator(request: Request):
    """Render the call simulator page"""
    return templates.TemplateResponse("call_simulator.html", {"request": request})

@app.get("/call-history", response_class=HTMLResponse)
async def call_history(request: Request, db: Session = Depends(get_db)):
    """Render the call history page"""
    simulations = db.query(CallSimulation).all()
    return templates.TemplateResponse(
        "call_history.html",
        {"request": request, "simulations": simulations}
    )

# Simulation API endpoints
@app.post("/api/simulate/start")
async def start_simulation():
    """Start a new call simulation"""
    simulation_id = simulation_service.start_simulation()
    if not simulation_id:
        raise HTTPException(status_code=500, detail="Failed to start simulation")
    logger.info(f"Started simulation {simulation_id}")
    return {"simulation_id": simulation_id}

@app.post("/api/simulate/end")
async def end_simulation(request: Request):
    """End an active call simulation"""
    data = await request.json()
    simulation_id = data.get("simulation_id")
    if not simulation_id:
        raise HTTPException(status_code=400, detail="Simulation ID is required")
    
    success = simulation_service.end_simulation(simulation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Simulation not found or already ended")
    
    logger.info(f"Ended simulation {simulation_id}")
    return {"status": "success"}

@app.post("/api/simulate/message")
async def process_message(request: Request):
    """Process a message in the simulation"""
    data = await request.json()
    simulation_id = data.get("simulation_id")
    message = data.get("message")
    
    if not simulation_id or not message:
        raise HTTPException(status_code=400, detail="Simulation ID and message are required")
    
    response = simulation_service.process_message(simulation_id, message)
    if response is None:
        raise HTTPException(status_code=404, detail="Simulation not found or inactive")
    
    return {"response": response}

@app.get("/api/simulate/{simulation_id}")
async def get_simulation(simulation_id: str):
    """Get details about a specific simulation"""
    details = simulation_service.get_simulation_details(simulation_id)
    if not details:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return details

@app.post("/api/simulate/{simulation_id}/transfer")
async def transfer_call(simulation_id: str, request: Request):
    """Transfer a call to another agent"""
    data = await request.json()
    agent = data.get("agent")
    reason = data.get("reason")
    
    if not agent or not reason:
        raise HTTPException(status_code=400, detail="Agent and reason are required")
    
    success = simulation_service.transfer_call(simulation_id, agent, reason)
    if not success:
        raise HTTPException(status_code=404, detail="Simulation not found or inactive")
    
    return {"status": "success"}

@app.post("/api/simulate/{simulation_id}/note")
async def add_note(simulation_id: str, request: Request):
    """Add a note to the call"""
    data = await request.json()
    note = data.get("note")
    
    if not note:
        raise HTTPException(status_code=400, detail="Note content is required")
    
    success = simulation_service.add_note(simulation_id, note)
    if not success:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    return {"status": "success"}

@app.post("/api/simulate/{simulation_id}/tag")
async def add_tag(simulation_id: str, request: Request):
    """Add a tag to the call"""
    data = await request.json()
    tag = data.get("tag")
    
    if not tag:
        raise HTTPException(status_code=400, detail="Tag is required")
    
    success = simulation_service.add_tag(simulation_id, tag)
    if not success:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    return {"status": "success"}

# Authentication endpoints
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username != os.getenv("API_USERNAME") or form_data.password != os.getenv("API_PASSWORD"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 