import json
from pydriller import Repository
import os
import logging
import subprocess



# Reset git repo at its main branch
def reset_git_head(repo_path):
    try:
        # Try master brancj
        subprocess.run(['git', 'checkout', 'master'], 
                      cwd=repo_path, 
                      capture_output=True)
        return True
    except:
        try:
            # If no master, try main
            subprocess.run(['git', 'checkout', 'main'], 
                         cwd=repo_path, 
                         capture_output=True)
            return True
        except:
            try:
                # Finally, try default branch
                result = subprocess.run(['git', 'remote', 'show', 'origin'],
                                     cwd=repo_path,
                                     capture_output=True,
                                     text=True)
                
                for line in result.stdout.split('\n'):
                    if 'HEAD branch:' in line:
                        default_branch = line.split(':')[1].strip()
                        subprocess.run(['git', 'checkout', default_branch],
                                    cwd=repo_path,
                                    capture_output=True)
                        return True
            except:
                logging.error(f"Impossible de réinitialiser HEAD pour {repo_path}")
                return False

# Analyse difference between commits for a repo
def find_repo_diff(repo_path, result_dir_path):
    commits_data = []
    
    try:
        # Check if path exists and if it's a git repo
        if not os.path.exists(os.path.join(repo_path, '.git')):
            logging.error(f"No git repo found in {repo_path}")
            return
        
        # Reset HEAD
        if not reset_git_head(repo_path):
            logging.error(f"Unable to analyse {repo_path} - HEAD problem")
            return
            
        # Instanciate Repository object
        repo = Repository(
            path_to_repo=repo_path,
            order='reverse',  # Du plus récent au plus ancien
            include_refs=True  # Inclure toutes les références
        )
        
        logging.info(f"[Diff mining] : {repo_path}")
        commit_count = 0
        
        # Get all the commits
        all_commits = list(repo.traverse_commits())
        total_commits = len(all_commits)
        logging.info(f"Total amount of commits : {total_commits}")
        
        for commit in all_commits:
            try:
                # Check for parent
                if not commit.parents:
                    logging.debug(f"[Commit ignored (no parent)] : {commit.hash}")
                    continue
                
                # Get prievious commit hash
                if hasattr(commit.parents[0], 'hash'):
                    previous_commit_hash = commit.parents[0].hash
                else:
                    # If parents[0] is a string, its the hash itself
                    previous_commit_hash = commit.parents[0]
                
                modified_files = list(commit.modified_files)
                
                if not modified_files:
                    logging.debug(f"[Commit ignored (no touched file)] {commit.hash}")
                    continue
                
                # Get diffs statistics
                diff_stats = {
                    'added': sum(1 for file in modified_files if file.change_type.name == 'ADD'),
                    'deleted': sum(1 for file in modified_files if file.change_type.name == 'DELETE'),
                    'changed': len(modified_files),
                    'files': [f.filename for f in modified_files]
                }
                
                # Get diffs content
                diff_content = ''
                for modified_file in modified_files:
                    if modified_file.diff:
                        diff_content += modified_file.diff
                
                commit_info = {
                    'commit_hash': commit.hash,
                    'previous_commit_hash': previous_commit_hash,
                    'author': commit.author.name,
                    'date': commit.author_date.isoformat(),
                    'message': commit.msg,
                    'diff_stats': diff_stats,
                    'diff_content': diff_content
                }
                
                commits_data.append(commit_info)
                commit_count += 1
                
                if commit_count % 10 == 0:
                    logging.info(f"{commit_count}/{total_commits} commits analysed ...")
                
            except Exception as e:
                logging.error(f"[Error analysing commit] : {commit.hash} : {str(e)}")
                continue
        
        logging.info(f"[Repo analyse done] :  {commit_count} treadted.")
        
        # Create results directory if not existing
        #os.makedirs(result_dir_path, exist_ok=True)
        
        # Save results
        output_file = os.path.join(result_dir_path, 'CommitsDiff.json')
        with open(output_file, 'w', encoding='utf-8') as json_file:
            json.dump(commits_data, json_file, ensure_ascii=False, indent=4)
        
    except Exception as e:
        logging.error(f"[Error analysing repo] : {repo_path} : {str(e)}")
    finally:
        # Reset HEAD
        reset_git_head(repo_path)

def run():
    # Logging config
    logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
    repos_dir = "repos"
    results_dir = "results"
    
    if not os.path.exists(repos_dir):
        logging.error(f"Folder {repos_dir} doesn't exist")
        return
    
    for project in os.listdir(repos_dir):
        project_path = os.path.join(repos_dir, project)
        result_dir_path = os.path.join(results_dir, project)
        
        if os.path.isdir(project_path):
            logging.info(f"\n[Analysing project] : {project}")
            find_repo_diff(project_path, result_dir_path)

if __name__ == "__main__":
    run()