#!/usr/bin/env python3
"""
MCP Server dla Poker
Umożliwia botom interakcję z grą pokera poprzez standardowy protokół MCP
"""

import asyncio
import json
import os
import sys
from typing import Any
import httpx
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp import types

# URL do API pokera
POKER_API_URL = os.getenv("POKER_API_URL", "http://localhost:5000")

app = Server("poker-mcp")

# Global API key storage (in-memory)
_stored_api_key = None

def get_stored_api_key():
    """Pobiera zapisany klucz API"""
    return _stored_api_key

def set_stored_api_key(api_key: str):
    """Zapisuje klucz API w pamięci"""
    global _stored_api_key
    _stored_api_key = api_key

def get_headers(api_key: str = None):
    """Tworzy headers z API key dla requestów"""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    return headers

async def make_request(method: str, endpoint: str, api_key: str = None, data: dict = None):
    """Wykonuje HTTP request do API pokera"""
    url = f"{POKER_API_URL}{endpoint}"
    headers = get_headers(api_key)
    
    async with httpx.AsyncClient() as client:
        if method == "GET":
            response = await client.get(url, headers=headers)
        elif method == "POST":
            response = await client.post(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response.raise_for_status()
        return response.json()

@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """Lista dostępnych narzędzi MCP dla botów"""
    return [
        types.Tool(
            name="set_api_key",
            description="Zapisuje klucz API bota do użycia w kolejnych operacjach. Po ustawieniu, inne narzędzia mogą działać bez podawania api_key za każdym razem.",
            inputSchema={
                "type": "object",
                "properties": {
                    "api_key": {
                        "type": "string",
                        "description": "Klucz API bota do zapisania"
                    }
                },
                "required": ["api_key"]
            }
        ),
        types.Tool(
            name="get_stored_api_key",
            description="Pobiera aktualnie zapisany klucz API (jeśli został ustawiony)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="list_games",
            description="Pobiera listę wszystkich dostępnych gier pokera",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="create_game",
            description="Tworzy nową grę pokera. Możesz podać api_key lub użyć wcześniej zapisanego klucza (set_api_key).",
            inputSchema={
                "type": "object",
                "properties": {
                    "api_key": {
                        "type": "string",
                        "description": "Klucz API bota (opcjonalny jeśli wcześniej ustawiony przez set_api_key)"
                    },
                    "game_name": {
                        "type": "string",
                        "description": "Nazwa gry"
                    }
                },
                "required": ["game_name"]
            }
        ),
        types.Tool(
            name="join_game",
            description="Dołącz do istniejącej gry. Możesz podać api_key lub użyć wcześniej zapisanego klucza (set_api_key).",
            inputSchema={
                "type": "object",
                "properties": {
                    "api_key": {
                        "type": "string",
                        "description": "Klucz API bota (opcjonalny jeśli wcześniej ustawiony przez set_api_key)"
                    },
                    "game_id": {
                        "type": "number",
                        "description": "ID gry"
                    }
                },
                "required": ["game_id"]
            }
        ),
        types.Tool(
            name="get_game_state",
            description="Pobiera aktualny stan gry",
            inputSchema={
                "type": "object",
                "properties": {
                    "game_id": {
                        "type": "number",
                        "description": "ID gry"
                    }
                },
                "required": ["game_id"]
            }
        ),
        types.Tool(
            name="make_action",
            description="Wykonaj akcję w grze (fold, check, call, raise, all_in). Możesz podać api_key lub użyć wcześniej zapisanego klucza (set_api_key).",
            inputSchema={
                "type": "object",
                "properties": {
                    "api_key": {
                        "type": "string",
                        "description": "Klucz API bota (opcjonalny jeśli wcześniej ustawiony przez set_api_key)"
                    },
                    "game_id": {
                        "type": "number",
                        "description": "ID gry"
                    },
                    "action": {
                        "type": "string",
                        "description": "Akcja do wykonania",
                        "enum": ["fold", "check", "call", "raise", "all_in"]
                    },
                    "amount": {
                        "type": "number",
                        "description": "Kwota (dla raise)"
                    }
                },
                "required": ["game_id", "action"]
            }
        ),
        types.Tool(
            name="start_game",
            description="Rozpocznij grę (tylko dla kreatora gry). Możesz podać api_key lub użyć wcześniej zapisanego klucza (set_api_key).",
            inputSchema={
                "type": "object",
                "properties": {
                    "api_key": {
                        "type": "string",
                        "description": "Klucz API bota (opcjonalny jeśli wcześniej ustawiony przez set_api_key)"
                    },
                    "game_id": {
                        "type": "number",
                        "description": "ID gry"
                    }
                },
                "required": ["game_id"]
            }
        )
    ]

@app.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Obsługuje wywołania narzędzi MCP"""
    
    if not arguments:
        arguments = {}
    
    try:
        if name == "set_api_key":
            api_key = arguments.get("api_key")
            if not api_key:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"error": "api_key is required"})
                )]
            
            set_stored_api_key(api_key)
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "message": f"API key został zapisany (końcówka: ...{api_key[-8:]})",
                    "note": "Możesz teraz używać innych narzędzi bez podawania api_key"
                }, indent=2)
            )]
        
        elif name == "get_stored_api_key":
            stored_key = get_stored_api_key()
            if stored_key:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "has_key": True,
                        "key_preview": f"...{stored_key[-8:]}",
                        "message": "Klucz API jest zapisany i może być używany"
                    }, indent=2)
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "has_key": False,
                        "message": "Brak zapisanego klucza API. Użyj set_api_key aby go ustawić."
                    }, indent=2)
                )]
        
        elif name == "list_games":
            result = await make_request("GET", "/api/games/list")
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "create_game":
            api_key = arguments.get("api_key") or get_stored_api_key()
            if not api_key:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "error": "API key is required. Either provide it or use set_api_key first."
                    })
                )]
            
            game_name = arguments.get("game_name")
            
            result = await make_request(
                "POST",
                "/api/games/create",
                api_key=api_key,
                data={"name": game_name}
            )
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "join_game":
            api_key = arguments.get("api_key") or get_stored_api_key()
            if not api_key:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "error": "API key is required. Either provide it or use set_api_key first."
                    })
                )]
            
            game_id = arguments.get("game_id")
            
            result = await make_request(
                "POST",
                f"/api/games/{game_id}/join",
                api_key=api_key
            )
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "get_game_state":
            game_id = arguments.get("game_id")
            
            result = await make_request(
                "GET",
                f"/api/games/{game_id}/state"
            )
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "make_action":
            api_key = arguments.get("api_key") or get_stored_api_key()
            if not api_key:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "error": "API key is required. Either provide it or use set_api_key first."
                    })
                )]
            
            game_id = arguments.get("game_id")
            action = arguments.get("action")
            amount = arguments.get("amount", 0)
            
            result = await make_request(
                "POST",
                f"/api/games/{game_id}/action",
                api_key=api_key,
                data={"action": action, "amount": amount}
            )
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "start_game":
            api_key = arguments.get("api_key") or get_stored_api_key()
            if not api_key:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "error": "API key is required. Either provide it or use set_api_key first."
                    })
                )]
            
            game_id = arguments.get("game_id")
            
            result = await make_request(
                "POST",
                f"/api/games/{game_id}/start",
                api_key=api_key
            )
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]

async def main():
    """Uruchamia serwer MCP"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="poker-mcp",
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
