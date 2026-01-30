"""
GraphRAG Query Agent (Google ADK)
Answers questions about patient history using graph traversal and retrieval.
"""
from typing import Dict, Any, List, Optional
from google.adk.agents import Agent
from google.adk.tools import Tool
from app.core.graph_db import get_graph_manager


# Tool: Patient History Retrieval
def retrieve_patient_history(patient_id: str, query: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve comprehensive patient history from the graph.
    
    Args:
        patient_id: Patient identifier
        query: Optional natural language query to filter results
    
    Returns:
        Dictionary with patient history including conditions, medications, and encounters
    """
    graph_manager = get_graph_manager()
    
    # Get patient summary
    summary = graph_manager.get_patient_graph_summary(patient_id)
    
    # Get all conditions
    conditions = graph_manager.get_patient_conditions(patient_id)
    
    # Get all medications
    medications = graph_manager.get_patient_medications(patient_id)
    
    # Get full history with relationships
    history = graph_manager.retrieve_patient_history(patient_id)
    
    return {
        "patient_id": patient_id,
        "summary": summary,
        "conditions": conditions,
        "medications": medications,
        "history": history,
        "message": f"Retrieved history for patient {patient_id}: {summary.get('condition_count', 0)} conditions, {summary.get('medication_count', 0)} medications"
    }


# Tool: Condition-Specific Query
def query_condition_details(patient_id: str, condition_code: Optional[str] = None, condition_label: Optional[str] = None) -> Dict[str, Any]:
    """
    Query specific condition details and related information.
    
    Args:
        patient_id: Patient identifier
        condition_code: SNOMED-CT code (optional)
        condition_label: Condition name (optional)
    
    Returns:
        Dictionary with condition details and related medications
    """
    graph_manager = get_graph_manager()
    
    if condition_code:
        # Query by code
        query = """
        MATCH (p:Patient {id: $patient_id})-[:HAS_ENCOUNTER]->(e:Encounter)-[:DIAGNOSED_WITH]->(c:Condition {code: $condition_code})
        OPTIONAL MATCH (c)-[:TREATED_WITH]->(m:Medication)
        RETURN c.code as code, c.label as label, e.date as encounter_date,
               collect(DISTINCT {code: m.code, label: m.label, dosage: m.dosage}) as medications
        ORDER BY e.date DESC
        """
        
        with graph_manager.driver.session() as session:
            result = session.run(query, patient_id=patient_id, condition_code=condition_code)
            records = [dict(record) for record in result]
            
            return {
                "patient_id": patient_id,
                "condition_code": condition_code,
                "records": records,
                "message": f"Found {len(records)} encounter(s) for condition {condition_code}"
            }
    elif condition_label:
        # Query by label (fuzzy)
        query = """
        MATCH (p:Patient {id: $patient_id})-[:HAS_ENCOUNTER]->(e:Encounter)-[:DIAGNOSED_WITH]->(c:Condition)
        WHERE toLower(c.label) CONTAINS toLower($condition_label)
        OPTIONAL MATCH (c)-[:TREATED_WITH]->(m:Medication)
        RETURN c.code as code, c.label as label, e.date as encounter_date,
               collect(DISTINCT {code: m.code, label: m.label, dosage: m.dosage}) as medications
        ORDER BY e.date DESC
        """
        
        with graph_manager.driver.session() as session:
            result = session.run(query, patient_id=patient_id, condition_label=condition_label)
            records = [dict(record) for record in result]
            
            return {
                "patient_id": patient_id,
                "condition_label": condition_label,
                "records": records,
                "message": f"Found {len(records)} encounter(s) matching '{condition_label}'"
            }
    else:
        return {
            "error": "Please provide either condition_code or condition_label"
        }


# Create tools for ADK
history_tool = Tool(
    name="retrieve_patient_history",
    func=retrieve_patient_history,
    description="""Retrieves comprehensive patient history from the medical graph.
    Use this to answer questions about a patient's medical history, conditions, and medications.
    Input: patient_id (required), query (optional natural language filter)
    Output: Complete patient history with conditions, medications, and encounter dates."""
)

condition_tool = Tool(
    name="query_condition_details",
    func=query_condition_details,
    description="""Queries specific condition details and related treatments.
    Use this to find information about a specific condition for a patient.
    Input: patient_id (required), condition_code OR condition_label (optional)
    Output: Condition details with related medications and encounter dates."""
)


# Query Agent
query_agent = Agent(
    name="patient_history_specialist",
    model="gemini-2.0-flash-live-001",
    instruction="""
    You are a Patient History Specialist with expertise in medical record retrieval and analysis.
    
    Your role:
    1. Answer questions about patient medical history using graph database queries
    2. Retrieve and summarize patient conditions, medications, and encounters
    3. Provide temporal context (when conditions were diagnosed, medication timelines)
    4. Identify relationships between conditions and treatments
    
    Guidelines:
    - Always use retrieve_patient_history first to get comprehensive patient data
    - Use query_condition_details for specific condition inquiries
    - Present information in a clear, chronological format when relevant
    - Highlight important relationships (e.g., medications treating specific conditions)
    - If patient_id is not provided in the query, ask for it
    - Maintain patient privacy and HIPAA compliance in responses
    
    Output format:
    - Provide clear, structured answers
    - Include relevant dates and timelines
    - Explain relationships between conditions and treatments
    - Summarize key findings
    """,
    tools=[history_tool, condition_tool]
)

