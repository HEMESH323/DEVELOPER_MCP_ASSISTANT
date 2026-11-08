"""MCP Client powered by Gemini API (Free tier compatible).

Usage:
 python client.py tools
 python client.py demo
 python client.py ask "What tasks do we have about LangGraph?"
"""
import asyncio
import os
import sys
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp import ClientSession
from mcp.client.sse import sse_client

PARAMS = StdioServerParameters(command=sys.executable, args=["server.py"])

def text_of(result) -> str:
    return "\n".join(c.text for c in result.content if hasattr(c, "text"))

async def list_tools(session):
    tools = await session.list_tools()
    print("Available MCP Tools:")
    for t in tools.tools:
        print(f"  - {t.name}: {t.description}")

async def demo(session):
    print("Running direct tool demo (no AI model):")
    r = await session.call_tool("search_tasks", {"keyword": "LangGraph"})
    print("search_tasks('LangGraph') ->", text_of(r))
    
    r = await session.call_tool("get_recent_git_commits", {"limit": 3})
    print("get_recent_git_commits(3) ->", text_of(r))

async def ask(session, question):
    # Initialize Google GenAI client (reads GEMINI_API_KEY from environment)
    ai_client = genai.Client(http_options={"api_version": "v1beta"})
    # Using gemini-2.5-flash as the fast, free-tier default model
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # 1. Fetch tools from MCP server
    listed = await session.list_tools()
    
    # 2. Convert MCP tools to Gemini FunctionDeclarations
    gemini_tools = []
    for t in listed.tools:
        # Simple schema conversion for Gemini
        schema = t.inputSchema or {"type": "OBJECT", "properties": {}}
        gemini_tools.append(
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name=t.name,
                        description=t.description or "",
                        parameters=schema
                    )
                ]
            )
        )

    # 3. Start chat conversation with Gemini
    chat = ai_client.chats.create(
        model=model_name,
        config=types.GenerateContentConfig(
            tools=gemini_tools,
            temperature=0.2
        )
    )

    print(f"User Question: {question}\n")
    response = chat.send_message(question)

    # 4. Handle tool execution loop if Gemini decides to call a tool
    while response.function_calls:
        for function_call in response.function_calls:
            print(f"[Gemini Tool Call] {function_call.name}({function_call.args})")
            
            # Execute tool through MCP session
            out = await session.call_tool(function_call.name, function_call.args)
            tool_output_text = text_of(out)
            print(f"[Tool Output]: {tool_output_text}\n")

            # Send tool results back to Gemini
            response = chat.send_message(
                types.Part.from_function_response(
                    name=function_call.name,
                    response={"result": tool_output_text}
                )
            )

    # 5. Print final model response
    if response.text:
        print("Gemini Final Answer:")
        print(response.text)

async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "tools"
    
    # Connect to the MCP server running over HTTP/SSE
    async with sse_client("http://localhost:8000/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            if mode == "tools":
                await list_tools(session)
            elif mode == "demo":
                await demo(session)
            elif mode == "ask":
                await ask(session, " ".join(sys.argv[2:]))

asyncio.run(main())