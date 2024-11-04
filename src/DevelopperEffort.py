import os
import subprocess
import json
from collections import defaultdict



def run_scc(repo_path):
    """
    Exécute scc sur le répertoire et retourne le total des lignes de code
    pour les langages de programmation reconnus.
    """

    # Liste des langages de programmation selon TIOBE
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
            # Utiliser 'Name' au lieu de 'Language'
            if lang_data.get('Name') in PROGRAMMING_LANGUAGES:
                # Utiliser 'Lines' pour le total des lignes
                total_loc += lang_data.get('Lines', 0)
                # print(f"Ajout de {lang_data.get('Lines', 0)} lignes pour {lang_data.get('Name')}")
                
        return total_loc
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de l'exécution de scc: {e}")
        return 0
    except json.JSONDecodeError as e:
        print(f"Erreur lors du décodage JSON de scc: {e}")
        return 0

def checkout_commit(repo_path, commit_hash):
    """
    Checkout un commit spécifique dans le répertoire.
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
            print(f"Erreur lors du checkout du commit {commit_hash}: {process.stderr}")
            return False
        return True
    except subprocess.SubprocessError as e:
        print(f"Erreur lors du checkout: {e}")
        return False

def get_previous_commit(repo_path, commit_hash):
    """
    Obtient le hash du commit précédent.
    """
    try:
        result = subprocess.run(
            ['git', 'rev-parse', f'{commit_hash}^1'],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            print(f"Erreur lors de la récupération du commit précédent: {result.stderr}")
            return None
        return result.stdout.strip()
    except subprocess.SubprocessError as e:
        print(f"Erreur lors de la commande git rev-parse: {e}")
        return None

def analyze_commit_effort(repo_path, commit_hash):
    """
    Calcule le TLOC (Total Lines of Code Changed) pour un commit spécifique.
    """
    # Checkout le commit de refactoring
    if not checkout_commit(repo_path, commit_hash):
        return 0
        
    current_loc = run_scc(repo_path)
    
    # Obtenir et checkout le commit précédent
    previous_hash = get_previous_commit(repo_path, commit_hash)
    if not previous_hash:
        return 0
        
    if not checkout_commit(repo_path, previous_hash):
        return 0
        
    previous_loc = run_scc(repo_path)
    
    # Retourner la différence absolue
    return abs(current_loc - previous_loc)

def analyze_developer_effort(refactoring_results_path, repo_path):
    """
    Analyse l'effort des développeurs à partir des résultats de RefactoringMiner.
    """
    try:
        with open(refactoring_results_path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Erreur lors de la lecture du fichier JSON {refactoring_results_path}: {e}")
        return {'developer_effort': {}, 'refactoring_effort': {}}
    
    developer_effort = defaultdict(int)
    refactoring_effort = defaultdict(int)
    
    try:
        for commit in data.get('commits', []):
            commit_hash = commit.get('sha1')
            if not commit_hash:
                continue
            
            # Essayer différentes façons de récupérer l'auteur
            author = commit.get('authorName')
            if not author:
                author = commit.get('author', {}).get('name')
            if not author:
                author = commit.get('author')
                
            # Si toujours pas d'auteur, essayer via git
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
            print("Attention: Impossible de revenir au commit HEAD")
        
        return {
            'developer_effort': dict(developer_effort),
            'refactoring_effort': dict(refactoring_effort)
        }
        
    except Exception as e:
        print(f"Erreur lors de l'analyse: {e}")
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
        
        refactoring_results = os.path.join(results_dir, project, "ListOfCommits.json")
        if not os.path.exists(refactoring_results):
            print(f"Pas de résultats trouvés pour {project}")
            continue
            
        results = analyze_developer_effort(refactoring_results, project_path)
        
        # Afficher les résultats
        print("\nEffort par développeur (TLOC):")
        print("-" * 40)
        for dev, tloc in results['developer_effort'].items():
            print(f"{dev:<30} | {tloc:>8}")
            
        print("\nEffort par type de refactoring (TLOC):")
        print("-" * 40)
        for refactoring_type, tloc in results['refactoring_effort'].items():
            print(f"{refactoring_type:<30} | {tloc:>8}")

if __name__ == "__main__":
    run()