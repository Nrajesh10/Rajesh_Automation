(fixed code here)
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    fixed_output = response.choices[0].message.content.strip()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_file = FIX_HISTORY_DIR / f"ai_fix_phase4_{timestamp}.txt"
    history_file.write_text(fixed_output, encoding="utf-8")

    current_file, buffer = None, []
    for line in fixed_output.splitlines():
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

def controller_loop(max_attempts=7, min_lint=7.0):
    attempt = 1
    while attempt <= max_attempts:
        print(f"\n=== Attempt {attempt} ===")

        code, test_output = tester_agent()
        if code != 0:
            print("❌ Tests failed, running fixer...\n", test_output)
            fixer_agent(test_output)
            attempt += 1
            time.sleep(1)
            continue

        print("✅ Tests passed!")

        lint_score, lint_output = reviewer_agent()
        print(f"🎯 Lint score: {lint_score}/10")

        if lint_score >= min_lint:
            print(f"🏆 SUCCESS: Tests + Lint passed (score {lint_score}) in {attempt} attempt(s)!")
            return True
        else:
            print("⚠️ Lint issues found, sending fixer...")
            fixer_agent("", lint_output)
            attempt += 1
            time.sleep(1)

    print("💀 FAILURE: Could not fix after max attempts.")
    return False

if __name__ == "__main__":
    controller_loop()
