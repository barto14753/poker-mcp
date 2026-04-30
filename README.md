# Poker MCP

Web-based poker game with AI bot integration via Model Context Protocol (MCP).

## Features

- Texas Hold'em poker implementation
- Web UI for human players
- AI bots via MCP integration
- Live game spectating

## Quick Start

```bash
./run.sh
```

App runs at `http://localhost:5001`

## MCP Setup

Project includes `opencode.json` configuration. Verify connection:

```bash
opencode mcp list
```

## MCP Tools

- `set_api_key` - Store API key
- `list_games` - List available games
- `create_game` - Create new game
- `join_game` - Join game
- `get_game_state` - Get current game state
- `make_action` - Make poker action (fold, check, call, raise, all_in)
- `start_game` - Start game (creator only)

## Documentation

- `MCP_SETUP.md` - Detailed MCP configuration
- `TESTING_GUIDE.md` - Testing instructions
- `EXAMPLES.md` - API examples
- `BOT_WORKFLOW.md` - Bot strategy examples

