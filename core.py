from pathlib import Path
import logging
import subprocess
from uuid import uuid4

from models import get_db, Configuration, Store, Repo
from silly_engine.data_validation import DataValidationError
from silly_engine.logger import Logger

logger = Logger("core.py")
logger.level = logging.DEBUG


db = get_db()
Config = db.collection("config", model=Configuration)
Repos = db.collection("repos", model=Repo)
Stores = db.collection("stores", model=Store)


# ----------------------------------------------------------------
# STORE FUNCTIONS
# ----------------------------------------------------------------

def autoselect_store() -> bool:
    config = get_current_config()
    current_store_id = config.current_store_id
    stores_list = Stores.all()
    if not current_store_id:
        if not stores_list:
            config.current_store_id = ""
        else:
            config.current_store_id = stores_list[0]._id
    Config.first_update(config)
    return True

def list_stores() -> list[Store]:
    autoselect_store()
    stores = []
    for store in Stores.all():
        stores.append(store)
    return stores

def add_store(name: str, path: str, description: str = "") -> Store | str:
    try:
        store = Store(**{
            "name": name,
            "path": path,
            "description": description,
            "repos_ids": [],
        })
    except DataValidationError as e:
        return f"Error creating store: {e}"
    if Stores.filter(lambda k: k["name"] == name):
        return f"Store with name '{name}' already exists"
    if not Path(path).expanduser().resolve().exists():
        return f"Path '{path}' does not exist"
    if not Path(path).expanduser().resolve().is_dir():
        return f"Path '{path}' is not a directory"
    Stores.insert(store)
    autoselect_store()
    return store

def _get_store_by_id(store_id: str) -> Store | None:
    stores = Stores.filter(lambda k: k["_id"] == store_id)
    if not stores:
        return None
    store = stores[0]
    assert isinstance(store, Store)
    return store

def select_store_by_id(store_id: str) -> Store | str:
    stores = Stores.filter(lambda k: k["_id"] == store_id)
    if not stores:
        return f"Store with id '{store_id}' not found"
    store = stores[0]
    assert isinstance(store, Store)
    Config.first_update({"current_store_id": store_id})
    return store

def select_store_by_name(name: str) -> Store | str:
    stores = Stores.filter(lambda k: k["name"] == name)
    if not stores:
        return f"Store with name '{name}' not found"
    store = stores[0]
    assert isinstance(store, Store)
    if store.is_active:
        Config.first_update({"current_store_id": store._id})
    return store

def delete_store_by_name(name: str) -> str:
    stores = Stores.filter(lambda k: k["name"] == name)
    if not stores:
        return f"Store with name '{name}' not found"
    store = stores[0]
    assert isinstance(store, Store)
    for repo_id in store.repos_ids:
        Repos.delete(repo_id)
    Stores.delete(store._id)
    autoselect_store()
    return f"Store '{name}' deleted successfully"

# ----------------------------------------------------------------
# CONFIG FUNCTIONS
# ----------------------------------------------------------------

def get_current_config():
    config = Config.first()
    if not config:
        config = Configuration(**{"current_store_id": ""})
        config = Config.insert(config)
    assert isinstance(config, Configuration)
    return config

# ----------------------------------------------------------------
# REPO FUNCTIONS
# ----------------------------------------------------------------

def _create_repo(repo: Repo) -> Repo:
    """Create the actual git repository on the filesystem"""
    store = _get_store_by_id(repo.store_id)
    if store is None:
        raise ValueError(f"Store with id '{repo.store_id}' not found")
    if not store.is_active:
        raise ValueError(f"Store with id '{repo.store_id}' is not active")
    repo_path = Path(store.path).expanduser().resolve() / repo.name
    repo.path = str(repo_path)
    Repos.update(repo)
    repo_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--bare", repo.name], cwd=store.path)
    return repo

def add_repo_to_store(name: str, description: str = "No description") -> str | Repo | None:
    config = get_current_config()
    store_id = config.current_store_id
    store = _get_store_by_id(store_id)
    if store is None or not store.is_active:
        return "No active store selected. Please select an active store before adding a repo."
    repo_path = Path(store.path).expanduser().resolve() / name
    try:
        repo = Repo(**{
            "name": name,
            "description": description,
            "store_id": store_id,
            "path": str(repo_path),
        })
    except DataValidationError as e:
        return f"Error creating repo: {e}"
    if Repos.filter(lambda k: k["name"] == name and k["store_id"] == store_id):
        return f"Repo with name '{name}' already exists in this store"
    repo = Repos.insert(repo)
    assert isinstance(repo, Repo)
    store.repos_ids.append(repo._id)
    Stores.update(store)
    assert isinstance(repo, Repo)
    return f"Repo '{name}' added successfully"

def add_and_create_repo(name: str, description: str = "No description") -> str | Repo:
    add_repo_to_store(name, description)
    config = get_current_config()
    store_id = config.current_store_id
    repos = Repos.filter(lambda k: k["name"] == name and k["store_id"] == store_id)
    if not repos:
        return f"Repo with name '{name}' not found in the current store after adding it"
    repo = repos[0]
    assert isinstance(repo, Repo)
    return _create_repo(repo)

def list_repos_in_current_store() -> list[Repo]:
    config = get_current_config()
    store_id = config.current_store_id
    repos: list[Repo] = Repos.filter(lambda k: k["store_id"] == store_id)  # type: ignore
    return repos