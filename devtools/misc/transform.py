import json
from typing import Any, Dict, List


def pick(d: Dict[object, object], keys: List[object]):
    return {k: v for k, v in d.items() if k in keys}


def omit(d: Dict[object, object], keys: List[object]):
    return {k: v for k, v in d.items() if k not in keys}


def is_serializable(x: Any) -> bool:
    """A try-before-ask approach to checking serializable of Object

    Args:
        x (Any): object

    Returns:
        bool: is obj serializable?
    """
    try:
        json.dumps(x)
        return True
    except:
        return False
