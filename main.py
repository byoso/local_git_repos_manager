#! /usr/bin/env python3
from typing import Any

from silly_engine.router import Router, RouterError

from core import add_repo, create_git_repo, delete_by_name, list_repos

def print_res(res: Any | str) -> None:
    if isinstance(res, str):
        print(res)

def tui_add_repo(project_name: str, path: str) -> None:
    res = add_repo(project_name, path)
    print_res(res)

def tui_create_git_repo(project_name: str, path: str) -> None:
    res = create_git_repo(project_name, path)
    if isinstance(res, str):
        print(
            "Git repository 'project.git' created successfully.",
            "To add this remote to your project, do:"
        )
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
    for repo in repos:
        availability = "✅"if repo.is_active else "❌"
        print(f"{availability}- {repo.project_name}: {repo.path}")

if __name__ == "__main__":
    router = Router(name="local Git")
    router.add_routes([
        (("", "-h", "--help"), router.display_help, "Show this help message"),
        (("list", "ls"), tui_list_repos, "List all repos"),
        ("add <project_name> <path>", tui_add_repo, "Add a new repo"),
        ("create <project_name> <path>", tui_create_git_repo, "Create a new git repo"),
        ("remove <project_name>", tui_delete_repo, "remove a remote repo from list, but does NOT actually delete it"),
    ])
    try:
        router.query()
    except RouterError as e:
        print(f"Error: {e}")