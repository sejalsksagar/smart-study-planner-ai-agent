import sqlite3
from google.adk import Agent
from google.adk.agents import SequentialAgent

# =========================
# 🗄️ DATABASE (Cloud Run safe)
# =========================

conn = sqlite3.connect("/tmp/tasks.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task TEXT,
    day TEXT,
    priority TEXT,
    status TEXT
)
""")
conn.commit()

# =========================
# 🔧 TOOLS
# =========================

def add_task(task: str, day: str, priority: str = "medium") -> str:
    """Save task with priority"""
    cursor.execute(
        "INSERT INTO tasks (task, day, priority, status) VALUES (?, ?, ?, ?)",
        (task, day, priority, "pending")
    )
    conn.commit()
    return f"✅ Added: {task} ({priority}) on {day}"

def get_tasks() -> str:
    """Formatted task list"""
    cursor.execute("SELECT task, day, priority, status FROM tasks")
    rows = cursor.fetchall()

    if not rows:
        return "📭 No tasks yet."

    output = "📚 YOUR STUDY PLAN:\n\n"
    for task, day, priority, status in rows:
        output += f"📅 {day} | {task} | 🔥 {priority} | {status}\n"
    return output

def mark_done(task: str) -> str:
    cursor.execute(
        "UPDATE tasks SET status='done' WHERE task=?",
        (task,)
    )
    conn.commit()
    return f"✅ Marked '{task}' as completed"

def get_progress() -> str:
    cursor.execute("SELECT COUNT(*) FROM tasks")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status='done'")
    done = cursor.fetchone()[0]

    if total == 0:
        return "📊 No progress yet."

    percent = int((done / total) * 100)

    return f"""
📊 PROGRESS REPORT
-------------------
✅ Completed: {done}
📌 Total: {total}
📈 Progress: {percent}%
"""

def add_to_calendar(task: str, day: str) -> str:
    return f"📅 Scheduled '{task}' on {day}"

# =========================
# 🤖 AGENTS
# =========================

# 1️⃣ SMART PLANNER
planner = Agent(
    name="planner",
    model="gemini-2.5-flash",
    description="Creates smart study plan with priority.",
    instruction="""
Create a study plan.

Rules:
- Difficult topics → high priority
- Medium topics → medium priority
- Easy topics → low priority

Output STRICT format:
Day 1: Topic | priority
Day 2: Topic | priority

Example:
Day 1: Arrays | high
Day 2: OS basics | medium
"""
)

# 2️⃣ TASK + CALENDAR AGENT
task_agent = Agent(
    name="task_agent",
    model="gemini-2.5-flash",
    description="Stores and schedules tasks.",
    instruction="""
You will receive:

Day 1: Arrays | high

For each line:
1. Extract day, task, priority
2. Call:
   add_task(task, day, priority)
   add_to_calendar(task, day)
""",
    tools=[add_task, add_to_calendar]
)

# 3️⃣ WORKFLOW
study_workflow = SequentialAgent(
    name="study_workflow",
    sub_agents=[planner, task_agent]
)

# =========================
# 🎯 ROOT AGENT (UX IMPROVED)
# =========================

root_agent = Agent(
    name="study_planner_root",
    model="gemini-2.5-flash",
    description="Smart Study Planner Assistant",
    instruction="""
You are a friendly AI Study Planner 🤖

If user says hi/hello:
→ Respond with:
"Hi! I can help you:
📚 Create study plans
📅 Schedule tasks
📊 Track progress
✅ Mark tasks complete

Try saying:
'I have DSA exam in 5 days'"

If user asks to create a study plan:
→ Use study_workflow

If user asks:
- "show tasks" → use get_tasks
- "progress" → use get_progress
- "mark done <task>" → use mark_done

Always respond in a clean, formatted, user-friendly way.
""",
    tools=[get_tasks, get_progress, mark_done],
    sub_agents=[study_workflow]
)
