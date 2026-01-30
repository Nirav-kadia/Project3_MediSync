"""
FastHTML Chat Components
UI components for the chat interface.
"""
from fasthtml.common import *


def chat_container() -> Div:
    """Create the main chat container."""
    return Div(
        id="chat-container",
        cls="flex flex-col h-full bg-white rounded-lg shadow-lg",
        children=[
            Div(
                id="chat-messages",
                cls="flex-1 overflow-y-auto p-4 space-y-4",
                children=[]
            ),
            Div(
                id="chat-input-container",
                cls="border-t p-4",
                children=[
                    Form(
                        id="chat-form",
                        hx_post="/chat",
                        hx_target="#chat-messages",
                        hx_swap="beforeend",
                        children=[
                            Div(
                                cls="flex gap-2",
                                children=[
                                    Input(
                                        type="text",
                                        name="message",
                                        id="chat-input",
                                        placeholder="Ask about patient history...",
                                        cls="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                                        required=True
                                    ),
                                    Button(
                                        "Send",
                                        type="submit",
                                        cls="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    )
                                ]
                            )
                        ]
                    )
                ]
            )
        ]
    )


def chat_message(content: str, role: str = "user") -> Div:
    """
    Create a chat message bubble.
    
    Args:
        content: Message content
        role: 'user' or 'assistant'
    """
    if role == "user":
        return Div(
            cls="flex justify-end",
            children=[
                Div(
                    cls="max-w-3xl bg-blue-600 text-white rounded-lg px-4 py-2",
                    children=[P(content)]
                )
            ]
        )
    else:
        return Div(
            cls="flex justify-start",
            children=[
                Div(
                    cls="max-w-3xl bg-gray-200 text-gray-800 rounded-lg px-4 py-2",
                    children=[P(content)]
                )
            ]
        )

