from textops import find, cat, grepci
import os
from pathlib import Path
import glob
import requests

from opensafely.check import RESTRICTED_DATASETS, PERMISSIONS_URL,  get_datasource_permissions 

from repoupdater import BASE_PATH


def check():
    permissions = get_datasource_permissions(PERMISSIONS_URL)

    restricted = {}
    for dataset in RESTRICTED_DATASETS:
        restricted[dataset.name] = {"allowed": [], "using": []}
        restricted[dataset.name]["allowed"] = sorted(
            [
                k.replace("opensafely/", "") for k, v in permissions.items() 
                if dataset.name in v["allow"]
            ]
        )
        function_names = [
            f"\.{fname}" for fname in dataset.cohort_extractor_function_names
        ]
    
        for filep in sorted(glob.glob(os.path.join(BASE_PATH, "*"))):
            found = 0
            path = Path(filep)
            for ext in ["py", "sql", "ipynb"]:
                if ext == "py":
                    # in python files, check for `tablename.` usage
                    table_names_to_search = [
                        f"{fname}\." for fname in dataset.ehrql_table_names
                    ]
                else:
                    table_names_to_search = dataset.ehrql_table_names
                found = filep | find(f'*.{ext}') | cat() | grepci("|".join(function_names + table_names_to_search))
                if found > 0:
                    project = requests.get(f"http://localhost:8000/api/v2/repo/{path.name}").json()

                    restricted[dataset.name]["using"].append(
                        {"name": path.name, "url": f"https://github.com/opensafely/{path.name}", "project_name": project["name"], "project_url": project["url"]}
                    )
                    break

        print(f"\n============={dataset.name}============")
        print("\nALLOWED\n-------")
        print("\n".join(restricted[dataset.name]["allowed"]))
        print("\nUSING\n-----")
        print(
            "\n".join(
                [f"{repo['name']} - {repo['project_name']}" for repo in restricted[dataset.name]["using"]]
            )
        )
        
    markdown = "# Restricted Dataset Use"
    for dataset_name, data in restricted.items():
        markdown += f"\n## {dataset_name}"
        markdown += "\n### Allowed repos"
        for repo in data["allowed"]:
            markdown += f"\n - [{repo}](https://github.com/opensafely/{repo})"
        markdown += "\n### Repos using dataset"
        for repo_dict in data["using"]:
            if repo_dict["name"] not in data["allowed"]:
                repo_name = f"**{repo_dict['name']}**"
            else:
                repo_name = repo_dict['name']
            markdown += f"\n - [{repo_name}]({repo_dict['url']}) (project: [{repo_dict['project_name']}]({repo_dict['project_url']}))"

    outpath = Path("restricted_dataset_report.md")
    outpath.write_text(markdown)


if __name__ == "__main__":
    check()
