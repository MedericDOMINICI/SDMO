import json
import subprocess
import os

def clone_repo(repo_name, repo_url, target_dir, result_dir):
    try:
        repo_dir = os.path.join(target_dir, repo_name)
        print(f"Cloning {repo_name} into {repo_dir}")
        
        subprocess.run(["git", "clone", "--single-branch", repo_url, repo_dir], check=True)

    except subprocess.CalledProcessError as e:
        print(f"Failed to clone {repo_name}: {e}")

def load_repos_from_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)
    
# Clone all the repos
def clone_all_repos(json_file, target_dir, result_dir, amount_of_repo=None, starting_repo=None):
    repos = load_repos_from_json(json_file)
    if amount_of_repo and starting_repo:
        # select only the repos bewteen "start_repo" and "amount_of_repo" firsts repos
        repos = dict(list(repos.items())[starting_repo:starting_repo+amount_of_repo])
    os.makedirs(target_dir, exist_ok=True)  # Create 'repos' folder if not existing
    for repo_name, repo_url in repos.items():
        clone_repo(repo_name, repo_url, target_dir, result_dir)

def run():
    json_file = "repos_urls.json"  # URL storage file
    target_directory = "repos"  # Folder where repos will be cloned
    result_dir="results"


    # clone_all_repos(json_file, target_directory, result_dir, 3,1)
    clone_all_repos(json_file, target_directory, result_dir)

if __name__ == "__main__":
    run()