'''
[Release Note]
2026/2/11 version 1 created by M.Ishida
First Release Version
2026/2/13 version 2 created by M.Ishida
Add Function "Export Monthly Schedule to Supabase"
Add Function "Remind Schedule 1 Week Before"
'''

import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent

# 実行対象
TARGET_SCRIPTS = [
    # BASE_DIR / "schedule_manager/ScheduleManager.py",
    BASE_DIR / "one_week_reminder/OneWeekReminder.py",
    # BASE_DIR / "test1_AutoPost.py",
    # BASE_DIR / "target2.py",
    # BASE_DIR / "target3.py",
]

SUCCESS_SCRIPT = BASE_DIR / "success.py"
FAILED_SCRIPT  = BASE_DIR / "failed.py"

def run_script(path: Path):
    result = subprocess.run(
        [sys.executable, str(path)],
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr

def main():
    failures = []

    for script in TARGET_SCRIPTS:
        if not script.exists():
            failures.append({
                "script": script.name,
                "returncode": "NOT_FOUND"
            })
            continue

        rc, out, err = run_script(script)

        if rc != 0:
            failures.append({
                "script": script.name,
                "returncode": rc,
                "stderr": err.strip()
            })

    # 結果分岐
    if failures:
        args = [sys.executable, str(FAILED_SCRIPT), str(failures)]
        subprocess.run(args)
        sys.exit(1)
    else:
        subprocess.run([sys.executable, str(SUCCESS_SCRIPT)])
        sys.exit(0)

if __name__ == "__main__":
    main()
