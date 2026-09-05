import itertools
import json
import logging
import os
import subprocess
import time
from multiprocessing import Pool, cpu_count
from file_utils import make_folder

bash_path = r"D:\\Programs\\Git\\bin\\bash.exe"

custom_env = os.environ.copy()
custom_env["MSYS_NO_PATHCONV"] = "1"
custom_env["MSYS2_ARG_CONV_EXCL"] = "*"


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


def get_dolos_lang(lang):
    return {
        'cpp': 'cpp', 'c': 'c', 'csharp': 'cs', 'golang': 'go',
        'java': 'java', 'javascript': 'javascript', 'python': 'python',
        'python3': 'python', 'rust': 'rust', 'kotlin': 'kotlin', 'dart': 'dart'
    }.get(lang.lower(), '')


def generate_report_for_question(args):
    """
    Worker function expecting a tuple of (question_id, lang).
    """
    question_id, lang = args
    mount_directory = "D:/Intrest/leetcode_query"
    submissions_folder = f"submissions/{lang}/{question_id}"
    
    if not os.path.exists(submissions_folder):
        logging.error("%s does not exist. Skipping %s/%s.", submissions_folder, lang, question_id)
        return f"Skipped: {lang}/{question_id} (missing folder)"

    # Ensure output directory exists per task safely
    make_folder(f"{mount_directory}/reports/{question_id}")

    try:
        print(f"[{lang}/{question_id}] -> Cleaning up previous reports...")
        subprocess.run(
            [bash_path, "-c", f"cd -P {mount_directory}/reports/{question_id} && rm -rf {lang}_report"],
            env=custom_env,
            check=False,  # Don't throw if folder doesn't exist yet
            capture_output=True
        )

        print(f"[{lang}/{question_id}] -> Executing Dolos analysis...")

        docker_command = [
            "docker", "run", "--init",
            "-w", "//dolos",
            "-v", f"{mount_directory}:/dolos",
            "ghcr.io/dodona-edu/dolos-cli:latest",
            "-l", get_dolos_lang(lang),
            "-i", f"templates/{lang}/{question_id}{get_extension(lang)}",
            "-M", "0.5",
            "-f", "csv", "-o", f"reports/{question_id}/{lang}_report",
            f"submissions/{lang}/{question_id}/*{get_extension(lang)}",
        ]

        final_execution_string = f'cd -P {mount_directory} && {" ".join(docker_command)}'

        subprocess.run(
            [bash_path, "-c", final_execution_string],
            env=custom_env,
            capture_output=True,
            text=True,
            check=True
        )

        print(f"[{lang}/{question_id}] -> Completed Successfully!")
        return f"Success: {lang}/{question_id}"

    except subprocess.CalledProcessError as e:
        print(f"[{lang}/{question_id}] Error (Exit Code {e.returncode}):\n{e.stderr}")
        return f"Failed: {lang}/{question_id}"


def sync_docker_image():
    print("-> Syncing Docker image...")
    subprocess.run(
        [bash_path, "-c", "docker pull ghcr.io/dodona-edu/dolos-cli:latest"],
        env=custom_env,
        check=True,
        capture_output=True
    )


if __name__ == "__main__":
    # Step 1: Sync image once centrally before starting workers
    sync_docker_image()

    # Step 2: Read dataset
    with open("data/parsed_submissions.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    valid_questions = set(submission["problem_number"] for submission in data)
    languages = set(submission['lang'] for submission in data)

    # Step 3: Create argument tuples for pool map
    tasks = list(itertools.product(valid_questions, languages))

    # Adjust workers based on CPU count (or limit manually to avoid high Docker overhead)
    max_workers = min(cpu_count(), 4)
    print(f"-> Starting multiprocessing pool with {max_workers} processes across {len(tasks)} tasks...")

    with Pool(processes=max_workers) as pool:
        results = pool.map(generate_report_for_question, tasks)

    print("\n=== Processing Complete ===")