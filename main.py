#! /usr/bin/env python3
from typing import Any

from silly_engine.router import Router, RouterError

from core import (
    add_repo, create_repo, list_repos, remove_repo_by_name,
    list_keeps, add_keep, select_keep_by_name,
    get_current_config,
)


def print_res(res: Any | str) -> None:
    if isinstance(res, str):
        print(res)

# ----------------------------------------------------------------
# KEEPs TUI FUNCTIONS
# ----------------------------------------------------------------

def tui_add_keep(name: str, path: str, description: str = "") -> None:
    if name in [k.name for k in list_keeps()]:
        print(f"Keep with name '{name}' already exists")
        return
    new_keep = add_keep(name, path, description)
    print(new_keep)

def tui_list_keeps() -> None:
    keeps = list_keeps()
    if not keeps:
        print("No keeps found")
        return
    config = get_current_config()
    for keep in keeps:
        prefix = " "
        if keep._id == config.data.get("current_keep_id"):
            prefix = "*"
        availability = "✅"if keep.is_active else "❌"
        print(f"{prefix}{availability}- {keep.name:<20}: {keep.path}")

def tui_select_keep_by_name(name: str) -> None:
    select_keep_by_name(name)
    tui_list_keeps()

# ----------------------------------------------------------------
# REPOS TUI FUNCTIONS
# ----------------------------------------------------------------

def tui_add_repo(name: str, url: str, description: str = "") -> None:
    res = add_repo(name, url, description)
    print_res(res)

def tui_list_repos() -> None:
    repos = list_repos()
    config = get_current_config()
    if not repos:
        print("No repos found")
        return
    for repo in repos:
        prefix = " "
        if repo._id == config.data.get("current_repo_id"):
            prefix = "*"
        availability = "✅"if repo.is_active else "❌"
        print(f"{prefix}{availability}- {repo.name}: {repo.path} {repo._id}")

def tui_create_repo(name: str, path: str) -> None:
    if name in [r.name for r in list_repos()]:
        print(f"Repo with name '{name}' already exists")
        return
    new_repo = create_repo(name, path)
    print(new_repo)

def tui_remove_repo(name: str) -> None:
    res = remove_repo_by_name(name)
    if res:
        print(f"Repo '{name}' removed successfully")
    else:
        print(f"Repo '{name}' not found")


# ----------------------------------------------------------------
# CONFIG TUI FUNCTIONS
# ----------------------------------------------------------------

def tui_show_config() -> None:
    config = get_current_config()
    print(config)


if __name__ == "__main__":
    router = Router(name="local Git", width=100)
    router.add_routes([
        (("", "-h", "--help"), router.display_help, "Show this help message"),
        "Repos commands:",
        ("repo add <keep> <name>", tui_add_repo, "Add an already existing repo"),
        ("repo create <keep> <name>", tui_create_repo, "Create a new repo"),
        ("repo remove <keep> <name>", tui_remove_repo, "Remove a repo"),
        ("repo ls", tui_list_repos, "List all repos"),
        "Keeps commands:",
        ("keep add <name> <path>", tui_add_keep, "Add a new keep"),
        ("keep select <name>", tui_select_keep_by_name, "Select a keep to be the current one"),
        ("keep ls", tui_list_keeps, "List all keeps"),
        "Config commands:",
        ("config", tui_show_config, "Show current configuration"),
    ])
    try:
        router.query()
    except RouterError as e:
        print(f"Error: {e}")