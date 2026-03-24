from pathlib import Path
import logging
import subprocess
from models import Repo, get_db
from silly_engine.data_validation import DataValidationError
from silly_engine.logger import Logger

logger = Logger("core.py")
logger.level = logging.DEBUG


db = get_db()
Repos = db.collection("repos")


def add_repo(project_name: str, path: str) -> Repo | str:
    path = str(Path(path).expanduser().resolve())
    logger.debug(f"Creating repo with project_name={project_name!r} and path={path!r}")
    # check database for existing project_name or path
    try:
        repo = Repo({
            "project_name": project_name,
            "path": path,
        })
    except DataValidationError as e:
        return f"Error creating repo: {e}"
    if Repos.filter(lambda r: r["project_name"] == project_name):
        return f"Repo with project_name '{project_name}' already exists"
    # check if path exists and is a git repository
    if not Path(path).exists():
        return f"Path '{path}' does not exist"
    Repos.insert(repo)
    return f"Repo '{project_name}' added successfully"

def create_git_repo(project_name: str, path: str) -> Repo | str:
    """Create the actual git repo if it doesn't exist"""
    if Repos.filter(lambda r: r["project_name"] == project_name):
        return f"Repo with project_name '{project_name}' already exists"
    path = str(Path(path).expanduser().resolve())
    if not Path(path).exists():
        return f"Path '{path}' does not exist"
    logger.debug(f"Creating bare git repo: {project_name} in {path}")

    try:
        repo_path = Path(path) / project_name
        result = subprocess.run(
            ["git", "init", "--bare", str(repo_path)],
            capture_output=True,
            text=True,
            cwd=path
        )
        if result.returncode != 0:
            return f"Error creating git repo: {result.stderr}"

        instruction = f"git remote add local {path}/{project_name}"
        return instruction
    except FileNotFoundError:
        return "Error: git command not found. Please install git."
    except Exception as e:
        return f"Error creating git repo: {e}"


def delete_by_name(project_name: str) -> bool:
    repo = Repos.filter(lambda r: r["project_name"] == project_name)
    if not repo:
        return False
    Repos.delete(repo[0])
    return True

def list_repos() -> list[Repo]:
    not_found = []
    found = []
    repos = []
    for repo in Repos.all():
        if not (Path(repo["path"]) / repo["project_name"]).exists():
            repo["is_active"] = False
        repos.append(Repo(repo))
    repos.sort(key=lambda r: r.is_active, reverse=True)
    return repos
