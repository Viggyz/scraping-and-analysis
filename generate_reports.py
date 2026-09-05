import itertools
import json
import logging
import os
import time

import subprocess
import shutil

from file_utils import make_folder

bash_path = r"D:\\Programs\\Git\\bin\\bash.exe"

custom_env = os.environ.copy()
custom_env["MSYS_NO_PATHCONV"] = "1"
# Stops all argument rewriting across the board
custom_env["MSYS2_ARG_CONV_EXCL"] = "*"

# Force pull the image via a pure array execution to safeguard the naming format
print(f"-> Syncing Docker image...")
subprocess.run(
    [bash_path, "-c", "docker pull ghcr.io/dodona-edu/dolos-cli:latest"],
    env=custom_env,
    check=True,
    capture_output=True
)

# Define the script logic using $1 and $2
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


def get_extension(lang):
    extensions = {
        'cpp': 'cpp',
        'c': 'c',
        'csharp': 'cs',
        'golang': 'go',
        'java': 'java',
        'javascript': 'js',
        'python': 'py',
        'python3': 'py',
        'rust': 'rs',
        'kotlin': 'kt',
        'dart': 'dart',
    }
    return f".{extensions.get(lang.lower(), '')}"


def get_dolos_lang(lang): return {'cpp': 'cpp', 'c': 'c', 'csharp': 'cs', 'golang': 'go', 'java': 'java',
                                  'javascript': 'javascript', 'python': 'python', 'python3': 'python', 'rust': 'rust', 'kotlin': 'kotlin', 'dart': 'dart'}.get(lang.lower(), '')


def generate_report_for_question(question_id, lang):
    mount_directory = "D:/Intrest/leetcode_query"
    submissions_folder = f"submissions/{lang}/{question_id}"
    templates_folder = f"templates/{lang}"
    template_file = f"templates/{lang}/{question_id}{get_extension(lang)}"
    if not os.path.exists(submissions_folder):
        logging.error("%s does not exist. skipping.", submissions_folder)
        return

    try:
        print(f"-> Cleaning up any previous Dolos reports for {lang}/{question_id}...")
        subprocess.run(
            [bash_path, "-c",
             f"cd -P D:/Intrest/leetcode_query/reports/{question_id} && rm -rf {lang}_report"],
            env=custom_env,
            check=True,
            capture_output=True
        )

        # Step 1: Use direct array arguments to call the run statement cleanly
        print(
            f"-> Executing Dolos analysis inside your repository: {lang}/{question_id}...")

        # We build the precise command array so Git Bash can't break down the text components
        docker_command = [
            "docker", "run", "--init",
            "-w", "//dolos",
            "-v", f"{mount_directory}:/dolos",
            "ghcr.io/dodona-edu/dolos-cli:latest",
            "-l", get_dolos_lang(lang),
            "-i", f"templates/{lang}/{question_id}{get_extension(lang)}",
            "-M", "0.5",
            "-f csv", "-o", f"reports/{question_id}/{lang}_report",
            f"submissions/{lang}/{question_id}/*{get_extension(lang)}",
        ]

        # We chain 'cd' and our safe docker command array together using a clean string join
        final_execution_string = f'cd -P {mount_directory} && {" ".join(docker_command)}'

        result = subprocess.run(
            [bash_path, "-c", final_execution_string],
            env=custom_env,
            capture_output=True,
            text=True,
            check=True
        )

        result = subprocess.run(
            [bash_path, "-c",
                f"mv reports/{question_id}/{lang}_report {mount_directory}/reports/{question_id}/{lang}_report"],
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


if __name__ == "__main__":
    valid_questions = set(submission["problem_number"] for submission in json.load(open(
        "data/parsed_submissions.json", "r", encoding="utf-8")))
    languages = set(submission['lang'] for submission in json.load(
        open("data/parsed_submissions.json", "r", encoding="utf-8")))
    for question, lang in itertools.product(valid_questions, languages):
        make_folder(f"D:/Intrest/leetcode_query/reports/{question}")
        generate_report_for_question(question, lang)
