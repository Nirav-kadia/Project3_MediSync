"""
Medical Coder Agent (Google ADK)
Converts unstructured clinical notes into structured graph nodes with SNOMED-CT codes.
"""
import os
from typing import Dict, Any, Optional
from google.adk.agents import Agent
from google.adk.tools import Tool
from app.core.graph_db import get_graph_manager
from app.core.ontology import get_ontology_lookup


# Global patient context (in production, this would come from session/auth)
_current_patient_id: Optional[str] = None


def set_patient_context(patient_id: str):
    """Set the current patient context for the agent."""
    global _current_patient_id
    _current_patient_id = patient_id


def get_patient_context() -> Optional[str]:
    """Get the current patient context."""
    return _current_patient_id


# Tool: Ontology Lookup
def lookup_snomed_code(search_term: str) -> Dict[str, Any]:
    """
    Searches standard medical ontology (SNOMED-CT) for a code.
    
    Args:
        search_term: Medical term to search (e.g., 'Heart Attack', 'high bp', 'diabetes')
    
    Returns:
        Dictionary with 'code' (SNOMED-CT code), 'label' (standard name), and 'found' (boolean)
    """
    ontology = get_ontology_lookup()
    result = ontology.lookup_snomed_code(search_term)
    
    if result:
        return {
            "code": result["code"],
            "label": result["label"],
            "found": True,
            "message": f"Found SNOMED-CT code {result['code']} for '{search_term}': {result['label']}"
        }
    else:
        return {
            "code": None,
            "label": None,
            "found": False,
            "message": f"No SNOMED-CT code found for '{search_term}'. Please use a more specific medical term."
        }


# Tool: Graph Writer
def commit_to_patient_record(
    condition_code: str,
    condition_label: str,
    patient_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Writes the diagnosis to Neo4j patient graph.
    
    Args:
        condition_code: SNOMED-CT code
        condition_label: Standard condition name
        patient_id: Patient identifier (uses current context if not provided)
    
    Returns:
        Dictionary with success status and message
    """
    patient_id = patient_id or get_patient_context()
    
    if not patient_id:
        return {
            "success": False,
            "message": "No patient context set. Please specify patient_id."
        }
    
    graph_manager = get_graph_manager()
    
    # Ensure patient exists
    graph_manager.create_or_get_patient(patient_id)
    
    # Write diagnosis
    success = graph_manager.write_diagnosis_node(
        patient_id=patient_id,
        condition_code=condition_code,
        condition_label=condition_label
    )
    
    if success:
        return {
            "success": True,
            "message": f"Successfully recorded {condition_label} (SNOMED: {condition_code}) for patient {patient_id}"
        }
    else:
        return {
            "success": False,
            "message": f"Failed to record diagnosis for patient {patient_id}"
        }


# Tool: Medication Writer
def commit_medication_to_record(
    medication_name: str,
    medication_code: Optional[str] = None,
    dosage: Optional[str] = None,
    condition_code: Optional[str] = None,
    patient_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Writes medication information to Neo4j patient graph.
    
    Args:
        medication_name: Medication name
        medication_code: Medication code (RxNorm or custom)
        dosage: Dosage information
        condition_code: Associated condition SNOMED code (optional)
        patient_id: Patient identifier (uses current context if not provided)
    
    Returns:
        Dictionary with success status and message
    """
    patient_id = patient_id or get_patient_context()
    
    if not patient_id:
        return {
            "success": False,
            "message": "No patient context set. Please specify patient_id."
        }
    
    # Use medication name as code if not provided
    if not medication_code:
        medication_code = medication_name.lower().replace(" ", "_")
    
    graph_manager = get_graph_manager()
    
    # Ensure patient exists
    graph_manager.create_or_get_patient(patient_id)
    
    # Write medication
    success = graph_manager.write_medication(
        patient_id=patient_id,
        medication_code=medication_code,
        medication_label=medication_name,
        dosage=dosage,
        condition_code=condition_code
    )
    
    if success:
        return {
            "success": True,
            "message": f"Successfully recorded medication {medication_name} for patient {patient_id}"
        }
    else:
        return {
            "success": False,
            "message": f"Failed to record medication for patient {patient_id}"
        }


# Create tools for ADK
lookup_tool = Tool(
    name="lookup_snomed_code",
    func=lookup_snomed_code,
    description="""Searches SNOMED-CT medical ontology for standardized codes.
    Use this to map medical terms from clinical notes to standard codes.
    Input: Medical term (e.g., 'high blood pressure', 'diabetes', 'chest pain')
    Output: SNOMED-CT code and standardized label."""
)

commit_tool = Tool(
    name="commit_to_patient_record",
    func=commit_to_patient_record,
    description="""Writes a diagnosis to the patient's medical record in the graph database.
    Use this AFTER you have found the correct SNOMED-CT code using lookup_snomed_code.
    Input: condition_code (SNOMED-CT code), condition_label (standard name)
    Output: Confirmation message"""
)

medication_tool = Tool(
    name="commit_medication_to_record",
    func=commit_medication_to_record,
    description="""Writes medication information to the patient's medical record.
    Use this to record medications mentioned in clinical notes.
    Input: medication_name, optional: dosage, condition_code, medication_code
    Output: Confirmation message"""
)


# Medical Coder Agent
medical_coder = Agent(
    name="clinical_ontology_specialist",
    model="gemini-2.0-flash-live-001",
    instruction="""
    You are a Medical Coding Specialist with expertise in clinical terminology and SNOMED-CT coding.
    
    Your role:
    1. Receive unstructured clinical notes from healthcare providers
    2. Identify distinct medical conditions, symptoms, and medications
    3. For EACH condition/symptom:
       - Use `lookup_snomed_code` to find the standardized SNOMED-CT code
       - Verify the code matches the clinical description
       - Use `commit_to_patient_record` to save it to the graph database
    4. For medications:
       - Extract medication name, dosage if mentioned
       - Use `commit_medication_to_record` to save medication information
       - Link to associated conditions if clear from context
    
    Important guidelines:
    - ALWAYS use lookup_snomed_code BEFORE committing to the record
    - Only commit codes you are confident about (high confidence matches)
    - If a term is ambiguous or you find multiple possible codes, ask for clarification
    - Be precise: "high bp" should map to hypertension, not just "blood pressure"
    - Extract all conditions mentioned, not just the primary one
    - Maintain patient privacy and follow medical coding standards
    
    Output format:
    - List each condition found with its SNOMED code
    - List each medication found
    - Provide a summary of what was recorded
    """,
    tools=[lookup_tool, commit_tool, medication_tool]
)

