"""
Initialize Neo4j Graph Database
Creates sample patient data for testing.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.graph_db import GraphManager
from datetime import datetime, timedelta


def init_sample_data():
    """Initialize sample patient data."""
    print("Initializing Neo4j with sample patient data...")
    
    graph_manager = GraphManager()
    
    # Sample Patient 1
    patient_id = "PAT001"
    graph_manager.create_or_get_patient(patient_id, "John Doe")
    
    # Add some conditions
    graph_manager.write_diagnosis_node(
        patient_id=patient_id,
        condition_code="38341003",
        condition_label="Hypertensive disorder",
        encounter_date=(datetime.now() - timedelta(days=30)).isoformat()
    )
    
    graph_manager.write_diagnosis_node(
        patient_id=patient_id,
        condition_code="73211009",
        condition_label="Diabetes mellitus",
        encounter_date=(datetime.now() - timedelta(days=60)).isoformat()
    )
    
    # Add medications
    graph_manager.write_medication(
        patient_id=patient_id,
        medication_code="lisinopril",
        medication_label="Lisinopril",
        dosage="10mg daily",
        condition_code="38341003"
    )
    
    graph_manager.write_medication(
        patient_id=patient_id,
        medication_code="metformin",
        medication_label="Metformin",
        dosage="500mg twice daily",
        condition_code="73211009"
    )
    
    print(f"✅ Created sample data for patient {patient_id}")
    
    # Sample Patient 2
    patient_id = "PAT002"
    graph_manager.create_or_get_patient(patient_id, "Jane Smith")
    
    graph_manager.write_diagnosis_node(
        patient_id=patient_id,
        condition_code="195967001",
        condition_label="Asthma",
        encounter_date=(datetime.now() - timedelta(days=15)).isoformat()
    )
    
    graph_manager.write_medication(
        patient_id=patient_id,
        medication_code="albuterol",
        medication_label="Albuterol",
        dosage="2 puffs as needed",
        condition_code="195967001"
    )
    
    print(f"✅ Created sample data for patient {patient_id}")
    
    graph_manager.close()
    print("✅ Graph initialization complete!")


if __name__ == "__main__":
    init_sample_data()

