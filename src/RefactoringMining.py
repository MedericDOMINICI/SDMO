import os
import subprocess
import json
import time
from collections import defaultdict
from datetime import datetime
import numpy as np
from concurrent.futures import ProcessPoolExecutor

def find_analyzed_commits(result_dir_path):
    """Find commits that were already analyzed"""
    commit_set = set()
    invalid_json_files = []

    # Return empty values if the result directory does not exist yet
    if not os.path.exists(result_dir_path):
        return commit_set, invalid_json_files

    for file in os.listdir(result_dir_path):

        file_path = os.path.join(result_dir_path, file)
        
        with open(file_path, "r") as f:

            try:
                data = json.load(f)
                for commit in data["commits"]:
                    commit_set.add(commit["sha1"])
            except:
                invalid_json_files.append(file_path)

    return commit_set, invalid_json_files

def chunk_commits(repo_path, result_dir_path, chunk_size=100):
    """Split commits into chunks for parallel processing"""
    get_commits_command = ["git", "-C", repo_path, "rev-list", "--reverse", "HEAD"]
    result = subprocess.run(get_commits_command, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise Exception(f"Failed to get commits: {result.stderr}")

    # Find commits that were already analyzed. This will be empty if this is a new repository
    # If there are chunks, this will allow the program to get back to its previous state
    commit_set, invalid_json_files = find_analyzed_commits(result_dir_path)

    # Find all commit hashes from the output of the command above
    all_commits = result.stdout.strip().split('\n')

    # Filter out the commits that were already analyzed
    # as in, create a new list with only the commits not found in commit_set
    # This operation should preserve the order of the commits,
    # but might not do so if the program has previously failed to preserve the order
    commits = [x for x in all_commits if x not in commit_set]

    # Delete invalid JSON files that appear if the program was terminated while processing a chunk
    for file in invalid_json_files:
        print(f"Removing malformed JSON file {file} to reprocess it...")
        os.remove(file)

    print(f"Found {len(commits)} remaining commits")

    # Return a list containing the commit chunks
    return [commits[i:i + chunk_size] for i in range(0, len(commits), chunk_size)]
 
def run_refactoring_miner_chunk(args):
    counter, total_chunks, repo_path, result_dir_path, start_commit, end_commit = args
    REFACTORING_MINER_PATH = os.path.join(os.getcwd(), "RefactoringMiner-3.0.9", "bin", "RefactoringMiner.bat")
    
    chunk_output = os.path.join(os.getcwd(), result_dir_path, f"chunk_{start_commit[:8]}_{end_commit[:8]}.json")
    repo_path = os.path.join(os.getcwd(), repo_path)

    if os.path.exists(chunk_output):
        print(f"Skipping chunk {start_commit[:8]}-{end_commit[:8]} as it was already processed")
        return None

    command = [
        REFACTORING_MINER_PATH,
        "-bc",
        repo_path,
        start_commit,
        end_commit,
        "-json",
        chunk_output
    ]

    if not os.path.exists(os.path.dirname(chunk_output)):
        print(f"{os.path.dirname(chunk_output)} does not exist. Creating it...")
        os.makedirs(os.path.dirname(chunk_output))

    # Set the Xmx flag to something much less if your computer is not that powerful
    env = os.environ.copy()
    env["_JAVA_OPTIONS"] = "-Xmx2G"
    
    try:
        print(f"Processing chunk {start_commit[:8]}-{end_commit[:8]}")
        result = subprocess.run(command, capture_output=True, text=True, env=env)
        if result.returncode == 0:
            print(f"Chunk {start_commit[:8]}-{end_commit[:8]} finished ({counter}/{total_chunks})")
            return chunk_output
        else:
            print(f"Error processing chunk {start_commit[:8]}-{end_commit[:8]}: {result.stderr}")
            return None
    except Exception as e:
        print(command)
        print(f"Exception processing chunk {start_commit[:8]}-{end_commit[:8]}: {str(e)}")
        return None
 
def merge_json_results(json_files, output_file):

    print("Merging chunks...")

    merged_commits = []
    
    for json_file in json_files:

        if not json_file:
            continue

        if json_file and os.path.exists(json_file):
            with open(json_file, 'r') as f:
                data = json.load(f)
                merged_commits.extend(data.get('commits', []))
            os.remove(json_file)  # Clean up chunk files

    if not os.path.exists(os.path.dirname(output_file)):
        print(f"{os.path.dirname(output_file)} does not exist. Creating it...")
        os.makedirs(os.path.dirname(output_file))

    print(f"Dumping commits to {output_file}")

    with open(output_file, 'w+') as f:
        json.dump({'commits': merged_commits}, f)
 
def run_refactoring_miner(repo_path, result_dir_path):
    # Create chunks of commits
    commit_chunks = chunk_commits(repo_path, result_dir_path, chunk_size=100)

    total_chunks = len(commit_chunks)
    counter = 1
    
    # Prepare arguments for parallel processing
    chunk_args = []
    for i in range(total_chunks):
        start_commit = commit_chunks[i][0]
        end_commit = commit_chunks[i][-1]
        chunk_args.append((counter, total_chunks, repo_path, result_dir_path, start_commit, end_commit))
        counter += 1

    # Calculate optimal number of workers based on CPU cores and memory
    # 1 for now to let the script run in the background
    num_workers = 1 #min(os.cpu_count() or 1, 1)  # Limit to 4 parallel processes

    print(f"Processing {total_chunks} chunks with {num_workers} workers...")
    
    # Process chunks in parallel
    chunk_results = []
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        chunk_results = list(executor.map(run_refactoring_miner_chunk, chunk_args))
    
    # Merge results
    final_output = os.path.join(result_dir_path, "ListOfRefactoringCommits.json")
    merge_json_results(chunk_results, final_output)
 
# Rest of the code remains the same, starting from parse_refactoring_results...
 
 
def parse_refactoring_results(repo_path, json_file):
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    refactoring_counts = defaultdict(int)
    refactoring_times = []
    
    for commit in data['commits']:
        for refactoring in commit.get('refactorings', []):
            refactoring_counts[refactoring['type']] += 1
        
        #get_commit_timestamp_command = ["git", "log", "-1", f"--format=%ci {commit.get('sha1')}"]
        get_commit_timestamp_command = ["git", "-C", repo_path, "log", "-1", f"--format=%ci", commit.get('sha1')]
 
        result = subprocess.run(get_commit_timestamp_command, capture_output=True, text=True)
        # print(result)
 
        if result.returncode == 0:
            timestamp = result.stdout.strip()
            # print(timestamp)
            refactoring_times.append(timestamp)
        else:
            print(f"Error retrieving timestamp for commit {commit.get('sha1')}: {result.stderr}")
    
    return refactoring_counts, refactoring_times
 
def calculate_average_time_between_refactorings(times):
    if not times or len(times) < 2:
        return 0
 
    dates = [datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S %z') for date_str in times]
 
    dates.sort()
 
    # Computes consecutive differences
    time_deltas = [(dates[i+1] - dates[i]).total_seconds() for i in range(len(dates) - 1)]
 
    # Avg inter-refactoring time measured in seconds
    average_time_delta = int(round(np.mean(time_deltas),0))
 
    return average_time_delta
 
def analyze_project(project_path, result_dir_path):
    run_refactoring_miner(project_path, result_dir_path)
 
    json_file = os.path.join(result_dir_path, "ListOfRefactoringCommits.json")

    if not os.path.exists(json_file):
        print(f"File {json_file} not created")
        return {}, 0, 0

    print("Finished mining refactoring activity. Calculating refactoring results...")
    counts, times = parse_refactoring_results(project_path,json_file)
    total_refactorings = sum(counts.values())
    avg_time = calculate_average_time_between_refactorings(times)
 
    return counts, total_refactorings, avg_time
 
def run():
    
    repos_dir = "repos"
    results_dir = "results"

    with open("repos_names.json", "r") as f:
        project_names = json.load(f)

    for project in os.listdir(repos_dir):

        result_dir_path = os.path.join(results_dir, project)

        # Exclude projects that were already processed
        if os.path.exists(result_dir_path):
            if os.path.exists(os.path.join(result_dir_path, "ListOfRefactoringCommits.json")):
                continue

        if project not in project_names:
            continue

        project_path = os.path.join(repos_dir, project)
        result_dir_path = os.path.join(results_dir, project)

        if os.path.isdir(project_path):
            print(f"[Refactoring Mining] : {project}...")

            start = time.time()

            counts, total, avg_time = analyze_project(project_path, result_dir_path)

            project_results = {
                "counts": counts,
                "total": total,
                "avg_time": avg_time
            }

            out_path = os.path.join(result_dir_path, "RMining_results.json")
            print(f"Writing refactoring mining results of {project} to {out_path}")
            with open(out_path, "w+") as f:
                json.dump(project_results, f, indent=4)

            end = time.time()

            print(f"Processing {project} took {time.strftime('%H:%M:%S', time.gmtime(end - start))}")
 
if __name__ == "__main__":
    run()
