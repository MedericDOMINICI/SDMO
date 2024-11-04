import pandas as pd
import requests as r
import json
import os



# Check if url is 404
def check_url(url):
    try:
        response = r.get(url)
        if response.status_code != 200:
            return 200
        else:
            return response.status_code
    except r.exceptions.RequestException as e:
        print(f"request error")

def run():
    file_path = "sonar_measures.csv"

    # df without formating data
    init_df = pd.read_csv(file_path, dtype=str, encoding='utf-8', delimiter=',')

    # Get all the project names in a single column dataframe
    df = init_df.iloc[:, 0].str.split(',', expand=True).iloc[:,1].drop_duplicates()

    project_list = df.tolist()

    project_urls = {}


    i=0
    result_dir="results"

    for project in project_list:
        if project and  "_" in project:
            owner, name = project.split('_')
            url = f"https://github.com/{owner}/{name}"
            check_url = 200
            if check_url==200:
                project_urls[owner+"_"+name] = url
                i+=1
                print(f"{i}:[Added] : {url}")
        elif project:
            url = f"https://github.com/apache/{project}"
            check_url = 200
            if check_url==200:
                project_urls[project] = url
                i+=1
                print(f"{i}:[Added] : {url}")

    for project in project_urls:
        os.makedirs(result_dir+"/"+project)


    # project_list
    # project_urls


    jsonObject = json.dumps(project_urls, indent=4)

    with open ("repos_urls.json", "w") as outfile:
        outfile.write(jsonObject)

if __name__ == "__main__":
    run()