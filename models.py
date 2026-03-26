from dataclasses import dataclass
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
    current_keep_id: str = ""


@dataclass
class Repo(ValidatedDataClass):
    name: str = ""
    description: str = ""
    path: str = ""
    keep_id: str = ""

    def _validate(self) -> None:
        if " " in self.name:
            raise DataValidationError("name must not contain spaces")

    @property
    def is_active(self) -> bool:
        if Path(self.path).exists():
            return True
        return False

@dataclass
class Keep(ValidatedDataClass):
    """A keep is a file or directory where we want to store the Repos"""
    name: str = ""
    description: str = ""
    path: str = ""

    @property
    def is_active(self) -> bool:
        if Path(self.path).exists():
            return True
        return False