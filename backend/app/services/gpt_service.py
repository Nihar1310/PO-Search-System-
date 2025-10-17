from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Tuple

from openai import OpenAI
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import ChatMessage, Conversation, PO
from . import search_service


settings = get_settings()
client = OpenAI(api_key=settings.OPENAI_API_KEY or None)

MODEL_NAME = getattr(settings, "OPENAI_MODEL", None) or "gpt-4o-mini"

SYSTEM_PROMPT = (
    "You are an assistant that helps users search and inspect purchase orders. "
    "When appropriate, call the provided functions. Summaries should be concise and actionable."
)

FUNCTION_DEFINITIONS = [
    {
        "name": "search_po",
        "description": "Search cached purchase orders by keyword, PO number, or client name.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keywords, PO number, or client name to search for.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default 5).",
                    "minimum": 1,
                    "maximum": 25,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_po_details",
        "description": "Retrieve full details for a purchase order by ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "po_id": {
                    "type": "integer",
                    "description": "Internal ID of the PO",  # matches /api/po/{id}
                }
            },
            "required": ["po_id"],
        },
    },
    {
        "name": "export_po_json",
        "description": "Return the parsed JSON payload for a purchase order (same as /export endpoint).",
        "parameters": {
            "type": "object",
            "properties": {
                "po_id": {
                    "type": "integer",
                    "description": "Internal ID of the PO",
                }
            },
            "required": ["po_id"],
        },
    },
]


def generate_reply(
    message: str,
    conversation_id: Optional[str],
    db: Session,
) -> Tuple[str, Optional[Dict[str, Any]], str]:
    if not settings.OPENAI_API_KEY:
        reply = (
            "OpenAI API key is not configured. Please set OPENAI_API_KEY to enable the AI assistant."
        )
        return reply, None, conversation_id or ""

    conversation = _get_or_create_conversation(db, conversation_id)
    conversation_id = conversation.id

    user_message = ChatMessage(
        conversation_id=conversation_id,
        role="user",
        content=message,
    )
    db.add(user_message)
    db.flush()

    history = _build_message_payload(db, conversation_id)

    structured_data: Optional[Dict[str, Any]] = None

    try:
        first_response = _call_openai(history)
    except Exception as exc:  # pragma: no cover - OpenAI dependency
        db.rollback()
        return (
            "Sorry, I couldn't reach the language model just now. Please try again shortly.",
            {"error": str(exc)},
            conversation_id,
        )

    assistant_message = first_response["choices"][0]["message"]
    finish_reason = first_response["choices"][0].get("finish_reason")

    messages_to_store: List[ChatMessage] = []

    if assistant_message.get("function_call"):
        # Store the assistant function call metadata
        tool_call_id = (
            assistant_message.get("tool_call_id")
            or (assistant_message.get("tool_calls") or [{}])[0].get("id")
        )
        messages_to_store.append(
            ChatMessage(
                conversation_id=conversation_id,
                role="assistant",
                content="",
                message_metadata={
                    "function_call": assistant_message["function_call"],
                    "tool_call_id": tool_call_id,
                    "tool_calls": assistant_message.get("tool_calls"),
                },
            )
        )

        function_name = assistant_message["function_call"]["name"]
        raw_arguments = assistant_message["function_call"].get("arguments") or "{}"
        try:
            args = json.loads(raw_arguments)
        except json.JSONDecodeError:
            args = {}

        structured_data = _execute_tool(function_name, args, db)
        tool_content = json.dumps(structured_data or {"result": None})

        tool_message = ChatMessage(
            conversation_id=conversation_id,
            role="tool",
            content=tool_content,
            message_metadata={
                "tool_name": function_name,
                "tool_call_id": tool_call_id,
            },
        )
        messages_to_store.append(tool_message)
        db.add_all(messages_to_store)
        db.flush()

        # Append assistant and tool messages to history for follow-up response
        # Use only tool_calls format (not function_call) for OpenAI v1.x compatibility
        tool_call_id = (
            assistant_message.get("tool_call_id")
            or (assistant_message.get("tool_calls") or [{}])[0].get("id")
        )
        
        history.append({
            "role": "assistant",
            "content": "",
            "tool_calls": assistant_message.get("tool_calls") or [{
                "id": tool_call_id,
                "type": "function",
                "function": assistant_message["function_call"]
            }]
        })
        
        tool_history_payload = {"role": "tool", "name": function_name, "content": tool_content}
        if tool_call_id:
            tool_history_payload["tool_call_id"] = tool_call_id
        history.append(tool_history_payload)

        try:
            second_response = _call_openai(history)
        except Exception as exc:  # pragma: no cover
            db.rollback()
            return (
                "I gathered the PO data but couldn't finish the reply. Try again.",
                structured_data,
                conversation_id,
            )

        final_message = second_response["choices"][0]["message"]
        reply_text = final_message.get("content") or "I wasn't able to compose a response."
        messages_to_store.append(
            ChatMessage(
                conversation_id=conversation_id,
                role="assistant",
                content=reply_text,
            )
        )

    else:
        reply_text = assistant_message.get("content") or "I couldn't generate a response."
        messages_to_store.append(
            ChatMessage(
                conversation_id=conversation_id,
                role="assistant",
                content=reply_text,
            )
        )
        structured_data = None

    db.add_all(messages_to_store)
    db.commit()

    return reply_text, structured_data, conversation_id


def _call_openai(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        tools=[
            {
                "type": "function",
                "function": func_def
            }
            for func_def in FUNCTION_DEFINITIONS
        ],
        tool_choice="auto",
        temperature=0.2,
    )
    
    # Convert new API format to old format for compatibility
    choice = response.choices[0]
    result = {
        "choices": [
            {
                "message": {
                    "role": choice.message.role,
                    "content": choice.message.content,
                },
                "finish_reason": choice.finish_reason,
            }
        ]
    }
    
    # Handle tool calls (new API) -> function_call (old format)
    if choice.message.tool_calls:
        tool_calls_serialized = []
        for tool_call in choice.message.tool_calls:
            tool_calls_serialized.append(
                {
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
            )

        primary_call = tool_calls_serialized[0]
        result_message = result["choices"][0]["message"]
        result_message["function_call"] = primary_call["function"]
        result_message["tool_call_id"] = primary_call["id"]
        result_message["tool_calls"] = tool_calls_serialized

    return result


def _get_or_create_conversation(db: Session, conversation_id: Optional[str]) -> Conversation:
    if conversation_id:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conversation:
            return conversation

    conversation = Conversation()
    db.add(conversation)
    db.flush()
    return conversation


def _build_message_payload(db: Session, conversation_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
        .all()
    )

    for item in history:
        metadata = item.message_metadata or {}
        if item.role == "tool":
            tool_payload = {
                "role": "tool",
                "name": metadata.get("tool_name"),
                "content": item.content,
            }
            tool_call_id = metadata.get("tool_call_id")
            if tool_call_id:
                tool_payload["tool_call_id"] = tool_call_id
            messages.append(tool_payload)
        elif item.role == "assistant" and metadata.get("function_call"):
            # Use new tool_calls format for OpenAI v1.x API
            function_call = metadata.get("function_call")
            tool_call_id = metadata.get("tool_call_id") or "call_" + str(item.id)
            
            assistant_payload = {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": tool_call_id,
                    "type": "function",
                    "function": {
                        "name": function_call["name"],
                        "arguments": function_call["arguments"]
                    }
                }]
            }
            messages.append(assistant_payload)
        else:
            messages.append({"role": item.role, "content": item.content})

    return messages


def _execute_tool(name: str, args: Dict[str, Any], db: Session) -> Optional[Dict[str, Any]]:
    if name == "search_po":
        query = args.get("query", "").strip()
        limit = int(args.get("limit") or 5)
        results = search_service.search_pos(db, query, limit=limit)
        return {
            "intent": "search",
            "query": query,
            "results": [
                {
                    "id": po.id,
                    "po_number": po.po_number,
                    "client_name": po.client_name,
                    "date": po.date.isoformat() if po.date else None,
                    "total_value": po.total_value,
                    "source": po.source,
                }
                for po in results
            ],
        }

    if name == "get_po_details":
        po_id = args.get("po_id")
        if po_id is None:
            return {"intent": "po_detail", "error": "Missing po_id"}
        po = db.query(PO).filter(PO.id == po_id).first()
        if not po:
            return {"intent": "po_detail", "error": "PO not found"}
        return {
            "intent": "po_detail",
            "po": {
                "id": po.id,
                "po_number": po.po_number,
                "date": po.date.isoformat() if po.date else None,
                "client_name": po.client_name,
                "total_value": po.total_value,
                "source": po.source,
                "filename": po.filename,
                "parsed_data": po.parsed_data,
            },
        }

    if name == "export_po_json":
        po_id = args.get("po_id")
        if po_id is None:
            return {"intent": "export", "error": "Missing po_id"}
        po = db.query(PO).filter(PO.id == po_id).first()
        if not po:
            return {"intent": "export", "error": "PO not found"}
        return {"intent": "export", "po_id": po.id, "payload": po.parsed_data}

    return {"intent": "unknown", "error": f"Unhandled tool {name}"}
