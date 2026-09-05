import requests

LEETCODE_GRAPHQL_URL = "https://leetcode.com"


def get_contest_question_slugs(contest_slug) -> list[str]:
    """
    Given a LeetCode contest slug, fetches metadata for all questions 
    included in that contest, returning a list of their titleSlugs.
    """
    graphql_url = "https://leetcode.com/graphql"

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    # LeetCode's native GraphQL query for fetching full contest problem data
    contest_query = """
    query contestQuestionList($contestSlug: String!) {
        contestQuestionList(contestSlug: $contestSlug) {
            isAc
            credit
            title
            titleSlug
            titleCn
            questionId
            isContest
        }
    }
    """

    payload = {
        "query": contest_query,
        "operationName": "contestQuestionList",
        "variables": {"contestSlug": contest_slug}
    }

    try:
        response = requests.post(graphql_url, json=payload, headers=headers)
        if response.status_code != 200:
            print(f"Error: Received HTTP Status {response.status_code}")
            return []

        res_json = response.json()
    except Exception as e:
        print(f"Failed to fetch contest or decode JSON: {str(e)}")
        return []

    # Safe navigation into the nested contest schema dictionary
    questions = res_json.get("data", {}).get("contestQuestionList")
    if not questions:
        print(f"Error: Contest '{contest_slug}' not found or returned null.")
        return []

    print(f"--- Successfully Parsed: {len(questions)} questions ---")

    # Extract just the titleSlugs (or pass the full dictionaries if you need structural info)
    title_slugs = [q.get("titleSlug") for q in questions if q.get("titleSlug")]
    question_ids = [q.get("questionId")
                    for q in questions if q.get("questionId")]

    # Optional print statement to visually confirm mapping structures
    for q in questions:
        print(f"Q: {q.get('title')} -> slug: {q.get('titleSlug')}")

    return title_slugs, question_ids


def get_code_template_by_id(title_slug, target_languages: list[str]):
    """
    Given a LeetCode problem's titleSlug and a list of target languages, fetches the code templates
    for those languages from LeetCode's GraphQL API. Returns a dictionary mapping each language
    to its corresponding code template.
    """
    graphql_url = "https://leetcode.com/graphql"
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    # The exact same GraphQL query from the curl command
    query = """
    query questionEditorData($titleSlug: String!) {
        question(titleSlug: $titleSlug) {
            questionFrontendId
            title
            codeSnippets {
                lang
                langSlug
                code
            }
        }
    }
    """
    
    payload = {
        "query": query,
        "variables": {
            "titleSlug": title_slug
        }
    }

    try:
        response = requests.post(graphql_url, json=payload, headers=headers)
        if response.status_code != 200:
            print(f"Error: Received HTTP Status {response.status_code}")
            return
            
        res_json = response.json()
    except Exception as e:
        print(f"Failed to fetch data or decode JSON: {str(e)}")
        return
    question_data = res_json.get("data", {}).get("question")

    if not question_data:
        return f"Error: Could not retrieve data for slug '{title_slug}'."

    # Step 3: Extract the requested language snippet
    snippets = question_data.get("codeSnippets", [])
    for snippet in snippets:
        if snippet["langSlug"] in target_languages:
            print(
                f"--- Code Template for #{question_data.get('questionFrontendId')}: {question_data.get('title')} ({snippet['lang']}) ---\n")
            yield snippet["langSlug"], snippet["code"]

    return f"Error: Template for languages '{target_languages}' not found for this problem."
