from dataclasses import dataclass

from silly_engine.data_validation import ValidatedDataClass, DataValidationError
from silly_engine.jsondb import JsonDb


def get_db() -> JsonDb:
    db = JsonDb(
        "localGit.json",
        autosave=True,
        )
    return db


@dataclass
class Repo(ValidatedDataClass):
    project_name: str = ""
    path: str = ""
    is_active: bool = True

    def _validate(self) -> None:
        if " " in self.project_name:
            raise DataValidationError("project_name must not contain spaces")