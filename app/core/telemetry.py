"""
Phoenix Telemetry Configuration
Provides "Glass Box" AI observability for medical decision-making.
"""
import os
from typing import Optional

# Optional Phoenix imports
try:
    import phoenix as px
    from phoenix.otel import register
    PHOENIX_AVAILABLE = True
except ImportError:
    PHOENIX_AVAILABLE = False
    px = None
    register = None


def setup_telemetry() -> Optional[str]:
    """
    Initialize Phoenix telemetry for tracing agent interactions.
    
    Returns:
        URL to Phoenix dashboard, or None if setup fails
    """
    if not PHOENIX_AVAILABLE:
        print("⚠️  Phoenix not installed. Telemetry disabled.")
        print("   Install with: pip install phoenix openinference[google-genai]")
        return None
    
    try:
        # Launch Phoenix Server locally
        session = px.launch_app()
        
        # Register Tracer Provider
        tracer_provider = register(
            project_name="medisync-production",
            endpoint="http://localhost:6006/v1/traces"
        )
        
        # Auto-instrument Google ADK (Gemini) interactions
        # This automatically captures prompts, responses, and tool calls
        try:
            from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
        except ImportError:
            try:
                # Alternative import path for different versions
                from openinference.instrumentation.genai import GoogleGenAIInstrumentor
            except ImportError:
                print("⚠️  Warning: openinference not installed. Telemetry will be limited.")
                print("   Install with: pip install openinference[google-genai]")
                return session.url
        
        GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)
        
        print(f"✅ Phoenix telemetry initialized at {session.url}")
        return session.url
    
    except Exception as e:
        print(f"⚠️  Warning: Phoenix telemetry setup failed: {e}")
        print("   Continuing without telemetry...")
        return None

