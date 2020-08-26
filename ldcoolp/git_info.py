from pathlib import Path


def get_active_branch_name(input_path="."):

    head_dir = Path(input_path) / ".git" / "HEAD"
    with head_dir.open("r") as f:
        content = f.read().splitlines()

    for line in content:
        if line[0:4] == "ref:":
            return line.partition("refs/heads/")[2]


def get_latest_commit(input_path="."):

    head_dir = Path(input_path) / ".git" / "HEAD"
    with head_dir.open("r") as f:
        content = f.read().splitlines()

    for line in content:
        if line[0:4] == "ref:":
            head_path = Path(f".git/{line.partition(' ')[2]}")
            with head_path.open('r') as g:
                commit = g.read().splitlines()

    return commit[0], commit[0][:7]  # full and short hash
