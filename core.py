from pathlib import Path
import logging
import subprocess
from uuid import uuid4

from models import get_db, Configuration, Keep, Repo
from silly_engine.data_validation import DataValidationError
from silly_engine.logger import Logger
from silly_engine.jsondb import Item

logger = Logger("core.py")
logger.level = logging.DEBUG


db = get_db()
Config = db.collection("config")
Repos = db.collection("repos")
Keeps = db.collection("keeps")


# ----------------------------------------------------------------
# REMOTE FUNCTIONS
# ----------------------------------------------------------------

def add_repo(name: str, path: str, description: str = "") -> Repo | str:
    try:
        repo = Repo({
            "name": name,
            "path": path,
            "description": description,
        })
    except DataValidationError as e:
        return f"Error creating repo: {e}"
    if Repos.filter(lambda r: r["name"] == name):
        return f"Repo with name '{name}' already exists"
    Repos.insert(repo)
    return repo

def create_repo(name: str, keep_name: str) -> Repo | str:
    keep = Keeps.filter(lambda k: k["name"] == keep_name)
    if not keep:
        return f"Keep with name '{keep_name}' not found"
    path_obj = Path(keep[0].to_dict()["path"]).expanduser().resolve()
    if not path_obj.exists():
        return f"Path '{path_obj}' does not exist"

    repo_path = path_obj / (name + ".git")
    if repo_path.exists():
        return f"Repo repository '{repo_path}' already exists"

    result = subprocess.run(
        ["git", "init", "--bare", str(repo_path)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return f"Error creating repo repo: {result.stderr.strip()}"

    # Save in the json db
    repo_data = {"name": name, "path": str(repo_path), "keep_id": keep[0]._id}
    repo = Repo(repo_data)
    Repos.insert(repo)
    return repo

def remove_repo_by_id(repo_id: str) -> bool:
    repo = Repos.filter(lambda r: r["_id"] == repo_id)
    if not repo:
        return False
    Repos.delete(repo[0].to_dict())
    return True

def remove_repo_by_name(name: str) -> bool:
    repo = Repos.filter(lambda r: r["name"] == name)
    if not repo:
        return False
    Repos.delete(repo[0].to_dict())
    return True

def get_repo_by_id(repo_id: str) -> Repo | None:
    repo = Repos.filter(lambda r: r["_id"] == repo_id)
    if not repo:
        return None
    return Repo(repo[0].to_dict())

def get_repo_by_name(name: str) -> Repo | None:
    repo = Repos.filter(lambda r: r["name"] == name)
    if not repo:
        return None
    return Repo(repo[0].to_dict())

def list_repos() -> list[Repo]:
    current_keep = get_current_config().data.get("current_keep_id")
    if not current_keep:
        return []
    repos = []
    for repo in Repos.all():
        repo_obj = Repo(repo.to_dict())
        if repo_obj.keep_id == current_keep:
            repos.append(repo_obj)
    return repos

# ----------------------------------------------------------------
# KEEP FUNCTIONS
# ----------------------------------------------------------------

def autoselect_keep() -> bool:
    config = get_current_config()
    current_keep_id = config.data.get("current_keep_id")
    keeps_list = Keeps.all()
    if not current_keep_id:
        if not keeps_list:
            return False
        if current_keep_id is None or not any(k._id == current_keep_id for k in keeps_list):
            Config.first_update({"current_keep_id": keeps_list[0]._id})
    return True

def list_keeps() -> list[Keep]:
    autoselect_keep()
    keeps = []
    for keep in Keeps.all():
        keeps.append(Keep(keep.to_dict()))
    return keeps

def add_keep(name: str, path: str, description: str = "") -> Keep | str:
    try:
        keep = Keep({
            "name": name,
            "path": path,
            "description": description,
        })
    except DataValidationError as e:
        return f"Error creating keep: {e}"
    if Keeps.filter(lambda k: k["name"] == name):
        return f"Keep with name '{name}' already exists"
    if not Path(path).expanduser().resolve().exists():
        return f"Path '{path}' does not exist"
    Keeps.insert(keep)
    autoselect_keep()
    return keep

def select_keep_by_id(keep_id: str) -> Keep | str:
    keep = Keeps.filter(lambda k: k["_id"] == keep_id)
    if not keep:
        return f"Keep with id '{keep_id}' not found"
    Config.first_update({"current_keep_id": keep_id})
    return Keep(keep[0].to_dict())

def select_keep_by_name(name: str) -> Keep | str:
    keep = Keeps.filter(lambda k: k["name"] == name)
    if not keep:
        return f"Keep with name '{name}' not found"
    Config.first_update({"current_keep_id": keep[0]._id})
    return Keep(keep[0].to_dict())

# ----------------------------------------------------------------
# CONFIG FUNCTIONS
# ----------------------------------------------------------------

def get_current_config() -> Item:
    config = Config.first()
    if not config:
        config = Configuration({"current_keep_id": ""})
        config = Config.insert(config)
    return config