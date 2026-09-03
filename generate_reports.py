import logging
import os
import time

import subprocess
import shutil

bash_path = r"D:\\Programs\\Git\\bin\\bash.exe"

custom_env = os.environ.copy()
custom_env["MSYS_NO_PATHCONV"] = "1"
# Stops all argument rewriting across the board
custom_env["MSYS2_ARG_CONV_EXCL"] = "*"


# 2. Define the script logic using $1 and $2
# MSYS_NO_PATHCONV=1 tells Git Bash not to mutate the '//dolos' Docker path
bash_script = """
set -e

echo "=== Navigating to directory ==="
cd "$1"

echo "=== Step 2: Ensuring Docker image is up to date ==="
docker pull ghcr.io/dodona-edu/dolos-cli:latest

echo "=== Running Dolos Analysis via Docker ==="
docker run --init -w //dolos -v "$1:/dolos" ghcr.io/dodona-edu
/dolos-cli -l "$2" *."$3" > ../../reports/"$2".txt
"""

get_extension = lambda lang: f".{{'cpp': 'cpp', 'c': 'c', 'csharp': 'cs', 'golang': 'go', 'java': 'java', 'javascript': 'js', 'python': 'py', 'python3': 'py', 'rust': 'rs'}.get(lang.lower(), '') }"

def get_dolos_lang(lang): return {'cpp': 'cpp', 'c': 'c', 'csharp': 'cs', 'golang': 'go', 'java': 'java', 'javascript': 'javascript', 'python': 'python', 'python3': 'python', 'rust': 'rust'}.get(lang.lower(), '')


if __name__ == "__main__":
    for lang in ["cpp", "c", "csharp", "golang", "java", "javascript", "python", "python3", "rust"]:
        lang_folder = f"D:/Intrest/leetcode_query/submissions/{lang}"
        if not os.path.exists(lang_folder):
            logging.error("%s does not exist. skipping.", lang_folder)
            continue

        try:
            # Step 1: Force pull the image via a pure array execution to safeguard the naming format
            print(f"-> Syncing Docker image for {lang}...")
            subprocess.run(
                [bash_path, "-c", "docker pull ghcr.io/dodona-edu/dolos-cli:latest"],
                env=custom_env,
                check=True,
                capture_output=True
            )

            print(f"-> Cleaning up any previous Dolos reports for {lang}...")
            subprocess.run(
                [bash_path, "-c",
                    f"cd -P D:/Intrest/leetcode_query/reports && rm -rf {lang}_report"],
                env=custom_env,
                check=True,
                capture_output=True
            )

            # Step 2: Use direct array arguments to call the run statement cleanly
            print(
                f"-> Executing Dolos analysis inside your repository: {lang}...")

            # We build the precise command array so Git Bash can't break down the text components
            docker_command = [
                "docker", "run", "--init",
                "-w", "//dolos",
                "-v", f"{lang_folder}:/dolos",
                "ghcr.io/dodona-edu/dolos-cli:latest",
                "-l", get_dolos_lang(lang),
                "-f csv", "-o", f"{lang}_report",
                "-M 0.3",  # If a token if it appears in more than 30% of the submissions, it is ignored
                f"*{get_extension(lang)}",
            ]

            # We chain 'cd' and our safe docker command array together using a clean string join
            final_execution_string = f'cd -P "{lang_folder}" && {" ".join(docker_command)}'

            result = subprocess.run(
                [bash_path, "-c", final_execution_string],
                env=custom_env,
                capture_output=True,
                text=True,
                check=True
            )

            result = subprocess.run(
                [bash_path, "-c",
                    f"mv {lang_folder}/{lang}_report D:/Intrest/leetcode_query/reports/{lang}_report"],
                env=custom_env,
                capture_output=True,
                text=True,
                check=True
            )

            print("\nExecution Completed Successfully!")
            print(result.stdout)

        except subprocess.CalledProcessError as e:
            # Print error details if the Docker command or cd fails
            print(f"Error occurred (Exit Code {e.returncode}):")
            print(e.stderr)
