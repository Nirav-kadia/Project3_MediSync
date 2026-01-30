"""
Medical Ontology Lookup System
Provides SNOMED-CT and RxNorm code mapping functionality.
"""
import json
import os
from typing import Dict, List, Optional
from pathlib import Path


class OntologyLookup:
    """Handles medical ontology lookups (SNOMED-CT, RxNorm)."""
    
    def __init__(self, ontologies_dir: Optional[str] = None):
        """
        Initialize ontology lookup with local cache.
        
        Args:
            ontologies_dir: Directory containing ontology JSON files
        """
        if ontologies_dir is None:
            base_dir = Path(__file__).parent.parent.parent
            ontologies_dir = base_dir / "data" / "ontologies"
        
        self.ontologies_dir = Path(ontologies_dir)
        self.ontologies_dir.mkdir(parents=True, exist_ok=True)
        
        # Load ontologies
        self.snomed_cache: Dict[str, Dict] = {}
        self.rxnorm_cache: Dict[str, Dict] = {}
        self._load_ontologies()
    
    def _load_ontologies(self):
        """Load ontology data from JSON files."""
        snomed_file = self.ontologies_dir / "snomed.json"
        rxnorm_file = self.ontologies_dir / "rxnorm.json"
        
        if snomed_file.exists():
            with open(snomed_file, 'r') as f:
                self.snomed_cache = json.load(f)
        
        if rxnorm_file.exists():
            with open(rxnorm_file, 'r') as f:
                self.rxnorm_cache = json.load(f)
        
        # If no files exist, initialize with common medical terms
        if not self.snomed_cache:
            self._initialize_default_snomed()
            self._save_ontologies()
    
    def _initialize_default_snomed(self):
        """Initialize with common SNOMED-CT codes for demonstration."""
        self.snomed_cache = {
            "hypertension": {"code": "38341003", "label": "Hypertensive disorder"},
            "high blood pressure": {"code": "38341003", "label": "Hypertensive disorder"},
            "high bp": {"code": "38341003", "label": "Hypertensive disorder"},
            "htn": {"code": "38341003", "label": "Hypertensive disorder"},
            "diabetes": {"code": "73211009", "label": "Diabetes mellitus"},
            "diabetes mellitus": {"code": "73211009", "label": "Diabetes mellitus"},
            "type 2 diabetes": {"code": "44054006", "label": "Type 2 diabetes mellitus"},
            "t2dm": {"code": "44054006", "label": "Type 2 diabetes mellitus"},
            "asthma": {"code": "195967001", "label": "Asthma"},
            "copd": {"code": "13645005", "label": "Chronic obstructive pulmonary disease"},
            "chronic obstructive pulmonary disease": {"code": "13645005", "label": "Chronic obstructive pulmonary disease"},
            "pneumonia": {"code": "233604007", "label": "Pneumonia"},
            "myocardial infarction": {"code": "22298006", "label": "Myocardial infarction"},
            "heart attack": {"code": "22298006", "label": "Myocardial infarction"},
            "mi": {"code": "22298006", "label": "Myocardial infarction"},
            "dyspnea": {"code": "267036007", "label": "Dyspnea"},
            "shortness of breath": {"code": "267036007", "label": "Dyspnea"},
            "sob": {"code": "267036007", "label": "Dyspnea"},
            "chest pain": {"code": "29857009", "label": "Chest pain"},
            "fever": {"code": "386661006", "label": "Fever"},
            "cough": {"code": "49727002", "label": "Cough"},
            "headache": {"code": "25064002", "label": "Headache"},
            "anxiety": {"code": "48694002", "label": "Anxiety disorder"},
            "depression": {"code": "35489007", "label": "Depressive disorder"},
        }
    
    def _save_ontologies(self):
        """Save ontology caches to JSON files."""
        snomed_file = self.ontologies_dir / "snomed.json"
        rxnorm_file = self.ontologies_dir / "rxnorm.json"
        
        with open(snomed_file, 'w') as f:
            json.dump(self.snomed_cache, f, indent=2)
        
        if self.rxnorm_cache:
            with open(rxnorm_file, 'w') as f:
                json.dump(self.rxnorm_cache, f, indent=2)
    
    def lookup_snomed_code(self, search_term: str) -> Optional[Dict[str, str]]:
        """
        Search for SNOMED-CT code by term.
        
        Args:
            search_term: Medical term to search for (e.g., "high bp", "diabetes")
        
        Returns:
            Dictionary with 'code' and 'label', or None if not found
        """
        search_lower = search_term.lower().strip()
        
        # Exact match
        if search_lower in self.snomed_cache:
            return self.snomed_cache[search_lower]
        
        # Partial match (contains)
        for key, value in self.snomed_cache.items():
            if search_lower in key or key in search_lower:
                return value
        
        # Fuzzy match on label
        for key, value in self.snomed_cache.items():
            if search_lower in value["label"].lower():
                return value
        
        return None
    
    def lookup_rxnorm_code(self, medication_name: str) -> Optional[Dict[str, str]]:
        """
        Search for RxNorm code by medication name.
        
        Args:
            medication_name: Medication name to search for
        
        Returns:
            Dictionary with 'code' and 'label', or None if not found
        """
        search_lower = medication_name.lower().strip()
        
        # Exact match
        if search_lower in self.rxnorm_cache:
            return self.rxnorm_cache[search_lower]
        
        # Partial match
        for key, value in self.rxnorm_cache.items():
            if search_lower in key or key in search_lower:
                return value
        
        return None
    
    def add_snomed_mapping(self, term: str, code: str, label: str):
        """Add a new SNOMED mapping to the cache."""
        self.snomed_cache[term.lower()] = {"code": code, "label": label}
        self._save_ontologies()
    
    def add_rxnorm_mapping(self, term: str, code: str, label: str):
        """Add a new RxNorm mapping to the cache."""
        self.rxnorm_cache[term.lower()] = {"code": code, "label": label}
        self._save_ontologies()


# Global instance
_ontology_lookup: Optional[OntologyLookup] = None


def get_ontology_lookup() -> OntologyLookup:
    """Get or create the global ontology lookup instance."""
    global _ontology_lookup
    if _ontology_lookup is None:
        _ontology_lookup = OntologyLookup()
    return _ontology_lookup

