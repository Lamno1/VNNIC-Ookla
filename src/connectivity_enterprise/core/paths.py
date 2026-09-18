from pathlib import Path
import fnmatch
import yaml


WORKING_ROOT = Path(__file__).resolve().parents[3]


def load_yaml(relative_path):
    path = WORKING_ROOT / relative_path
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def sources_config():
    return load_yaml("config/sources.yml")


def study_config():
    return load_yaml("config/study.yml")


def variables_config():
    return load_yaml("config/variables.yml")


def assert_output_path(path):
    resolved = Path(path).resolve()
    try:
        resolved.relative_to(WORKING_ROOT.resolve())
    except ValueError as exc:
        raise RuntimeError(
            f"FAIL-CLOSED: attempted write outside working root: {resolved}"
        ) from exc
    return resolved


def protected_roots():
    return {
        key: Path(value).resolve()
        for key, value in sources_config()["protected_roots"].items()
    }


def assert_safe_input_path(path):
    resolved = Path(path).resolve()
    if is_credential_like(resolved):
        raise RuntimeError(
            "FAIL-CLOSED: credential-like input is prohibited"
        )
    matches = []
    for root_id, root in protected_roots().items():
        try:
            resolved.relative_to(root)
            matches.append(root_id)
        except ValueError:
            pass
    if not matches:
        raise RuntimeError(
            f"FAIL-CLOSED: input is outside protected allow-list: {resolved}"
        )
    return resolved


def is_credential_like(path):
    name = Path(path).name.lower()
    patterns = sources_config()["credential_exclusions"]
    return any(fnmatch.fnmatch(name, pattern.lower()) for pattern in patterns)
