#! /usr/bin/env python3
from typing import Any

from silly_engine.router import Router, RouterError

from core import (
    list_stores, add_store, select_store_by_name, delete_store_by_name, select_store_by_id,
    get_current_config,
    add_repo_to_store, add_and_create_repo, list_repos_in_current_store
)
from models import Store


def print_res(res: Any | str) -> None:
    if isinstance(res, str):
        print(res)

# ----------------------------------------------------------------
# KEEPs TUI FUNCTIONS
# ----------------------------------------------------------------

def cli_add_store(name: str, path: str, description: str = "") -> None:
    if name in [k.name for k in list_stores()]:
        print(f"Store with name '{name}' already exists")
        return
    if path in [k.path for k in list_stores()]:
        print(f"Store with path '{path}' already exists")
        return
    add_store(name, path, description)
    cli_list_stores()

def cli_delete_store_by_name(name: str) -> None:
    res = delete_store_by_name(name)
    print_res(res)
    cli_list_stores()

def cli_list_stores() -> None:
    stores = list_stores()
    if not stores:
        print("No stores found")
        return
    config = get_current_config()
    for store in stores:
        prefix = " "
        if store._id == config.current_store_id:
            prefix = "*"
        availability = "✅"if store.is_active else "❌"
        print(f"{prefix}{availability}- {store.name:<20}: {store.path} ({store._id})")

def cli_select_store_by_name(name: str) -> None:
    select_store_by_name(name)
    cli_list_stores()

# ----------------------------------------------------------------
# CONFIG TUI FUNCTIONS
# ----------------------------------------------------------------

def cli_show_config() -> None:
    config = get_current_config()
    store = None
    if config.current_store_id:
        store = select_store_by_id(config.current_store_id)
    print(f"current_store_id: {config.current_store_id}")
    if store is not None:
        assert isinstance(store, Store)
        print(f"current_store: {store.name}")

# ----------------------------------------------------------------
# REPOS TUI FUNCTIONS
# ----------------------------------------------------------------

def cli_repo_add(name: str) -> None:
    res = add_repo_to_store(name)
    print_res(res)


def cli_create_and_add_repo(name: str) -> None:
    res = add_and_create_repo(name)
    print_res(res)

def cli_list_repos_in_current_store(**kwargs) -> None:
    query_params = kwargs.get("query_params", {})
    tip = query_params.get("tip", False)
    repos = list_repos_in_current_store()
    if not repos:
        print("No repos found in the current store")
        return
    for repo in repos:
        prefix = "✅" if repo.is_active else "❌"
        print(f"{prefix}- {repo.name}: {repo.path} ({repo._id})")
        if tip:
            print(f"git remote add local {repo.path}")


# ----------------------------------------------------------------
# MAIN CLI
# ----------------------------------------------------------------

if __name__ == "__main__":
    router = Router(name="Local Git Manager", width=80)
    router.add_routes([
        (("", "-h", "--help"), router.display_help, "Show this help message"),
        "\n# Stores commands:",
        ("store add <name> <path>", cli_add_store, "Add a new store"),
        ("store delete <name>", cli_delete_store_by_name, "Delete a store by name"),
        ("store select <name>", cli_select_store_by_name, "Select a store to be the current one"),
        ("store ls", cli_list_stores, "List all stores"),
        "\n# Repos commands:",
        ("repo add <name>", cli_repo_add, "Add a new repo to the current store"),
        ("repo create <name>", cli_create_and_add_repo, "Add a new repo to the current store and create it on the filesystem"),
        ("repo ls", cli_list_repos_in_current_store, "List all repos in the current store, ?tip to show git remote add command"),
        "\n# Config commands:",
        ("config", cli_show_config, "Show current configuration"),
    ])
    try:
        router.query()
    except RouterError as e:
        print(f"Error: {e}")