"""
MediSync - FastAPI Alternative for Testing
This is a FastAPI version for local testing when FastHTML is not available.
"""
import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.core.telemetry import setup_telemetry
from app.core.graph_db import get_graph_manager
from app.agents.medical_coder import medical_coder, set_patient_context, get_patient_context
from app.agents.query_agent import query_agent
from app.components.visualizer import graph_summary_card, conditions_list, medications_list
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


# Initialize telemetry
trace_url = setup_telemetry()

# Initialize graph manager
graph_manager = get_graph_manager()

# Initialize FastAPI app
app = FastAPI(title="MediSync - GraphRAG Patient Intelligence Platform")

# Templates (we'll create a simple HTML template)
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Main page."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MediSync 🏥 - GraphRAG Patient Intelligence Platform</title>
        <script src="https://unpkg.com/htmx.org@1.9.10"></script>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="min-h-screen bg-gray-50">
        <div class="bg-blue-600 text-white p-4 shadow-md">
            <h1 class="text-2xl font-bold">MediSync 🏥</h1>
            <p class="text-blue-100">GraphRAG Patient Intelligence Platform</p>
        </div>
        <div class="container mx-auto px-4 py-8 max-w-6xl">
            <div class="bg-white rounded-lg shadow-md p-6 mb-6">
                <h2 class="text-xl font-semibold mb-4">Patient Context</h2>
                <form hx-post="/set_patient" hx-target="#patient-info" hx-swap="innerHTML">
                    <div class="flex gap-2">
                        <input type="text" name="patient_id" placeholder="Enter Patient ID (e.g., PAT001)" 
                               class="flex-1 px-4 py-2 border rounded-lg" required>
                        <button type="submit" class="px-6 py-2 bg-blue-600 text-white rounded-lg">Set Patient</button>
                    </div>
                </form>
                <div id="patient-info" class="mt-4"></div>
            </div>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div class="bg-white rounded-lg shadow-md p-6">
                    <h2 class="text-xl font-semibold mb-4">Clinical Note Ingestion</h2>
                    <form hx-post="/process" hx-target="#graph-update" hx-swap="innerHTML">
                        <textarea name="clinical_note" rows="8" 
                                  placeholder="Enter patient clinical notes..." 
                                  class="w-full px-4 py-2 border rounded-lg mb-4" required></textarea>
                        <button type="submit" class="w-full px-6 py-2 bg-green-600 text-white rounded-lg">Process Note</button>
                    </form>
                    <div id="graph-update" class="mt-4"></div>
                </div>
                <div class="bg-white rounded-lg shadow-md p-6">
                    <h2 class="text-xl font-semibold mb-4">Patient History Query</h2>
                    <form hx-post="/query" hx-target="#query-results" hx-swap="innerHTML">
                        <textarea name="query" rows="4" 
                                  placeholder="Ask about patient history..." 
                                  class="w-full px-4 py-2 border rounded-lg mb-4" required></textarea>
                        <button type="submit" class="w-full px-6 py-2 bg-purple-600 text-white rounded-lg">Query History</button>
                    </form>
                    <div id="query-results" class="mt-4"></div>
                </div>
            </div>
            <div class="mt-6 text-center">
                <p class="text-sm text-gray-600 mb-2">Audit Trail</p>
                <a href="{}" target="_blank" class="text-blue-600 hover:underline">View Phoenix Traces</a>
            </div>
        </div>
    </body>
    </html>
    """.format(trace_url or "#")
    return HTMLResponse(content=html_content)


@app.post("/set_patient")
async def set_patient(patient_id: str = Form(...)):
    """Set the current patient context."""
    set_patient_context(patient_id)
    
    summary = graph_manager.get_patient_graph_summary(patient_id)
    conditions = graph_manager.get_patient_conditions(patient_id)
    medications = graph_manager.get_patient_medications(patient_id)
    
    # Create HTML response
    html = f"""
    <div class="bg-green-50 border border-green-200 rounded-lg p-4">
        <p class="font-semibold text-green-800 mb-2">✅ Patient context set to: {patient_id}</p>
    </div>
    """
    return HTMLResponse(content=html)


@app.post("/process")
async def process_note(clinical_note: str = Form(...)):
    """Process clinical note using medical coder agent."""
    patient_id = get_patient_context()
    
    if not patient_id:
        return HTMLResponse(content='<div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4"><p class="text-yellow-800">⚠️ Please set a patient context first.</p></div>')
    
    try:
        session_service = InMemorySessionService()
        app_name = medical_coder.name + "_app"
        user_id = medical_coder.name + "_user"
        session_id = medical_coder.name + "_session_" + patient_id
        
        await session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
        
        runner = Runner(
            agent=medical_coder,
            app_name=app_name,
            session_service=session_service
        )
        
        content = types.Content(role='user', parts=[types.Part(text=clinical_note)])
        
        final_response_text = None
        async for event in runner.run_async(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            content=content
        ):
            if event.is_final_response():
                final_response_text = event.text
        
        summary = graph_manager.get_patient_graph_summary(patient_id)
        
        html = f"""
        <div class="bg-green-50 border border-green-200 rounded-lg p-4">
            <p class="font-semibold text-green-800 mb-2">✅ Agent Processing Complete</p>
            <p class="text-green-700">{final_response_text or "Note processed successfully."}</p>
        </div>
        """
        return HTMLResponse(content=html)
    
    except Exception as e:
        return HTMLResponse(content=f'<div class="bg-red-50 border border-red-200 rounded-lg p-4"><p class="text-red-800">❌ Error: {str(e)}</p></div>')


@app.post("/query")
async def query_history(query: str = Form(...)):
    """Query patient history using query agent."""
    patient_id = get_patient_context()
    
    if not patient_id:
        return HTMLResponse(content='<div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4"><p class="text-yellow-800">⚠️ Please set a patient context first.</p></div>')
    
    try:
        session_service = InMemorySessionService()
        app_name = query_agent.name + "_app"
        user_id = query_agent.name + "_user"
        session_id = query_agent.name + "_session_" + patient_id
        
        await session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
        
        runner = Runner(
            agent=query_agent,
            app_name=app_name,
            session_service=session_service
        )
        
        full_query = f"Patient ID: {patient_id}\n\nQuery: {query}"
        content = types.Content(role='user', parts=[types.Part(text=full_query)])
        
        final_response_text = None
        async for event in runner.run_async(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            content=content
        ):
            if event.is_final_response():
                final_response_text = event.text
        
        html = f"""
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p class="font-semibold text-blue-800 mb-2">📊 Query Results</p>
            <p class="text-blue-700 whitespace-pre-wrap">{final_response_text or "No results found."}</p>
        </div>
        """
        return HTMLResponse(content=html)
    
    except Exception as e:
        return HTMLResponse(content=f'<div class="bg-red-50 border border-red-200 rounded-lg p-4"><p class="text-red-800">❌ Error: {str(e)}</p></div>')


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)

