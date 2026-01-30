"""
Local Testing Script for MediSync
Tests core functionality without requiring full setup.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_ontology():
    """Test ontology lookup."""
    print("Testing Ontology Lookup...")
    try:
        from app.core.ontology import get_ontology_lookup
        ol = get_ontology_lookup()
        
        test_cases = [
            ("hypertension", "38341003"),
            ("diabetes", "73211009"),
            ("heart attack", "22298006"),
        ]
        
        all_passed = True
        for term, expected_code in test_cases:
            result = ol.lookup_snomed_code(term)
            if result and result.get("code") == expected_code:
                print(f"  ✅ '{term}' -> {expected_code}")
            else:
                print(f"  ❌ '{term}' -> {result}")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_graph_connection():
    """Test Neo4j connection."""
    print("\nTesting Neo4j Connection...")
    try:
        from app.core.graph_db import GraphManager
        
        # Try to connect
        gm = GraphManager()
        print("  ✅ Neo4j connection successful!")
        
        # Test basic operation
        test_patient = "TEST_PATIENT_001"
        gm.create_or_get_patient(test_patient, "Test Patient")
        print(f"  ✅ Created test patient: {test_patient}")
        
        # Clean up
        # (In production, you'd want to delete test data)
        gm.close()
        return True
    except Exception as e:
        print(f"  ⚠️  Neo4j connection failed: {e}")
        print("     This is expected if Neo4j is not running.")
        print("     Start Neo4j with: docker-compose up -d")
        return False


def test_imports():
    """Test that all modules can be imported."""
    print("\nTesting Module Imports...")
    modules = [
        "app.core.graph_db",
        "app.core.ontology",
        "app.core.telemetry",
        "app.agents.medical_coder",
        "app.agents.query_agent",
    ]
    
    all_passed = True
    for module in modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except Exception as e:
            print(f"  ❌ {module}: {e}")
            all_passed = False
    
    return all_passed


def main():
    """Run all tests."""
    print("🏥 MediSync Local Testing\n")
    print("=" * 50)
    
    imports_ok = test_imports()
    ontology_ok = test_ontology()
    graph_ok = test_graph_connection()
    
    print("\n" + "=" * 50)
    print("\nTest Summary:")
    print(f"  Imports: {'✅' if imports_ok else '❌'}")
    print(f"  Ontology: {'✅' if ontology_ok else '❌'}")
    print(f"  Graph DB: {'✅' if graph_ok else '⚠️  (Neo4j not running)'}")
    
    if imports_ok and ontology_ok:
        print("\n✅ Core functionality is working!")
        if not graph_ok:
            print("\n⚠️  To test graph functionality, start Neo4j:")
            print("   docker-compose up -d")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

