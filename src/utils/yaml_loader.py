from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import ValidationError

from src.schemas.policy import Policy


class PolicyLoaderError(Exception):
    pass


def load_policy(path: Path) -> Policy:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
        return Policy.model_validate(data)
    except (yaml.YAMLError, ValidationError) as exc:
        raise PolicyLoaderError(f"Failed to load policy '{path.name}': {exc}") from exc


@lru_cache
def load_policies(policy_dir: str) -> list[Policy]:
    policies: list[Policy] = []
    base = Path(policy_dir)
    if not base.exists():
        return policies
    for path in sorted(base.glob("*.yaml")):
        policies.append(load_policy(path))
    return [policy for policy in policies if policy.enabled]

