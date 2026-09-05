import collections
import itertools
import json
from pathlib import Path
import logging
import os
import random
import sys
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

from playwright.sync_api import sync_playwright

from file_utils import make_folder, process_and_write
from leetcode_api import get_code_template_by_id, get_contest_question_slugs

load_dotenv()

# Get current date and time
now = datetime.now()

# Format as YYYY-MM-DD_HH-MM-SS (safe for file names)
file_name_timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler(
                            f"logs/query_pages_{file_name_timestamp}.log"),
                        logging.StreamHandler(sys.stdout)
                    ])


def get_top_100_submissions(contest_name: str):
    users = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        for i in range(1, 5):
            # go to url
            page.goto(
                f"https://leetcode.com/contest/{contest_name}/ranking/{i}/?region=global_v2")
            with page.expect_response(f"https://leetcode.com/contest/api/ranking/{contest_name}/?pagination={i}&region=global_v2") as response_info:
                # pprint.pp(response_info.value.json())
                users.append(response_info.value.json())
                # stuff we care about in this run, possibly get all the user submissions and their submission ids
                # we can look up the submission code via https://leetcode.com/submissions/detail
    return users


def check_if_in_login(request):
    if request.url.startswith("https://leetcode.com/accounts/login"):
        raise Exception(
            "You are not logged in. Please log in to LeetCode and try again.")


def get_submission_details(submission_id: int, page, valid_questions):
    # go to url
    page.goto(f"https://leetcode.com/submissions/detail/{submission_id}/")
    with page.expect_response(lambda response: response.url == "https://leetcode.com/graphql/" and response.request.post_data_json["operationName"] == "questionBySubmissionId") as response_info:
        body = response_info.value.json()
        if body is None:
            return "", "", False
        submission = body.get("data", {}).get("submissionDetails", {})
        if submission is None or submission.get("question", {}).get('questionId', -1) not in valid_questions:
            return "", "", False
    with page.expect_response(lambda response: response.url == "https://leetcode.com/graphql/" and response.request.post_data_json["operationName"] == "submissionDetails") as response_info:
        body = response_info.value.json()
        if body is None:
            return "", "", False
        submission = body.get("data", {}).get("submissionDetails", {})
    return submission.get("lang").get("name", ""), submission.get("code", ""), True


def login(page, context):
    page.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    # go to url
    page.goto(f"https://leetcode.com/accounts/login/")
    page.locator("#id_login").fill(os.getenv("LEETCODE_USERNAME"))
    page.locator("#id_password").fill(os.getenv("LEETCODE_PASSWORD"))
    page.get_by_role("button", name="Sign In").click()
    # Save storage state into the file.
    context.storage_state(path="state.json")
    time.sleep(5)


def parse_submissions(paged_submissions):
    parsed_submissions = []
    flattened_submissions = []
    for submissions in paged_submissions:
        flattened_submissions.append(submissions["total_rank"])
    # print(flattened_submissions)
    for user_submission in itertools.chain.from_iterable(flattened_submissions):
        for problem_number, submission_details in user_submission["submissions"].items():
            parsed_submissions.append(
                {
                    "contest_id": user_submission["contest_id"],
                    "user_slug": user_submission["user_slug"],
                    "score": user_submission["score"],
                    "rank": user_submission["rank"],
                    "problem_number": problem_number,
                    "lang": submission_details["lang"],
                    "fail_count": submission_details["fail_count"],
                    "submission_id": submission_details["submission_id"],
                }
            )
    return parsed_submissions


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
        'rust': 'rs'
    }
    return f".{extensions.get(lang.lower(), '')}"


def get_submissions_to_process():
    with open("data/parsed_submissions.json", "r", encoding="utf-8") as f:
        return [submission['submission_id'] for submission in json.load(f)]


if __name__ == "__main__":
    process_and_write("data/submissions.json",
                      get_top_100_submissions, os.getenv("LEETCODE_CONTEST_NAME"))

    process_and_write("data/parsed_submissions.json", parse_submissions,
                      json.load(open("data/submissions.json", "r", encoding="utf-8")))

    # get content questions
    contest_questions_slug, contest_questions_ids = get_contest_question_slugs(
        os.getenv("LEETCODE_CONTEST_NAME"))
    # get valid contest questions in submissions
    valid_questions = set(submission["problem_number"] for submission in json.load(open(
        "data/parsed_submissions.json", "r", encoding="utf-8")))
    logging.info("Valid questions are %s", ",".join(valid_questions))
    print(f"Valid questions are {','.join(valid_questions)}")
    print(f"Contest questions are {','.join(contest_questions_ids)}")
    assert set(contest_questions_ids) == valid_questions, "Mismatch between contest questions and valid questions in submissions"

    STATE_FOLDER = "state"
    SUBMISSIONS_FOLDER = "submissions"
    TEMPLATES_FOLDER = "templates"
    make_folder(STATE_FOLDER)
    make_folder(SUBMISSIONS_FOLDER)
    make_folder(TEMPLATES_FOLDER)

    languages = set(submission['lang'] for submission in json.load(
        open("data/parsed_submissions.json", "r", encoding="utf-8")))
    for lang in languages:
        lang_folder = os.path.join(SUBMISSIONS_FOLDER, lang)
        make_folder(lang_folder)
    for lang in languages:
        lang_folder = os.path.join(TEMPLATES_FOLDER, lang)
        make_folder(lang_folder)

    for title_slug, question_id in zip(contest_questions_slug, contest_questions_ids):
        for lang, code in get_code_template_by_id(title_slug, languages):
            with open(f"templates/{lang}/{question_id}{get_extension(lang)}", "w", encoding="utf-8") as f:
                f.write(code)

    # Handle state to get processed data.
    logging.info("Generate submissions list to process...")
    process_and_write("state/submissions_to_process.json",
                      get_submissions_to_process)
    process_and_write("state/submissions_processed.json", lambda: [])
    process_and_write("state/invalid_submissions.json", lambda: [])

    logging.info(
        "Loading submissions to process and already processed submissions...")
    sids_to_process = []
    with open("state/submissions_to_process.json", "r", encoding="utf-8") as f_to_process, open("state/submissions_processed.json", "r", encoding="utf-8") as f_processed:
        all_sids = set(json.load(f_to_process))
        processed_sids = set(json.load(f_processed))
        sids_to_process = list(all_sids - processed_sids)

    # submission_id to question_id map
    submission_id_to_question_id = {}
    with open("data/parsed_submissions.json", "r", encoding="utf-8") as f:
        parsed_submissions = json.load(f)
        submission_id_to_question_id = {
            submission['submission_id']: submission['problem_number'] for submission in parsed_submissions}

    print(f"Submissions left to process: {len(sids_to_process)}")
    submissions_processed = []
    invalid_submission_ids = []
    processed_stats = collections.Counter()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        login(page, context)
        count = 0
        BREAK_AT = 25
        try:
            for submission_id in sids_to_process:
                # to_sleep = random.randint(1, 3)
                # logging.info("Sleeping for %d", to_sleep)
                # time.sleep(to_sleep)
                logging.info(f"Processing submission ID: %d", submission_id)
                lang, code, is_valid = get_submission_details(
                    submission_id, page, valid_questions)
                if not is_valid:
                    logging.warning(
                        "Submission id %d is invalid", submission_id)
                    invalid_submission_ids.append(submission_id)
                    processed_stats["invalid_submission_ids"] += 1
                    submissions_processed.append(submission_id)
                    continue
                # need validation that its returning correct info like question no and user.
                lang_folder = os.path.join(SUBMISSIONS_FOLDER, lang, submission_id_to_question_id[submission_id])
                make_folder(lang_folder)
                with open(f"{lang_folder}/{submission_id}{get_extension(lang)}", "w", encoding="utf-8") as f:
                    f.write(code)
                # process the submission
                submissions_processed.append(submission_id)
                count += 1
                if count % BREAK_AT == 0:
                    sleep_time = random.randint(10, 25)
                    logging.info(
                        "Querying hit breakpoint, sleeping for %d", sleep_time)
                    time.sleep(sleep_time)
        except Exception as e:
            logging.error(
                "Error processing submission ID %d: %s", submission_id, e)
            logging.warning("Sent to login page")
            logging.info("commiting completed submissions")

    processed_stats["submissions_processed"] += len(submissions_processed)
    logging.info("Processed %d submissions", len(submissions_processed))

    logging.info("Updating state with processed submissions: %d",
                 len(submissions_processed))

    logging.info("Checking if counters.json exists...")
    if not Path("counters.json").exists():
        logging.info(
            "File not found. Creating counters.json...")
        with open("counters.json", "w", encoding="utf-8") as f:
            json.dump({}, f)
    else:
        logging.info(
            "File found. Skipping creation of counters.json.")
    logging.info("Attempting to update counters.json")
    with open("counters.json", "r+", encoding="utf-8") as f:
        counters = collections.Counter(json.load(f))
        counters.update(processed_stats)
        f.seek(0)
        json.dump(counters, f)
        f.truncate()
    logging.info("Updated counters.json")
    logging.info("Updating invalid_submissions.json")
    with open("state/invalid_submissions.json", "r+", encoding="utf-8") as f:
        invalid_subs = json.load(f)
        invalid_subs.extend(invalid_submission_ids)
        f.seek(0)
        json.dump(invalid_subs, f)
        f.truncate()
    logging.info("Updated invalid_submissions.json")
    logging.info("Updating submissions_processed.json")
    with open("state/submissions_processed.json", "r+", encoding="utf-8") as f:
        processed_sids = json.load(f)
        processed_sids.extend(submissions_processed)
        f.seek(0)
        json.dump(processed_sids, f)
        f.truncate()
    logging.info("Updated submissions_processed.json")

    logging.info("Done")
