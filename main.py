#! /usr/bin/env python3
from typing import Any

from silly_engine import router

from core import add_repo, delete_by_name, list_repos

def print_res(res: Any | str) -> None:
    if isinstance(res, str):
        print(res)

def tui_add_repo(project_name: str, path: str) -> None:
    res = add_repo(project_name, path)
    print_res(res)

def tui_delete_repo(project_name: str) -> None:
    res = delete_by_name(project_name)
    if res:
        print(f"Repo '{project_name}' deleted successfully")
    else:
        print(f"Repo '{project_name}' not found")

def tui_list_repos() -> None:
    repos = list_repos()
    if not repos:
        print("No repos found")
        return
    print("Available repos:")
    for repo in repos:
        print(f"- {repo.project_name}: {repo.path}")

if __name__ == "__main__":
    router = router.Router(name="local Git")
    router.add_routes([
        (("", "-h", "--help"), router.display_help, "Show this help message"),
        ("list", tui_list_repos, "List all repos"),
        ("add <project_name> <path>", tui_add_repo, "Add a new repo"),
        ("remove <project_name>", tui_delete_repo, "Delete a repo by project name"),
    ])
    router.query()