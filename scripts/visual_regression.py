import os
import subprocess
import sys
import glob

def run_visual_regression():
    """
    Discovers all lab runners and executes them with the --snapshot flag
    to update the visual history in docs/snapshots/.
    """
    print("=== Starting Visual Regression Snapshot Update ===")
    
    # Ensure snapshots directory exists
    os.makedirs("docs/snapshots", exist_ok=True)
    
    # Find all run_*.py scripts in scripts/lab/
    lab_dir = os.path.join("scripts", "lab")
    runners = glob.glob(os.path.join(lab_dir, "run_*.py"))
    
    if not runners:
        print("No lab runners found in scripts/lab/")
        return

    success_count = 0
    for runner in runners:
        basename = os.path.basename(runner)
        print(f"Capturing snapshot for: {basename}...")
        
        try:
            # Run the lab script with the snapshot flag
            # We use sys.executable to ensure we use the same python environment
            result = subprocess.run(
                [sys.executable, runner, "--snapshot"],
                capture_output=True,
                text=True,
                timeout=30  # Safety timeout
            )
            
            if result.returncode == 0:
                print(f"  [SUCCESS] {result.stdout.strip()}")
                success_count += 1
            else:
                print(f"  [ERROR] Failed to capture snapshot for {basename}")
                print(f"  Output: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            print(f"  [TIMEOUT] {basename} took too long.")
        except Exception as e:
            print(f"  [EXCEPTION] {e}")

    print(f"\n=== Visual Regression Complete: {success_count}/{len(runners)} snapshots updated ===")

if __name__ == "__main__":
    run_visual_regression()
