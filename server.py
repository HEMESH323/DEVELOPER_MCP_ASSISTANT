"""Developer Productivity MCP Server using FastMCP, SQLite, and Local Git."""
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("dev-productivity-assistant")

# Database setup for local tasks/bugs tracking
DB_PATH = Path(__file__).parent / "dev_tasks.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            status TEXT DEFAULT 'OPEN',
            created_at TEXT
        )
    """)
    # Insert dummy data if empty
    cursor.execute("SELECT COUNT(*) FROM tasks")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO tasks (title, status, created_at) VALUES (?, ?, ?)", [
            ("Fix async race condition in webhook listener", "OPEN", "2026-11-01"),
            ("Optimize LangGraph memory checkpointing", "IN_PROGRESS", "2026-11-05"),
            ("Write unit tests for custom tool router", "OPEN", "2026-11-07")
        ])
        conn.commit()
    conn.close()

init_db()

@mcp.tool()
def search_tasks(keyword: str) -> list[str]:
    """Search local engineering tasks/bugs by keyword in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, status, created_at FROM tasks WHERE title LIKE ?", (f"%{keyword}%",))
    rows = cursor.fetchall()
    conn.close()
    return [f"[ID: {r[0]}] {r[1]} (Status: {r[2]}, Date: {r[3]})" for r in rows]

@mcp.tool()
def add_task(title: str) -> str:
    """Add a new engineering task or bug report to the local database."""
    stamp = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (title, status, created_at) VALUES (?, 'OPEN', ?)", (title, stamp))
    conn.commit()
    conn.close()
    return f"Successfully added task: '{title}'"

@mcp.tool()
def get_recent_git_commits(limit: int = 5) -> list[str]:
    """Get the recent Git commit logs from the current local repository."""
    try:
        result = subprocess.run(
            ["git", "log", f"-n {limit}", "--oneline"],
            capture_output=True,
            text=True,
            check=True
        )
        commits = result.stdout.splitlines()
        return commits if commits else ["No git commits found in this directory."]
    except Exception as e:
        return [f"Error fetching git logs: {str(e)} (Ensure this is a git repository)"]

@mcp.tool()
def get_git_diff() -> str:
    """Get the git diff of current unstaged changes in the repository to review code modifications."""
    try:
        result = subprocess.run(
            ["git", "diff"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout if result.stdout.strip() else "No unstaged git changes found in the repository."
    except Exception as e:
        return f"Error fetching git diff: {str(e)}"

@mcp.tool()
def update_task_status(task_id: int, status: str) -> str:
    """Update the status of an engineering task (e.g., 'IN_PROGRESS', 'CLOSED', 'OPEN') by its ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (status.upper(), task_id))
    conn.commit()
    conn.close()
    return f"Successfully updated task ID {task_id} to status: {status.upper()}"

@mcp.resource("db://schema")
def database_schema() -> str:
    """Expose the database schema description as a readable resource."""
    return "SQLite Database: dev_tasks.db\nTable: tasks\nColumns: id (INTEGER), title (TEXT), status (TEXT), created_at (TEXT)"

@mcp.prompt()
def review_workflow() -> str:
    """A reusable prompt template that asks the model to audit pending tasks and git logs."""
    return "Review the database schema db://schema, search for open tasks, and summarize what engineering priorities need attention."

if __name__ == "__main__":
    mcp.run(transport="sse")