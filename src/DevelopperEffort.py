import os
import subprocess
import json
from collections import defaultdict



def run_scc(repo_path):
    """
    Executes scc and return the TLOC by programming language for a repository
    """

    # Shorten list of programming languages since we struggles to compute data, so we considered to cut some programming languages
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
        print(f"Eror executing scc: {e}")
        return 0
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from scc: {e}")
        return 0

def checkout_commit(repo_path, commit_hash):
    """
    Checkout a specific commit in a directory
    """
    try:
        process = subprocess.run(
            ['git', 'checkout', commit_hash, '--force'],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if process.returncode != 0:
            print(f"Checkout error {commit_hash}: {process.stderr}")
            return False
        return True
    except subprocess.SubprocessError as e:
        print(f"Checkout error: {e}")
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
            print(f"Error getting previous commit: {result.stderr}")
            return None
        return result.stdout.strip()
    except subprocess.SubprocessError as e:
        print(f"Error with command git rev-parse: {e}")
        return None

def analyze_commit_effort(repo_path, commit_hash):
    """
    Compute TLOC for a specific commit
    """
    # Checkout refactoring commit
    if not checkout_commit(repo_path, commit_hash):
        return 0
        
    current_loc = run_scc(repo_path)
    
    # Obtain and checkout the previous commit
    previous_hash = get_previous_commit(repo_path, commit_hash)
    if not previous_hash:
        return 0
        
    if not checkout_commit(repo_path, previous_hash):
        return 0
        
    previous_loc = run_scc(repo_path)
    
    # Return absolute difference between commits
    return abs(current_loc - previous_loc)

def analyze_developer_effort(refactoring_results_path, repo_path, output_file):
    """
    Analyze dev effort from RMiner and save the results as a json file
    """
    try:
        with open(refactoring_results_path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error reading json file :  {refactoring_results_path}: {e}")
        return {'developer_effort': {}, 'refactoring_effort': {}}
    
    developer_effort = defaultdict(int)
    refactoring_effort = defaultdict(int)
    
    try:
        for commit in data.get('commits', []):
            commit_hash = commit.get('sha1')
            if not commit_hash:
                continue
            
            # Try different ways to get the author
            author = commit.get('authorName')
            if not author:
                author = commit.get('author', {}).get('name')
            if not author:
                author = commit.get('author')
                
            # If no author, try with git
            if not author:
                try:
                    result = subprocess.run(
                        ['git', 'show', '-s', '--format=%an', commit_hash],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    author = result.stdout.strip()
                except subprocess.SubprocessError:
                    author = 'Unknown'
                    
            if not author or author == '':
                author = 'Unknown'
                
            tloc = analyze_commit_effort(repo_path, commit_hash)
            developer_effort[author] += tloc
            
            for refactoring in commit.get('refactorings', []):
                refactoring_effort[refactoring['type']] += tloc

        if not checkout_commit(repo_path, 'HEAD'):
            print("Impossible to reset repo to HEAD")

        # Enregistrer les résultats dans le fichier JSON spécifié
        with open(output_file, 'w') as outfile:
            json.dump({
                'developer_effort': dict(developer_effort),
                'refactoring_effort': dict(refactoring_effort)
            }, outfile, indent=4)

        return {
            'developer_effort': dict(developer_effort),
            'refactoring_effort': dict(refactoring_effort)
        }
        
    except Exception as e:
        print(f"Error analyzing: {e}")
        checkout_commit(repo_path, 'HEAD')
        return {'developer_effort': {}, 'refactoring_effort': {}}

def run():
    repos_dir = "repos"
    results_dir = "results"
    
    for project in os.listdir(repos_dir):
        project_path = os.path.join(repos_dir, project)
        if not os.path.isdir(project_path):
            continue
            
        print(f"\nAnalysing effort for {project}...")
        
        refactoring_results = os.path.join(results_dir, project, "ListOfRefactoringCommits.json")
        if not os.path.exists(refactoring_results):
            print(f"No result for project {project}")
            continue
            
        output_json = os.path.join(results_dir, project, "DeveloperEffort_mining.json")
        results = analyze_developer_effort(refactoring_results, project_path, output_json)
        
        print(f"Results saved : {output_json}")

if __name__ == "__main__":
    run()