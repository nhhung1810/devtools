import fnmatch
from typing import Any, Generator
from pathlib import Path
import json
import os


def make_nest_path(path: str, is_file=True) -> str:
    """Make nest path, return the directory

    Args:
        path (str): The path to the file/directory
        is_file (bool, optional): is this path represent a
            file or a dir. Defaults to True.
    """

    def make_nested_dir(directory: str) -> str:
        Path(directory).mkdir(parents=True, exist_ok=True)
        return directory

    if not is_file:
        return make_nested_dir(path)

    return make_nested_dir(os.path.dirname(path))


def scan_dir(root: str, pattern: str) -> Generator[str, None, None]:
    """Scan directory and find file that match pattern

    Args:
        root (str): path of directory to begin scanning
        pattern (str): pattern to filter for

    Yields:
        str: Full path to the file
    """
    for dirpath, _, files in os.walk(root):
        files = fnmatch.filter(files, pattern)
        if len(files) == 0:
            continue
        for filename in files:
            yield os.path.join(dirpath, filename)


def load_json(path: str, encoding: str) -> Any:
    with open(path, mode="r", encoding=encoding) as f:
        return json.load(f)


def write_json(obj: Any, path: str, encoding: str):
    with open(path, mode="w", encoding=encoding) as f:
        json.dump(obj, f)
        pass
