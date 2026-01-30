"""
Verify MediSync Setup
Checks that all dependencies and configurations are correct.
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

def check_imports():
    """Check that all required modules can be imported."""
    print("Checking imports...")
    
    try:
        from app.core.graph_db import GraphManager
        print("✅ app.core.graph_db")
    except Exception as e:
        print(f"❌ app.core.graph_db: {e}")
        return False
    
    try:
        from app.core.ontology import get_ontology_lookup
        print("✅ app.core.ontology")
    except Exception as e:
        print(f"❌ app.core.ontology: {e}")
        return False
    
    try:
        from app.core.telemetry import setup_telemetry
        print("✅ app.core.telemetry")
    except Exception as e:
        print(f"⚠️  app.core.telemetry: {e} (optional)")
    
    try:
        from app.agents.medical_coder import medical_coder
        print("✅ app.agents.medical_coder")
    except Exception as e:
        print(f"❌ app.agents.medical_coder: {e}")
        return False
    
    try:
        from app.agents.query_agent import query_agent
        print("✅ app.agents.query_agent")
    except Exception as e:
        print(f"❌ app.agents.query_agent: {e}")
        return False
    
    try:
        from app.components.visualizer import graph_summary_card
        print("✅ app.components.visualizer")
    except Exception as e:
        print(f"❌ app.components.visualizer: {e}")
        return False
    
    try:
        import fastapi
        print("✅ fastapi (alternative to fasthtml)")
    except Exception as e:
        print(f"⚠️  fastapi: {e} (optional, using FastAPI alternative)")
    
    try:
        from google.adk.agents import Agent
        print("✅ google.adk")
    except Exception as e:
        print(f"❌ google.adk: {e}")
        return False
    
    try:
        import neo4j
        print("✅ neo4j")
    except Exception as e:
        print(f"❌ neo4j: {e}")
        return False
    
    return True


def check_env():
    """Check environment variables."""
    import os
    print("\nChecking environment variables...")
    
    google_key = os.getenv("GOOGLE_API_KEY")
    if google_key and google_key != "your_google_api_key_here":
        print("✅ GOOGLE_API_KEY is set")
    else:
        print("⚠️  GOOGLE_API_KEY not set or using placeholder")
    
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    print(f"✅ NEO4J_URI: {neo4j_uri}")
    
    return True


def check_directories():
    """Check that required directories exist."""
    print("\nChecking directories...")
    
    base = Path(__file__).parent.parent
    required_dirs = [
        "app",
        "app/agents",
        "app/core",
        "app/components",
        "data/ontologies",
        "scripts"
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        full_path = base / dir_path
        if full_path.exists():
            print(f"✅ {dir_path}/")
        else:
            print(f"❌ {dir_path}/ (missing)")
            all_exist = False
    
    return all_exist


if __name__ == "__main__":
    print("🏥 MediSync Setup Verification\n")
    print("=" * 50)
    
    dirs_ok = check_directories()
    imports_ok = check_imports()
    env_ok = check_env()
    
    print("\n" + "=" * 50)
    if dirs_ok and imports_ok:
        print("✅ Setup verification complete!")
        print("\nNext steps:")
        print("1. Set GOOGLE_API_KEY in .env file")
        print("2. Start Neo4j: docker-compose up -d")
        print("3. Run: python app/main.py")
    else:
        print("❌ Setup verification failed. Please fix the issues above.")
        sys.exit(1)

