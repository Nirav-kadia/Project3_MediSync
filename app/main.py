"""
MediSync - FastHTML Application Entrypoint
Main application for clinical note ingestion and patient history queries.
"""
import os
from fasthtml.common import *
from app.core.telemetry import setup_telemetry
from app.core.graph_db import get_graph_manager
from app.agents.medical_coder import medical_coder, set_patient_context, get_patient_context
from app.agents.query_agent import query_agent
from app.components.chat import chat_message
from app.components.visualizer import graph_summary_card, conditions_list, medications_list
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


# Initialize telemetry
trace_url = setup_telemetry()

# Initialize graph manager
graph_manager = get_graph_manager()

# Initialize FastHTML app
app, rt = fast_app()


@rt('/')
def get():
    """Main page with clinical note ingestion and patient history query."""
    return Titled(
        "MediSync 🏥 - GraphRAG Patient Intelligence Platform",
        Div(
            cls="min-h-screen bg-gray-50",
            children=[
                # Header
                Div(
                    cls="bg-blue-600 text-white p-4 shadow-md",
                    children=[
                        H1("MediSync 🏥", cls="text-2xl font-bold"),
                        P("GraphRAG Patient Intelligence Platform", cls="text-blue-100")
                    ]
                ),
                
                # Main Content
                Div(
                    cls="container mx-auto px-4 py-8 max-w-6xl",
                    children=[
                        # Patient Context Section
                        Div(
                            cls="bg-white rounded-lg shadow-md p-6 mb-6",
                            children=[
                                H2("Patient Context", cls="text-xl font-semibold mb-4"),
                                Form(
                                    hx_post="/set_patient",
                                    hx_target="#patient-info",
                                    hx_swap="innerHTML",
                                    children=[
                                        Div(
                                            cls="flex gap-2",
                                            children=[
                                                Input(
                                                    type="text",
                                                    name="patient_id",
                                                    placeholder="Enter Patient ID (e.g., PAT001)",
                                                    cls="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                                                    required=True
                                                ),
                                                Button(
                                                    "Set Patient",
                                                    type="submit",
                                                    cls="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                                                )
                                            ]
                                        )
                                    ]
                                ),
                                Div(id="patient-info", cls="mt-4")
                            ]
                        ),
                        
                        # Two Column Layout
                        Div(
                            cls="grid grid-cols-1 lg:grid-cols-2 gap-6",
                            children=[
                                # Left Column: Clinical Note Ingestion
                                Div(
                                    cls="bg-white rounded-lg shadow-md p-6",
                                    children=[
                                        H2("Clinical Note Ingestion", cls="text-xl font-semibold mb-4"),
                                        Form(
                                            hx_post="/process",
                                            hx_target="#graph-update",
                                            hx_swap="innerHTML",
                                            children=[
                                                Textarea(
                                                    name="clinical_note",
                                                    placeholder="Enter patient clinical notes...\n\nExample:\nPatient presents with high blood pressure and chest pain. Prescribed lisinopril 10mg daily.",
                                                    rows=8,
                                                    cls="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4",
                                                    required=True
                                                ),
                                                Button(
                                                    "Process Note",
                                                    type="submit",
                                                    cls="w-full px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                                                )
                                            ]
                                        ),
                                        Div(id="graph-update", cls="mt-4")
                                    ]
                                ),
                                
                                # Right Column: Patient History Query
                                Div(
                                    cls="bg-white rounded-lg shadow-md p-6",
                                    children=[
                                        H2("Patient History Query", cls="text-xl font-semibold mb-4"),
                                        Form(
                                            hx_post="/query",
                                            hx_target="#query-results",
                                            hx_swap="innerHTML",
                                            children=[
                                                Textarea(
                                                    name="query",
                                                    placeholder="Ask about patient history...\n\nExample:\nWhat conditions does this patient have?\nWhat medications are prescribed?",
                                                    rows=4,
                                                    cls="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4",
                                                    required=True
                                                ),
                                                Button(
                                                    "Query History",
                                                    type="submit",
                                                    cls="w-full px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                                                )
                                            ]
                                        ),
                                        Div(id="query-results", cls="mt-4")
                                    ]
                                )
                            ]
                        ),
                        
                        # Patient Graph Summary Section
                        Div(
                            id="patient-summary-section",
                            cls="mt-6"
                        ),
                        
                        # Audit Trail Link
                        Div(
                            cls="mt-6 text-center",
                            children=[
                                P("Audit Trail", cls="text-sm text-gray-600 mb-2"),
                                A(
                                    "View Phoenix Traces",
                                    href=trace_url or "#",
                                    target="_blank",
                                    cls="text-blue-600 hover:underline"
                                ) if trace_url else P("Telemetry not available", cls="text-gray-400")
                            ]
                        )
                    ]
                )
            ]
        )
    )


@rt('/set_patient')
async def post(patient_id: str):
    """Set the current patient context."""
    set_patient_context(patient_id)
    
    # Get patient summary
    summary = graph_manager.get_patient_graph_summary(patient_id)
    conditions = graph_manager.get_patient_conditions(patient_id)
    medications = graph_manager.get_patient_medications(patient_id)
    
    return Div(
        cls="bg-green-50 border border-green-200 rounded-lg p-4",
        children=[
            P(f"✅ Patient context set to: {patient_id}", cls="font-semibold text-green-800 mb-2"),
            graph_summary_card(summary),
            Div(
                cls="mt-4 space-y-4",
                children=[
                    conditions_list(conditions),
                    medications_list(medications)
                ]
            )
        ]
    )


@rt('/process')
async def post(clinical_note: str):
    """Process clinical note using medical coder agent."""
    patient_id = get_patient_context()
    
    if not patient_id:
        return Div(
            cls="bg-yellow-50 border border-yellow-200 rounded-lg p-4",
            children=[
                P("⚠️ Please set a patient context first before processing notes.", cls="text-yellow-800")
            ]
        )
    
    # Setup ADK Runner
    session_service = InMemorySessionService()
    app_name = medical_coder.name + "_app"
    user_id = medical_coder.name + "_user"
    session_id = medical_coder.name + "_session_" + patient_id
    
    try:
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
        
        # Prepare user message
        content = types.Content(role='user', parts=[types.Part(text=clinical_note)])
        
        # Run agent
        final_response_text = None
        async for event in runner.run_async(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            content=content
        ):
            if event.is_final_response():
                final_response_text = event.text
        
        # Get updated patient data
        summary = graph_manager.get_patient_graph_summary(patient_id)
        conditions = graph_manager.get_patient_conditions(patient_id)
        medications = graph_manager.get_patient_medications(patient_id)
        
        return Div(
            cls="space-y-4",
            children=[
                Div(
                    cls="bg-green-50 border border-green-200 rounded-lg p-4",
                    children=[
                        P("✅ Agent Processing Complete", cls="font-semibold text-green-800 mb-2"),
                        P(final_response_text or "Note processed successfully.", cls="text-green-700")
                    ]
                ),
                graph_summary_card(summary),
                Div(
                    cls="grid grid-cols-1 md:grid-cols-2 gap-4",
                    children=[
                        conditions_list(conditions),
                        medications_list(medications)
                    ]
                )
            ]
        )
    
    except Exception as e:
        return Div(
            cls="bg-red-50 border border-red-200 rounded-lg p-4",
            children=[
                P("❌ Error processing note", cls="font-semibold text-red-800 mb-2"),
                P(str(e), cls="text-red-700")
            ]
        )


@rt('/query')
async def post(query: str):
    """Query patient history using query agent."""
    patient_id = get_patient_context()
    
    if not patient_id:
        return Div(
            cls="bg-yellow-50 border border-yellow-200 rounded-lg p-4",
            children=[
                P("⚠️ Please set a patient context first before querying.", cls="text-yellow-800")
            ]
        )
    
    # Setup ADK Runner
    session_service = InMemorySessionService()
    app_name = query_agent.name + "_app"
    user_id = query_agent.name + "_user"
    session_id = query_agent.name + "_session_" + patient_id
    
    try:
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
        
        # Prepare query with patient context
        full_query = f"Patient ID: {patient_id}\n\nQuery: {query}"
        content = types.Content(role='user', parts=[types.Part(text=full_query)])
        
        # Run agent
        final_response_text = None
        async for event in runner.run_async(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            content=content
        ):
            if event.is_final_response():
                final_response_text = event.text
        
        return Div(
            cls="bg-blue-50 border border-blue-200 rounded-lg p-4",
            children=[
                P("📊 Query Results", cls="font-semibold text-blue-800 mb-2"),
                Div(
                    cls="prose max-w-none",
                    children=[
                        P(final_response_text or "No results found.", cls="text-blue-700 whitespace-pre-wrap")
                    ]
                )
            ]
        )
    
    except Exception as e:
        return Div(
            cls="bg-red-50 border border-red-200 rounded-lg p-4",
            children=[
                P("❌ Error querying patient history", cls="font-semibold text-red-800 mb-2"),
                P(str(e), cls="text-red-700")
            ]
        )


if __name__ == "__main__":
    serve()

