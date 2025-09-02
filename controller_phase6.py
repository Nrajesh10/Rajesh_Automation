# controller_phase6.py
# Phase 6: Smarter Controller with GitHub Auto Commit + Push

import subprocess
import time
from pathlib import Path
import os
import json
from datetime import datetime
from openai import OpenAI

# === Paths ===
PROJECT_DIR = Path(".")
FIX_HISTORY_DIR = PROJECT_DIR / "fix_history"
FIX_HISTORY_DIR.mkdir(exist_ok=True)
METRICS_FILE = FIX_HISTORY_DIR / "metrics.json"

# === OpenAI Client ===
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ---------------------------
# AGENT: Tester
# ---------------------------
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

# ---------------------------
# AGENT: Reviewer (Lint)
# ---------------------------
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

# ---------------------------
# Collect project code
# ---------------------------
def collect_project_code():
    return [
        f for f in PROJECT_DIR.glob("*.py")
        if f.name not in ["controller.py", "controller_phase6.py"]
        and not f.name.startswith("test_")
    ]

# ---------------------------
# AGENT: Fixer
# ---------------------------
def fixer_agent(error_log, lint_log=None):
    code_files = collect_project_code()
    file_contents = "\n\n".join(
        [f"### {f.name}\n{f.read_text(encoding='utf-8')}" for f in code_files]
    )

    lint_part = f"\nHere is the lint report:\n{lint_log}" if lint_log else ""
    error_part = f"\nHere is the error log:\n{error_log}" if error_log else ""

    prompt = f"""
You are a strict Python fixer AI.

Here are the project files:
{file_contents}

{error_part}
{lint_part}

Fix the code so that:
1. All tests pass.
2. Lint score >= 7.0.
3. Do NOT include markdown fences.
4. Do NOT add commentary.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    fixed_output = response.choices[0].message.content.strip()

    # Save history
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_file = FIX_HISTORY_DIR / f"ai_fix_phase6_{timestamp}.txt"
    history_file.write_text(fixed_output, encoding="utf-8")

    # Apply fixes
    current_file, buffer = None, []
    for line in fixed_output.splitlines():
        if line.strip().startswith("```"):
            continue
        if line.startswith("### "):
            if current_file and buffer:
                Path(current_file).write_text("\n".join(buffer).rstrip() + "\n", encoding="utf-8")
            current_file = line.replace("### ", "").strip()
            buffer = []
        else:
            buffer.append(line)

    if current_file and buffer:
        Path(current_file).write_text("\n".join(buffer).rstrip() + "\n", encoding="utf-8")

    return True

# ---------------------------
# Metrics Logger
# ---------------------------
def log_metrics(attempt, tests_passed, lint_score, status, commit_hash=None):
    entry = {
        "attempt": attempt,
        "tests": "passed" if tests_passed else "failed",
        "lint_score": lint_score,
        "status": status,
        "commit_hash": commit_hash,
        "timestamp": datetime.now().isoformat()
    }

    data = []
    if METRICS_FILE.exists():
        try:
            data = json.loads(METRICS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = []

    data.append(entry)
    METRICS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

# ---------------------------
# Git Agent
# ---------------------------
def git_commit_and_push(message="Auto commit by controller"):
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", message], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            text=True,
            capture_output=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None

# ---------------------------
# Metrics Summary
# ---------------------------
def show_metrics_board():
    if not METRICS_FILE.exists():
        print("📊 No metrics yet.")
        return
    try:
        data = json.loads(METRICS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("⚠️ Metrics file corrupted.")
        return

    total_runs = len(data)
    successes = sum(1 for d in data if d["status"] == "success")
    avg_lint = round(sum(d.get("lint_score", 0) for d in data) / total_runs, 2)

    print("\n📊 === METRICS SUMMARY ===")
    print(f"🔢 Total Runs: {total_runs}")
    print(f"✅ Successes: {successes}")
    print(f"❌ Failures: {total_runs - successes}")
    print(f"🎯 Average Lint Score: {avg_lint}/10")
    print("🕒 Last Run:", data[-1]["timestamp"])
    if data[-1].get("commit_hash"):
        print("📌 Last Commit:", data[-1]["commit_hash"])

# ---------------------------
# Controller Loop
# ---------------------------
def controller_loop(max_attempts=7, min_lint=7.0):
    attempt = 1
    while attempt <= max_attempts:
        print(f"\n=== Attempt {attempt} ===")

        # Step 1: Tests
        code, test_output = tester_agent()
        if code != 0:
            print("❌ Tests failed!\n", test_output)
            fixer_agent(test_output)
            log_metrics(attempt, False, 0.0, "fixing tests")
            attempt += 1
            time.sleep(1)
            continue

        print("✅ Tests passed!")

        # Step 2: Lint
        lint_score, lint_output = reviewer_agent()
        print(f"🎯 Lint score: {lint_score}/10")

        if lint_score >= min_lint:
            print(f"🏆 SUCCESS: Tests + Lint passed (score {lint_score})!")
            commit_hash = git_commit_and_push("Auto commit: success")
            log_metrics(attempt, True, lint_score, "success", commit_hash)
            show_metrics_board()
            return True
        else:
            print("⚠️ Lint issues found, fixing...")
            fixer_agent("", lint_output)
            log_metrics(attempt, True, lint_score, "fixing lint")
            attempt += 1
            time.sleep(1)

    print("💀 FAILURE: Max attempts reached.")
    log_metrics(attempt, False, 0.0, "failure")
    show_metrics_board()
    return False

# ---------------------------
if __name__ == "__main__":
    controller_loop()
