from pathlib import Path
from typing import List, Dict, Optional
import subprocess


def _resolve_gitdir(repo_path: Path) -> Path:
    git_path = repo_path / ".git"
    if git_path.is_dir():
        return git_path
    if git_path.is_file():
        first = git_path.read_text(encoding="utf-8").splitlines()[0].strip()
        if first.startswith("gitdir:"):
            target = first.split(":", 1)[1].strip()
            return (repo_path / target).resolve()
    # Maybe this is a bare repository where the repository path IS the gitdir
    if (repo_path / "HEAD").exists() and (repo_path / "refs").exists():
        return repo_path

    raise RuntimeError(f".git not found or invalid in {repo_path}")


def _walk_refs_dir(refs_dir: Path, prefix: str) -> Dict[str, str]:
    refs = {}
    if not refs_dir.exists():
        return refs
    for p in refs_dir.rglob("*"):
        if p.is_file():
            # branch name is path relative to refs_dir
            rel = p.relative_to(refs_dir).as_posix()
            refname = f"{prefix}/{rel}"
            refs[refname] = p.read_text(encoding="utf-8").strip()
    return refs


def _parse_packed_refs(packed_file: Path) -> Dict[str, str]:
    refs = {}
    if not packed_file.exists():
        return refs
    for line in packed_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("^"):
            continue
        # format: <sha> <refname>
        parts = line.split(None, 1)
        if len(parts) == 2:
            sha, ref = parts
            refs[ref] = sha
    return refs


def list_branches(repo_path: str) -> List[Dict[str, Optional[str]]]:
    """
    Returns a list of branches found in the repo.
    Each branch is a dict: {'name': 'main', 'ref': 'refs/heads/main'|'refs/remotes/origin/main',
    'sha': '...', 'type': 'local'|'remote', 'current': True|False}
    """
    repo = Path(repo_path).resolve()
    gitdir = _resolve_gitdir(repo)

    # collect refs from filesystem
    heads = _walk_refs_dir(gitdir / "refs" / "heads", "refs/heads")
    remotes = _walk_refs_dir(gitdir / "refs" / "remotes", "refs/remotes")

    # collect packed refs
    packed = _parse_packed_refs(gitdir / "packed-refs")
    # packed refs may override or add missing entries
    for ref, sha in packed.items():
        if ref.startswith("refs/heads") and ref not in heads:
            heads[ref] = sha
        if ref.startswith("refs/remotes") and ref not in remotes:
            remotes[ref] = sha

    # read HEAD to detect current branch
    current_ref = None
    head_file = gitdir / "HEAD"
    if head_file.exists():
        head_txt = head_file.read_text(encoding="utf-8").strip()
        if head_txt.startswith("ref:"):
            current_ref = head_txt.split(":", 1)[1].strip()

    out = []
    for ref, sha in sorted(heads.items()):
        name = ref[len("refs/heads/") :]
        out.append({"name": name, "ref": ref, "sha": sha, "type": "local", "current": ref == current_ref})
    for ref, sha in sorted(remotes.items()):
        name = ref[len("refs/remotes/") :]
        out.append({"name": name, "ref": ref, "sha": sha, "type": "remote", "current": ref == current_ref})

    return out


def list_commits(repo_path: str, branch_ref: str, max_count: Optional[int] = None) -> List[Dict[str, str]]:
    """Return a list of commits for the given branch/ref using the `git` CLI.

    Each commit is a dict: {'sha', 'author', 'date', 'subject'}.
    Returns an empty list on error or if the branch is not found.
    """
    repo = Path(repo_path).resolve()
    cmd = ["git", "-C", str(repo), "log", "--pretty=format:%H\t%an\t%ad\t%s"]
    if max_count is not None:
        cmd += ["-n", str(max_count)]
    cmd.append(branch_ref)
    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return []
    commits: List[Dict[str, str]] = []
    for line in out.splitlines():
        parts = line.split("\t", 3)
        if len(parts) != 4:
            continue
        sha, author, date, subject = parts
        commits.append({"sha": sha, "author": author, "date": date, "subject": subject})
    return commits