"""
MediSync - Simplified FastHTML Application
Working version without google.adk dependency
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fasthtml.common import *
from app.core.graph_db import get_graph_manager
from app.core.ontology import get_ontology_lookup
from app.components.visualizer import graph_summary_card, conditions_list, medications_list
from google import genai
from google.genai import types

load_dotenv()

# Initialize graph manager and ontology
graph_manager = get_graph_manager()
ontology_lookup = get_ontology_lookup()

# Configure Gemini
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Global patient context
_current_patient_id = None

# Initialize FastHTML app
app, rt = fast_app()


@rt('/')
def get():
    """Main page with clinical note ingestion and patient history query."""
    return Titled(
        "MediSync 🏥 - GraphRAG Patient Intelligence Platform..!",
        Div(
            cls="min-h-screen bg-gray-50",
            children=[
                # Header
                Div(
                    cls="bg-blue-600 text-white p-4 shadow-md",
                    children=[
                        H1("MediSync 🏥", cls="text-2xl font-bold"),
                        P("GraphRAG Patient Intelligence Platform (Simplified)", cls="text-blue-100")
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
                                                    cls="flex-1 px-4 py-2 border rounded-lg",
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
                                                    cls="w-full px-4 py-2 border rounded-lg mb-4",
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
                                                    cls="w-full px-4 py-2 border rounded-lg mb-4",
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
                        )
                    ]
                )
            ]
        )
    )


@rt('/set_patient')
def post(patient_id: str):
    """Set the current patient context."""
    global _current_patient_id
    _current_patient_id = patient_id
    
    # Create patient if doesn't exist
    graph_manager.create_or_get_patient(patient_id)
    
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
def post(clinical_note: str):
    """Process clinical note using Gemini."""
    global _current_patient_id
    
    if not _current_patient_id:
        return Div(
            cls="bg-yellow-50 border border-yellow-200 rounded-lg p-4",
            children=[
                P("⚠️ Please set a patient context first.", cls="text-yellow-800")
            ]
        )
    
    try:
        # Use Gemini to extract medical entities
        prompt = f"""Extract medical conditions and medications from this clinical note.
        
Clinical Note: {clinical_note}

Return a JSON response with this structure:
{{
    "conditions": [
        {{"term": "condition name", "description": "brief description"}}
    ],
    "medications": [
        {{"name": "medication name", "dosage": "dosage info"}}
    ]
}}

Only return the JSON, no other text."""

        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt
        )
        result_text = response.text.strip()
        
        # Parse response (simplified - in production use proper JSON parsing)
        import json
        # Remove markdown code blocks if present
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
            
        data = json.loads(result_text)
        
        # Process conditions
        processed_conditions = []
        for condition in data.get("conditions", []):
            term = condition.get("term", "")
            # Look up SNOMED code
            snomed_result = ontology_lookup.lookup_snomed_code(term)
            if snomed_result:
                graph_manager.write_diagnosis_node(
                    patient_id=_current_patient_id,
                    condition_code=snomed_result["code"],
                    condition_label=snomed_result["label"]
                )
                processed_conditions.append(snomed_result["label"])
        
        # Process medications
        processed_meds = []
        for med in data.get("medications", []):
            name = med.get("name", "")
            dosage = med.get("dosage", "")
            graph_manager.write_medication(
                patient_id=_current_patient_id,
                medication_code=name.lower().replace(" ", "_"),
                medication_label=name,
                dosage=dosage
            )
            processed_meds.append(f"{name} ({dosage})")
        
        # Get updated patient data
        summary = graph_manager.get_patient_graph_summary(_current_patient_id)
        conditions = graph_manager.get_patient_conditions(_current_patient_id)
        medications = graph_manager.get_patient_medications(_current_patient_id)
        
        return Div(
            cls="space-y-4",
            children=[
                Div(
                    cls="bg-green-50 border border-green-200 rounded-lg p-4",
                    children=[
                        P("✅ Note Processed Successfully", cls="font-semibold text-green-800 mb-2"),
                        P(f"Extracted {len(processed_conditions)} conditions and {len(processed_meds)} medications", 
                          cls="text-green-700")
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
                P(str(e), cls="text-red-700 text-sm")
            ]
        )


@rt('/query')
def post(query: str):
    """Query patient history using Gemini."""
    global _current_patient_id
    
    if not _current_patient_id:
        return Div(
            cls="bg-yellow-50 border border-yellow-200 rounded-lg p-4",
            children=[
                P("⚠️ Please set a patient context first.", cls="text-yellow-800")
            ]
        )
    
    try:
        # Get patient data from graph
        conditions = graph_manager.get_patient_conditions(_current_patient_id)
        medications = graph_manager.get_patient_medications(_current_patient_id)
        
        # Build context for Gemini
        context = f"""Patient ID: {_current_patient_id}

Conditions:
{chr(10).join([f"- {c['label']} (Code: {c['code']}, Date: {c['encounter_date']})" for c in conditions])}

Medications:
{chr(10).join([f"- {m['label']} - {m['dosage']}" for m in medications])}

User Question: {query}

Please answer the question based on the patient data above."""

        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=context
        )
        
        return Div(
            cls="bg-blue-50 border border-blue-200 rounded-lg p-4",
            children=[
                P("📊 Query Results", cls="font-semibold text-blue-800 mb-2"),
                Div(
                    cls="prose max-w-none",
                    children=[
                        P(response.text, cls="text-blue-700 whitespace-pre-wrap")
                    ]
                )
            ]
        )
    
    except Exception as e:
        return Div(
            cls="bg-red-50 border border-red-200 rounded-lg p-4",
            children=[
                P("❌ Error querying patient history", cls="font-semibold text-red-800 mb-2"),
                P(str(e), cls="text-red-700 text-sm")
            ]
        )


if __name__ == "__main__":
    serve()
