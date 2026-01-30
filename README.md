## 1. Executive Summary
**MediSync** is an interoperability engine for healthcare providers. It solves the "Unstructured Data" problem in Electronic Health Records (EHR). Doctors often write free-text notes that are hard to search.

MediSync uses a **Medical Coding Agent** to read unstructured clinical notes, extract medical entities (Symptoms, Diagnoses, Medications), and map them to standard ontologies (SNOMED-CT, RxNorm) within a **Neo4j Knowledge Graph**. It features a "Glass Box" AI approach using **Phoenix** traces to ensure every medical decision made by the AI is auditable.

## 2. Architecture Overview

This project uses **FastHTML**, a new hyper-fast web framework that allows building complex, interactive UIs using only Python (no JavaScript/React required), making it ideal for Python-centric AI engineers.

*   **Frontend/Backend:** FastHTML (HTMX + Python).
*   **Agent Framework:** Google ADK (Gemini 2.0 Flash).
*   **Inference:** Amazon Bedrock (Anthropic Claude 3.5 Sonnet - preferred for medical reasoning).
*   **Graph Database:** Neo4j (Patient Graph).
*   **Observability:** Phoenix Arize (Trace visualization & Evaluation).

### Key Features & Technology Mapping
| Feature | Technology Used | Logic |
| :--- | :--- | :--- |
| **Medical Entity Extraction** | **Amazon Bedrock** | Uses Claude 3.5 Sonnet to parse clinical notes. |
| **Ontology Mapping** | **Google ADK** | An agent equipped with a `search_ontology` tool to map "high bp" $\to$ `SCTID: 38341003 | Hypertension`. |
| **Patient Graph** | **Neo4j** | Stores a timeline: `(:Patient)-[:HAS_EVENT]->(:Encounter)-[:DIAGNOSED_WITH]->(:Condition)`. |
| **Audit Trails** | **Phoenix** | Captures every agent step. If the AI maps a symptom incorrectly, the Phoenix trace reveals exactly which tool input caused the error. |
| **Real-time UI** | **FastHTML** | WebSockets-based chat interface that renders Graph visualizations directly in the browser. |

---

## 3. Directory Structure

```text
medisync/
├── app/
│   ├── agents/
│   │   ├── medical_coder.py     # ADK Agent: Maps text to SNOMED codes
│   │   └── query_agent.py       # ADK Agent: GraphRAG Question Answering
│   ├── core/
│   │   ├── telemetry.py         # Phoenix Tracer setup
│   │   └── graph_db.py          # Neo4j Connection
│   ├── components/
│   │   ├── chat.py              # FastHTML Chat Components
│   │   └── visualizer.py        # Graph Viz Component
│   └── main.py                  # FastHTML Application Entrypoint
├── data/
│   └── ontologies/              # Local cache of SNOMED/ICD-10 stubs
├── .env
├── requirements.txt
└── docker-compose.yml
```

---

## 4. Implementation Details

### A. Phoenix Telemetry Configuration
*Located in `app/core/telemetry.py`*

In healthcare, "Black Box" AI is unacceptable. We configure Phoenix to trace every single tool call and agent thought.

**Note:** Verify the `GoogleGenAIInstrumentor` import path matches your `openinference` package version. The instrumentation package structure may vary.

```python
import phoenix as px
from phoenix.otel import register

# Note: Import path may vary - verify with your openinference version
try:
    from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
except ImportError:
    # Alternative import path for different versions
    from openinference.instrumentation.genai import GoogleGenAIInstrumentor

def setup_telemetry():
    # 1. Launch Phoenix Server locally
    session = px.launch_app()
    
    # 2. Register Tracer
    tracer_provider = register(
        project_name="medisync-production",
        endpoint="http://localhost:6006/v1/traces"
    )
    
    # 3. Auto-instrument Google ADK (Gemini) interactions
    # This automatically captures prompts, responses, and tool calls
    GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)
    
    return session.url
```

### B. The Medical Coder Agent (Google ADK)
*Located in `app/agents/medical_coder.py`*

This agent converts raw text into structured graph nodes. It uses the **Coordinator** pattern to manage data hygiene.

```python
from google.adk.agents import Agent
from google.adk.tools import ToolContext
from app.core.graph_db import write_diagnosis_node

# Tool: Ontology Lookup
def lookup_snomed_code(search_term: str) -> dict:
    """
    Searches standard medical ontology for a code.
    Example: 'Heart Attack' -> {'code': '22298006', 'label': 'Myocardial Infarction'}
    """
    # ... logic to search local embedding database of SNOMED terms ...
    return {"code": "38341003", "label": "Hypertensive disorder"}

# Tool: Graph Writer
def commit_to_patient_record(patient_id: str, condition_code: str, condition_label: str):
    """Writes the diagnosis to Neo4j."""
    write_diagnosis_node(patient_id, condition_code, condition_label)
    return "Record updated."

medical_coder = Agent(
    name="clinical_ontology_specialist",
    model="gemini-2.0-flash-live-001",
    instruction="""
    You are a Medical Coding Specialist. 
    1. Receive clinical notes.
    2. Identify distinct medical conditions.
    3. For EACH condition, use `lookup_snomed_code` to find the standard ID.
    4. IF the confidence is high, use `commit_to_patient_record`.
    5. IF ambiguous, ask the user for clarification.
    """,
    tools=[lookup_snomed_code, commit_to_patient_record]
)
```

### C. The FastHTML Application
*Located in `app/main.py`*

FastHTML allows us to write the entire web app in Python. We use HTMX for dynamic updates.

**Note:** FastHTML API may vary. Verify the `fast_app()` function signature and routing decorators (`@rt`) match your FastHTML version. The code below follows common FastHTML patterns.

```python
from fasthtml.common import *
from app.core.telemetry import setup_telemetry
from app.agents.medical_coder import medical_coder
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Initialize Telemetry
trace_url = setup_telemetry()

app, rt = fast_app()

@rt('/')
def get():
    return Titled("MediSync 🏥",
        Div(
            H2("Clinical Note Ingestion"),
            Form(
                Textarea(name='clinical_note', placeholder="Enter patient notes...", rows=5),
                Button("Process Note", hx_post="/process", hx_target="#graph-update"),
            ),
            Div(id="graph-update"),
            H3("Audit Trail"),
            A("View Phoenix Traces", href=trace_url, target="_blank")
        )
    )

@rt('/process')
async def post(clinical_note: str):
    # CRITICAL: Proper ADK Runner setup with session management
    # ADK requires SessionService, app_name, user_id, and session_id
    session_service = InMemorySessionService()
    app_name = medical_coder.name + "_app"
    user_id = medical_coder.name + "_user"
    session_id = medical_coder.name + "_session_01"
    
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
    
    # Prepare user message in ADK Content format
    content = types.Content(role='user', parts=[types.Part(text=clinical_note)])
    
    # Run agent and iterate through events to get final response
    final_response_text = None
    async for event in runner.run_async(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        content=content
    ):
        if event.is_final_response():
            final_response_text = event.text
    
    # Return HTML snippet to update the UI
    if final_response_text:
        return Div(
            P(f"Agent Processing Complete. Output: {final_response_text}"),
            P("Graph Updated.", cls="text-green-500 font-bold")
        )
    else:
        return Div(
            P("Agent processing completed, but no final response received.", cls="text-yellow-500")
        )

serve()
```

### D. GraphRAG Retrieval (Hybrid Search)
*Located in `app/agents/query_agent.py`*

When a doctor asks a question, we don't just search vectors; we traverse the graph to find temporal relationships (e.g., "conditions *after* surgery").

```python
from neo4j import GraphDatabase

def retrieve_patient_history(patient_id: str, query: str, driver: GraphDatabase.driver, hit_ids: list):
    """
    Hybrid search combining vector similarity with graph traversal.
    
    Args:
        patient_id: Patient identifier
        query: Natural language query
        driver: Neo4j driver instance
        hit_ids: List of condition IDs from vector search
    """
    # 1. Vector Search: Find nodes semantically similar to query (e.g., "Heart issues")
    # vector_hits = vector_index.query(query)  # Implemented elsewhere
    # hit_ids = [hit.id for hit in vector_hits]
    
    # 2. Graph Traversal: Expand to find related medications and lab results
    # SECURITY: Use parameterized queries to prevent Cypher injection
    # NEVER use f-strings with user input in Cypher queries
    cypher_query = """
    MATCH (p:Patient {id: $patient_id})-[:HAS_CONDITION]->(c:Condition)
    WHERE c.id IN $hit_ids
    OPTIONAL MATCH (c)-[:TREATED_WITH]->(m:Medication)
    RETURN c.label, m.label, m.dosage
    """
    
    with driver.session() as session:
        result = session.run(
            cypher_query,
            patient_id=patient_id,  # Parameterized - safe from injection
            hit_ids=hit_ids
        )
        records = [dict(record) for record in result]
    
    # 3. Contextualize for LLM
    # Format records for LLM context...
    return records
```

## 5. Deployment Guide

### Prerequisites
*   Python 3.11+.
*   Neo4j instance.
*   Google Cloud Project (for Vertex AI/Gemini) OR API Key.

### Steps
1.  **Environment**:
    ```bash
    export GOOGLE_API_KEY=...
    export NEO4J_URI=bolt://localhost:7687
    export NEO4J_PASSWORD=...
    ```
2.  **Run Phoenix (Background)**:
    Phoenix starts automatically inside the app code, but ensure port `6006` is free.
3.  **Start FastHTML App**:
    ```bash
    python app/main.py
    ```
4.  **Access**:
    *   **App:** `http://localhost:5001`
    *   **Traces:** `http://localhost:6006`

## 6. Real World Value
**MediSync** addresses the "Garbage In, Garbage Out" problem in Medical AI.
1.  **Standardization**: By forcing ADK agents to map text to SNOMED codes, we ensure the Graph contains standardized data, not random text.
2.  **Safety**: The Phoenix integration allows compliance officers to review exactly *why* the AI decided "shortness of breath" mapped to "Dyspnea" and not "Anxiety".
3.  **Speed**: FastHTML allows deployment of this complex logic as a lightweight, fast web tool without the overhead of React/Node.js.

---

## 7. Quick Start Guide

### Prerequisites
- Python 3.11+
- Docker and Docker Compose (for Neo4j)
- Google API Key (for Gemini/ADK)

### Installation

1. **Clone/Navigate to the project:**
   ```bash
   cd Project_3_MediSync_GraphRAG_Patient_Intelligence_Platform
   ```

2. **Run setup script:**
   ```bash
   ./setup.sh
   ```
   
   Or manually:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your GOOGLE_API_KEY
   ```

4. **Start Neo4j:**
   ```bash
   docker-compose up -d
   ```
   
   Wait for Neo4j to be ready (check with `docker-compose ps`)

5. **Initialize sample data (optional):**
   ```bash
   source venv/bin/activate
   python scripts/init_graph.py
   ```

6. **Run the application:**
   ```bash
   source venv/bin/activate
   python app/main.py
   ```

7. **Access the application:**
   - **Web App:** http://localhost:5001
   - **Phoenix Traces:** http://localhost:6006 (if telemetry is enabled)
   - **Neo4j Browser:** http://localhost:7474 (username: neo4j, password: medisync123)

### Usage

1. **Set Patient Context:**
   - Enter a Patient ID (e.g., "PAT001") and click "Set Patient"
   - This loads the patient's current graph summary

2. **Process Clinical Notes:**
   - Enter unstructured clinical notes in the left panel
   - Example: "Patient presents with high blood pressure and chest pain. Prescribed lisinopril 10mg daily."
   - Click "Process Note"
   - The medical coder agent will extract entities and map them to SNOMED codes

3. **Query Patient History:**
   - Enter natural language queries in the right panel
   - Example: "What conditions does this patient have?"
   - Click "Query History"
   - The query agent will retrieve and summarize patient data

### Project Structure

```
Project_3_MediSync_GraphRAG_Patient_Intelligence_Platform/
├── app/
│   ├── agents/
│   │   ├── medical_coder.py      # ADK Agent: Maps text to SNOMED codes
│   │   └── query_agent.py         # ADK Agent: GraphRAG Question Answering
│   ├── core/
│   │   ├── graph_db.py            # Neo4j Connection & Operations
│   │   ├── ontology.py            # SNOMED-CT/RxNorm Lookup
│   │   └── telemetry.py           # Phoenix Tracer setup
│   ├── components/
│   │   ├── chat.py                # FastHTML Chat Components
│   │   └── visualizer.py          # Graph Viz Components
│   └── main.py                    # FastHTML Application Entrypoint
├── data/
│   └── ontologies/                # Local cache of SNOMED/ICD-10 stubs
├── scripts/
│   └── init_graph.py              # Initialize sample patient data
├── .env                            # Environment variables (create from .env.example)
├── .gitignore
├── docker-compose.yml              # Neo4j container configuration
├── requirements.txt                # Python dependencies
├── setup.sh                        # Automated setup script
└── README.md
```

### Environment Variables

Required:
- `GOOGLE_API_KEY`: Your Google API key for Gemini/ADK
- `NEO4J_URI`: Neo4j connection URI (default: `bolt://localhost:7687`)
- `NEO4J_USER`: Neo4j username (default: `neo4j`)
- `NEO4J_PASSWORD`: Neo4j password

Optional:
- `PHOENIX_ENABLED`: Enable Phoenix telemetry (default: `true`)
- `APP_PORT`: Application port (default: `5001`)

### Troubleshooting

**Neo4j Connection Issues:**
- Ensure Neo4j is running: `docker-compose ps`
- Check connection: `docker-compose logs neo4j`
- Verify credentials in `.env` match `docker-compose.yml`

**Google ADK Issues:**
- Verify `GOOGLE_API_KEY` is set correctly
- Check API key has access to Gemini models
- Ensure `google-adk` package is installed

**Phoenix Telemetry:**
- If telemetry fails, the app will continue without it
- Check port 6006 is available
- Install: `pip install openinference[google-genai]`

### Development

**Running Tests:**
```bash
# Test graph operations
python -c "from app.core.graph_db import GraphManager; gm = GraphManager(); print('✅ Graph connection OK')"

# Test ontology lookup
python -c "from app.core.ontology import get_ontology_lookup; ol = get_ontology_lookup(); print(ol.lookup_snomed_code('hypertension'))"
```

**Adding New SNOMED Codes:**
Edit `app/core/ontology.py` or add entries to `data/ontologies/snomed.json`

**Extending Agents:**
- Modify agent instructions in `app/agents/medical_coder.py` or `app/agents/query_agent.py`
- Add new tools using the `Tool` class from `google.adk.tools`

---

## 8. License & Disclaimer

**⚠️ Medical Disclaimer:** This is a demonstration project. It is NOT intended for clinical use. Always verify medical coding with qualified professionals. SNOMED-CT codes are for demonstration purposes only.

**Development Status:** This is a complete implementation ready for development and testing. Production deployment requires additional security, authentication, and compliance measures.