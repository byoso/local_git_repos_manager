from dataclasses import dataclass, field
from pathlib import Path

from silly_engine.data_validation import ValidatedDataClass, DataValidationError
from silly_engine.jsondb import JsonDb


def get_db() -> JsonDb:
    db = JsonDb(
        "localGit.json",
        autosave=True,
        )
    return db

@dataclass
class Configuration(ValidatedDataClass):
    description: str = "Singleton"
    current_store_id: str = ""


@dataclass
class Repo(ValidatedDataClass):
    name: str = ""
    description: str = ""
    path: str = ""
    store_id: str = ""

    def _validate(self) -> None:
        if " " in self.name:
            raise DataValidationError("name must not contain spaces")

    @property
    def is_active(self) -> bool:
        if Path(self.path).exists():
            return True
        return False

@dataclass
class Store(ValidatedDataClass):
    """A store is a file or directory where we want to store the Repos"""
    name: str = ""
    description: str = ""
    path: str = ""
    repos_ids: list[str] = field(default_factory=list)

    @property
    def repos(self) -> list[Repo]:
        db = get_db()
        repos = []
        for repo_id in self.repos_ids:
            repo = db.collections["repos"].get(repo_id)
            if repo is not None:
                repos.append(Repo(**repo))
        return repos


    @property
    def is_active(self) -> bool:
        if Path(self.path).exists():
            return True
        return False
