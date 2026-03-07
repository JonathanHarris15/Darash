import subprocess
result = subprocess.run(["python", "-m", "pytest", "tests/scene/test_scene_interactions.py", "-v", "--tb=short"], capture_output=True, text=True)
with open("pytest_traceback.txt", "w", encoding="utf-8") as f:
    f.write(result.stdout)
    f.write("\nSTDERR:\n")
    f.write(result.stderr)
print(result.returncode)
