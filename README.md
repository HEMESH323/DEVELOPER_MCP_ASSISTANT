# 🚀 Developer Productivity MCP Server & AI Agent

An end-to-end implementation of an AI engineering workflow using the **Model Context Protocol (MCP)**, **FastMCP**, **SQLite**, **Local Git integration**, and the **Gemini Developer API**. 

This system enables autonomous AI agents to query local task management databases, inspect git commit history, review unstaged code diffs, and manage developer workflows over standard `stdio` or **Server-Sent Events (SSE)** transport layers.

---

## 🏗️ Architecture Overview

```text
[ Gemini Agent (Client) ] 
       │ (v1beta API & Function Declarations)
       ▼
[ MCP Client Session ] 
       │ (HTTP / SSE Transport)
       ▼
[ FastMCP Server ] ──┬──► [ SQLite Task Database (dev_tasks.db) ]
                     └──► [ Local Git Subprocess (Commits & Diffs) ]
              


