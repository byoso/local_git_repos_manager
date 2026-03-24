#! /usr/bin/env python3

from models import Repo


if __name__ == "__main__":

    data = {
        "project_name": "Test Project",
        "path": "/path/to/repo",
    }
    repo = Repo(data)
    print(repo)