import requests
import json
import time
import os

def check_github_its(owner, repo, token):
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {
        "Authorization": f"token {token}"
    }
    response = requests.get(url, headers=headers)

    # Si la réponse est vide ou retourne un code 404, le projet n'utilise pas les issues GitHub
    if response.status_code == 404:
        print(f"{repo} using github as ITS.")
        return False
    elif response.status_code == 200 and response.json():
        print(f"{repo} not using gitHub as ITS.")
        return True
    else:
        print(f"[Error getting ITS info] : {repo}.")
        return False

def mine_github_issues(owner, repo, token, results_dir):
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {
        "Authorization": f"token {token}"
    }
    issues_data = []
    page = 1

    while True:
        params = {"state": "all", "per_page": 100, "page": page}
        response = requests.get(url, headers=headers, params=params)

        # Check limit rate of api
        if response.status_code == 403 and "X-RateLimit-Remaining" in response.headers and response.headers["X-RateLimit-Remaining"] == "0":
            reset_time = int(response.headers["X-RateLimit-Reset"])
            sleep_time = reset_time - int(time.time()) + 1
            print(f"Rate limit exceeded. Sleeping for {sleep_time} seconds...")
            time.sleep(sleep_time)
            continue
        
        if response.status_code != 200 or not response.json():
            break

        issues_data.extend(response.json())
        page += 1

        # Exit if less than 100 issues, wich means it was the last page
        if len(response.json()) < 100:
            break

    with open(f'{results_dir}/{owner}_{repo}/{repo}_issues.json', 'w') as f:
        json.dump(issues_data, f, indent=4)
    
    print(f"[Issues extracted] : {repo}.")
    return issues_data

def run():
    # Github token
    token = ""

    results_dir="results"

    for project in os.listdir(results_dir):

        owner, repo = project.split('_')
            
        if check_github_its(owner, repo, token):
            issues_data = mine_github_issues(owner, repo, token, results_dir)
            print(f"Issues mined: {len(issues_data)}")
        else:
            print("No issues found")

if __name__ == "__main__":
    run()
