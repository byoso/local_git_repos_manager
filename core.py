from pathlib import Path
import logging
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
    if Repos.filter(lambda r: r["path"] == path):
        return f"Repo with path '{path}' already exists"
    # check if path exists and is a git repository
    if not Path(path).exists():
        return f"Path '{path}' does not exist"
    if not (Path(path) / project_name).exists():
        return f"Path '{path}' is not a git repository"
    # insert repo in db
    Repos.insert(repo)
    return f"Repo '{project_name}' added successfully"

def create_git_repo(project_name: str, path: str) -> Repo | str:
    """Create the actual git repo if it doesn't exist"""



def delete_by_name(project_name: str) -> bool:
    repo = Repos.filter(lambda r: r["project_name"] == project_name)
    if not repo:
        return False
    Repos.delete(repo[0])
    return True

def list_repos() -> list[Repo]:
    not_found = []
    found = []
    for repo in Repos.all():
        if not (Path(repo["path"]) / repo["project_name"]).exists():
            not_found.append(Repo(repo))
        else:
            found.append(Repo(repo))
    if not_found:
        logger.debug('Repos not found:')
        for repo in not_found:
            logger.debug(f"- {repo.project_name}: {repo.path}")
    return found
