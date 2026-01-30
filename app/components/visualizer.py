"""
Graph Visualization Components
Components for displaying patient graph data.
"""
from fasthtml.common import *
from typing import List, Dict, Any


def graph_summary_card(summary: Dict[str, Any]) -> Div:
    """Create a summary card showing graph statistics."""
    return Div(
        cls="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4",
        children=[
            H3("Patient Graph Summary", cls="text-lg font-semibold mb-2"),
            Div(
                cls="grid grid-cols-3 gap-4",
                children=[
                    Div(
                        cls="text-center",
                        children=[
                            P(str(summary.get("encounter_count", 0)), cls="text-2xl font-bold text-blue-600"),
                            P("Encounters", cls="text-sm text-gray-600")
                        ]
                    ),
                    Div(
                        cls="text-center",
                        children=[
                            P(str(summary.get("condition_count", 0)), cls="text-2xl font-bold text-blue-600"),
                            P("Conditions", cls="text-sm text-gray-600")
                        ]
                    ),
                    Div(
                        cls="text-center",
                        children=[
                            P(str(summary.get("medication_count", 0)), cls="text-2xl font-bold text-blue-600"),
                            P("Medications", cls="text-sm text-gray-600")
                        ]
                    )
                ]
            )
        ]
    )


def conditions_list(conditions: List[Dict[str, Any]]) -> Div:
    """Create a list of patient conditions."""
    if not conditions:
        return Div(
            cls="bg-gray-50 border border-gray-200 rounded-lg p-4",
            children=[P("No conditions recorded yet.", cls="text-gray-500")]
        )
    
    condition_items = []
    for condition in conditions:
        condition_items.append(
            Div(
                cls="border-b border-gray-200 py-2",
                children=[
                    Div(
                        cls="flex justify-between items-start",
                        children=[
                            Div(
                                children=[
                                    P(condition.get("label", "Unknown"), cls="font-semibold"),
                                    P(f"SNOMED: {condition.get('code', 'N/A')}", cls="text-sm text-gray-600")
                                ]
                            ),
                            P(condition.get("encounter_date", "Unknown date"), cls="text-sm text-gray-500")
                        ]
                    )
                ]
            )
        )
    
    return Div(
        cls="bg-white border border-gray-200 rounded-lg p-4",
        children=[
            H3("Conditions", cls="text-lg font-semibold mb-3"),
            Div(children=condition_items)
        ]
    )


def medications_list(medications: List[Dict[str, Any]]) -> Div:
    """Create a list of patient medications."""
    if not medications:
        return Div(
            cls="bg-gray-50 border border-gray-200 rounded-lg p-4",
            children=[P("No medications recorded yet.", cls="text-gray-500")]
        )
    
    medication_items = []
    for med in medications:
        conditions_str = ", ".join(med.get("conditions", [])) if med.get("conditions") else "General"
        medication_items.append(
            Div(
                cls="border-b border-gray-200 py-2",
                children=[
                    Div(
                        cls="flex justify-between items-start",
                        children=[
                            Div(
                                children=[
                                    P(med.get("label", "Unknown"), cls="font-semibold"),
                                    P(f"Dosage: {med.get('dosage', 'Not specified')}", cls="text-sm text-gray-600"),
                                    P(f"For: {conditions_str}", cls="text-xs text-gray-500")
                                ]
                            )
                        ]
                    )
                ]
            )
        )
    
    return Div(
        cls="bg-white border border-gray-200 rounded-lg p-4",
        children=[
            H3("Medications", cls="text-lg font-semibold mb-3"),
            Div(children=medication_items)
        ]
    )

