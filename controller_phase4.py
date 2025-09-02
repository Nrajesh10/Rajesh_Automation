import subprocess
import time
from pathlib import Path
import os
from datetime import datetime
from openai import OpenAI

PROJECT_DIR = Path(".")
FIX_HISTORY_DIR = PROJECT_DIR / "fix_history"
FIX_HISTORY_DIR.mkdir(exist_ok=True)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def coder_agent(prompt="Write or fix Python code."):
    return prompt

def tester_agent():
    try:
        result = subprocess.run(
            ["pytest", "-q"],
            text=True,
            capture_output=True,
            timeout=20
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return 1, "❌ Tests timed out"

def reviewer_agent():
    try:
        result = subprocess.run(
            ["pylint", "ai_code.py", "--score=y", "--disable=R,C"],
            text=True,
            capture_output=True,
            timeout=20
        )
        score = 0.0
        for line in result.stdout.splitlines():
            if "rated at" in line:
                try:
                    score = float(line.split("rated at")[1].split("/")[0].strip())
                except ValueError:
                    score = 0.0
        return score, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return 0.0, "❌ Lint timed out"

def collect_project_code():
    return [
        f for f in PROJECT_DIR.glob("*.py")
        if f.name not in ["controller.py", "controller_phase4.py"]
        and not f.name.startswith("test_")
    ]

def fixer_agent(error_log, lint_log=None):
    code_files = collect_project_code()

    file_contents = "\n\n".join(
        [f"### {f.name}\n{f.read_text(encoding='utf-8')}" for f in code_files]
    )

    lint_part = f"\nHere is the lint report:\n{lint_log}" if lint_log else ""

    prompt = f"""
You are a strict Python fixer AI.

Here are the project files:
{file_contents}

Here is the error log:
{error_log}
{lint_part}

Fix the code so that:
1. All tests pass.
2. Lint score >= 7.0 (PEP8 clean).
3. Do NOT include markdown fences.
4. Ensure every function has a return if expected.
5. Replace undefined variables with correct ones.

Output corrected code, file by file, in this format:
