import os
import subprocess
import json
import csv
from collections import defaultdict


# Execute scc on a repo folder and return the total lignes of code for recognized programming languages
def run_scc(repo_path):

    PROGRAMMING_LANGUAGES = {
        'Java', 'Python', 'C++', 'C#', 'JavaScript', 'PHP', 'C', 'R', 'Swift', 
        'Go', 'Rust', 'Ruby', 'Kotlin', 'TypeScript'
    }

    try:
        result = subprocess.run(
            ['scc', '--no-cocomo', '--no-complexity', '--format', 'json', repo_path],
            capture_output=True,
            text=True,
            check=True
        )
        
        languages_data = json.loads(result.stdout)
        
        total_loc = 0
        for lang_data in languages_data:
            if lang_data.get('Name') in PROGRAMMING_LANGUAGES:
                total_loc += lang_data.get('Lines', 0)
                
        return total_loc
    except subprocess.CalledProcessError as e:
        print(f"[SCC error]: {e}")
        return 0
    except json.JSONDecodeError as e:
        print(f"[Json decoding scc error]: {e}")
        return 0

# Checkout a specific commit in the repo
def checkout_commit(repo_path, commit_hash):
    try:
        process = subprocess.run(
            ['git', 'checkout', commit_hash, '--force'],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if process.returncode != 0:
            print(f"[Commit checkout error] :  {commit_hash} : {process.stderr}")
            return False
        return True
    except subprocess.SubprocessError as e:
        print(f"[Checkout error] : {e}")
        return False

def get_previous_commit(repo_path, commit_hash):
    try:
        result = subprocess.run(
            ['git', 'rev-parse', f'{commit_hash}^1'],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            print(f"[Error getting previous commit hash] : {result.stderr}")
            return None
        return result.stdout.strip()
    except subprocess.SubprocessError as e:
        print(f"[git rev-parse error]: {e}")
        return None

def get_commit_author(repo_path, commit_hash):
    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--pretty=format:%an', commit_hash],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            print(f"[Error getting author] : {commit_hash} : {result.stderr}")
            return None
        return result.stdout.strip()
    except subprocess.SubprocessError as e:
        print(f"[Git log error]: {e}")
        return None

def analyze_commit_effort(repo_path, commit_hash):
    # Checkout refactoring commit
    if not checkout_commit(repo_path, commit_hash):
        return 0, None, None
        
    current_loc = run_scc(repo_path)
    
    # Get and checkout the previous commit
    previous_hash = get_previous_commit(repo_path, commit_hash)
    if not previous_hash:
        return 0, None, None
        
    if not checkout_commit(repo_path, previous_hash):
        return 0, None, None
        
    previous_loc = run_scc(repo_path)
    
    # Retrieve the author of the current commit
    author = get_commit_author(repo_path, commit_hash)
    
    return abs(current_loc - previous_loc), previous_hash, author

def analyze_developer_effort(refactoring_results_path, repo_path, output_csv_path):
    try:
        with open(refactoring_results_path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[Error reading json] : {refactoring_results_path} : {e}")
        return
    
    csv_data = []
    
    try:
        for commit in data.get('commits', []):
            commit_hash = commit.get('sha1')
            if not commit_hash:
                continue
            
            tloc, previous_hash, author = analyze_commit_effort(repo_path, commit_hash)
            
            csv_data.append({
                'refactoring_hash': commit_hash,
                'previous_hash': previous_hash if previous_hash else 'N/A',
                'author': author if author else 'Unknown',
                'TLOC': tloc
            })
        
        # Get back to head
        if not checkout_commit(repo_path, 'HEAD'):
            print("Impossible to reset to HEAD")
        
        with open(output_csv_path, 'w', newline='') as csvfile:
            fieldnames = ['refactoring_hash', 'previous_hash', 'author', 'TLOC']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for row in csv_data:
                writer.writerow(row)
            
    except Exception as e:
        print(f"[Error analysing] : {e}")
        checkout_commit(repo_path, 'HEAD')

def run():
    repos_dir = "repos"
    results_dir = "results"
    
    for project in os.listdir(repos_dir):
        project_path = os.path.join(repos_dir, project)
        if not os.path.isdir(project_path):
            continue
            
        print(f"\n[Analysing effort] : {project}...")
        
        refactoring_results = os.path.join(results_dir, project, "ListOfRefactoringCommits.json")
        if not os.path.exists(refactoring_results):
            print(f"[No results found] : {project}")
            continue
        
        # Créer le fichier CSV dans le même répertoire que les résultats
        output_csv = os.path.join(results_dir, project, "TLOC_mining.csv")
        analyze_developer_effort(refactoring_results, project_path, output_csv)

if __name__ == "__main__":
    run()
