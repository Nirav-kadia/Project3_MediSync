"""
Neo4j Graph Database Connection and Operations
Handles all graph operations for patient records, conditions, medications, and encounters.
"""
import os
from typing import Optional, List, Dict, Any
from neo4j import GraphDatabase, Driver
from datetime import datetime


class GraphManager:
    """Manages Neo4j connection and graph operations for MediSync."""
    
    def __init__(self, uri: Optional[str] = None, user: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize Neo4j connection.
        
        Args:
            uri: Neo4j connection URI (defaults to env var NEO4J_URI)
            user: Neo4j username (defaults to env var NEO4J_USER or 'neo4j')
            password: Neo4j password (defaults to env var NEO4J_PASSWORD)
        """
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self.driver: Optional[Driver] = None
        self._connect()
        self._initialize_schema()
    
    def _connect(self):
        """Establish connection to Neo4j."""
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Verify connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            print(f"✅ Connected to Neo4j at {self.uri}")
        except Exception as e:
            print(f"❌ Failed to connect to Neo4j: {e}")
            raise
    
    def _initialize_schema(self):
        """Initialize graph schema with constraints and indexes."""
        constraints = [
            "CREATE CONSTRAINT patient_id IF NOT EXISTS FOR (p:Patient) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT condition_code IF NOT EXISTS FOR (c:Condition) REQUIRE c.code IS UNIQUE",
            "CREATE CONSTRAINT medication_code IF NOT EXISTS FOR (m:Medication) REQUIRE m.code IS UNIQUE",
            "CREATE INDEX encounter_date IF NOT EXISTS FOR (e:Encounter) ON (e.date)",
        ]
        
        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    # Constraint might already exist, ignore
                    pass
    
    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
    
    def create_or_get_patient(self, patient_id: str, name: Optional[str] = None) -> str:
        """
        Create or retrieve a patient node.
        
        Args:
            patient_id: Unique patient identifier
            name: Patient name (optional)
        
        Returns:
            Patient ID
        """
        query = """
        MERGE (p:Patient {id: $patient_id})
        ON CREATE SET p.name = $name, p.created_at = datetime()
        ON MATCH SET p.updated_at = datetime()
        RETURN p.id as id
        """
        
        with self.driver.session() as session:
            result = session.run(query, patient_id=patient_id, name=name or patient_id)
            return result.single()["id"]
    
    def write_diagnosis_node(
        self,
        patient_id: str,
        condition_code: str,
        condition_label: str,
        encounter_date: Optional[str] = None
    ) -> bool:
        """
        Write a diagnosis to the patient graph.
        Creates: Patient -> Encounter -> Condition relationship.
        
        Args:
            patient_id: Patient identifier
            condition_code: SNOMED-CT code
            condition_label: Human-readable condition name
            encounter_date: Date of encounter (ISO format, defaults to today)
        
        Returns:
            True if successful
        """
        if not encounter_date:
            encounter_date = datetime.now().isoformat()
        
        query = """
        MATCH (p:Patient {id: $patient_id})
        MERGE (e:Encounter {patient_id: $patient_id, date: $encounter_date})
        MERGE (c:Condition {code: $condition_code})
        ON CREATE SET c.label = $condition_label, c.created_at = datetime()
        MERGE (p)-[:HAS_ENCOUNTER]->(e)
        MERGE (e)-[:DIAGNOSED_WITH]->(c)
        RETURN c.code as code
        """
        
        try:
            with self.driver.session() as session:
                session.run(
                    query,
                    patient_id=patient_id,
                    condition_code=condition_code,
                    condition_label=condition_label,
                    encounter_date=encounter_date
                )
            return True
        except Exception as e:
            print(f"Error writing diagnosis: {e}")
            return False
    
    def write_medication(
        self,
        patient_id: str,
        medication_code: str,
        medication_label: str,
        dosage: Optional[str] = None,
        condition_code: Optional[str] = None
    ) -> bool:
        """
        Write medication information to the graph.
        
        Args:
            patient_id: Patient identifier
            medication_code: RxNorm or medication code
            medication_label: Medication name
            dosage: Dosage information
            condition_code: Associated condition code (optional)
        
        Returns:
            True if successful
        """
        query = """
        MATCH (p:Patient {id: $patient_id})
        MERGE (m:Medication {code: $medication_code})
        ON CREATE SET m.label = $medication_label, m.created_at = datetime()
        MERGE (p)-[:PRESCRIBED]->(m)
        SET m.dosage = $dosage
        """
        
        # Link medication to condition if provided
        if condition_code:
            query += """
            WITH m
            MATCH (c:Condition {code: $condition_code})
            MERGE (c)-[:TREATED_WITH]->(m)
            """
        
        query += " RETURN m.code as code"
        
        try:
            with self.driver.session() as session:
                session.run(
                    query,
                    patient_id=patient_id,
                    medication_code=medication_code,
                    medication_label=medication_label,
                    dosage=dosage,
                    condition_code=condition_code
                )
            return True
        except Exception as e:
            print(f"Error writing medication: {e}")
            return False
    
    def get_patient_conditions(self, patient_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all conditions for a patient.
        
        Args:
            patient_id: Patient identifier
        
        Returns:
            List of condition dictionaries
        """
        query = """
        MATCH (p:Patient {id: $patient_id})-[:HAS_ENCOUNTER]->(e:Encounter)-[:DIAGNOSED_WITH]->(c:Condition)
        RETURN c.code as code, c.label as label, e.date as encounter_date
        ORDER BY e.date DESC
        """
        
        with self.driver.session() as session:
            result = session.run(query, patient_id=patient_id)
            return [dict(record) for record in result]
    
    def get_patient_medications(self, patient_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all medications for a patient.
        
        Args:
            patient_id: Patient identifier
        
        Returns:
            List of medication dictionaries
        """
        query = """
        MATCH (p:Patient {id: $patient_id})-[:PRESCRIBED]->(m:Medication)
        OPTIONAL MATCH (c:Condition)-[:TREATED_WITH]->(m)
        RETURN m.code as code, m.label as label, m.dosage as dosage, 
               collect(DISTINCT c.label) as conditions
        """
        
        with self.driver.session() as session:
            result = session.run(query, patient_id=patient_id)
            return [dict(record) for record in result]
    
    def retrieve_patient_history(
        self,
        patient_id: str,
        hit_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search: Retrieve patient history with optional condition filtering.
        
        Args:
            patient_id: Patient identifier
            hit_ids: Optional list of condition codes to filter by
        
        Returns:
            List of patient history records
        """
        if hit_ids:
            query = """
            MATCH (p:Patient {id: $patient_id})-[:HAS_ENCOUNTER]->(e:Encounter)-[:DIAGNOSED_WITH]->(c:Condition)
            WHERE c.code IN $hit_ids
            OPTIONAL MATCH (c)-[:TREATED_WITH]->(m:Medication)
            RETURN c.code as condition_code, c.label as condition_label,
                   e.date as encounter_date,
                   collect(DISTINCT {code: m.code, label: m.label, dosage: m.dosage}) as medications
            ORDER BY e.date DESC
            """
        else:
            query = """
            MATCH (p:Patient {id: $patient_id})-[:HAS_ENCOUNTER]->(e:Encounter)-[:DIAGNOSED_WITH]->(c:Condition)
            OPTIONAL MATCH (c)-[:TREATED_WITH]->(m:Medication)
            RETURN c.code as condition_code, c.label as condition_label,
                   e.date as encounter_date,
                   collect(DISTINCT {code: m.code, label: m.label, dosage: m.dosage}) as medications
            ORDER BY e.date DESC
            """
        
        with self.driver.session() as session:
            result = session.run(
                query,
                patient_id=patient_id,
                hit_ids=hit_ids or []
            )
            records = []
            for record in result:
                rec_dict = dict(record)
                # Filter out None medications
                rec_dict["medications"] = [m for m in rec_dict["medications"] if m.get("code")]
                records.append(rec_dict)
            return records
    
    def get_patient_graph_summary(self, patient_id: str) -> Dict[str, Any]:
        """
        Get a summary of the patient's graph structure.
        
        Args:
            patient_id: Patient identifier
        
        Returns:
            Summary dictionary with counts and relationships
        """
        query = """
        MATCH (p:Patient {id: $patient_id})
        OPTIONAL MATCH (p)-[:HAS_ENCOUNTER]->(e:Encounter)
        OPTIONAL MATCH (e)-[:DIAGNOSED_WITH]->(c:Condition)
        OPTIONAL MATCH (p)-[:PRESCRIBED]->(m:Medication)
        RETURN 
            count(DISTINCT e) as encounter_count,
            count(DISTINCT c) as condition_count,
            count(DISTINCT m) as medication_count
        """
        
        with self.driver.session() as session:
            result = session.run(query, patient_id=patient_id)
            record = result.single()
            return dict(record) if record else {}


# Global instance (will be initialized in main.py)
graph_manager: Optional[GraphManager] = None


def get_graph_manager() -> GraphManager:
    """Get or create the global graph manager instance."""
    global graph_manager
    if graph_manager is None:
        graph_manager = GraphManager()
    return graph_manager

