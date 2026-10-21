"""Opt-in language profiles; projects without a language retain the Chinese layout."""
from copy import deepcopy
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LANGUAGES = ("zh", "en")


def project_language(meta: dict | None = None) -> str:
    language = (meta or {}).get("language", "zh")
    if language not in LANGUAGES:
        raise ValueError(f"Unsupported project language: {language!r}")
    return language


def load_profile(language: str) -> dict:
    project_language({"language": language})
    if language == "zh":
        return {
            "voice": {"voice_primary": "zh-CN-XiaoyiNeural",
                      "voice_fallback": "zh-CN-YunxiNeural", "rate": "+0%"}
        }
    return yaml.safe_load(
        (ROOT / "config" / "languages" / f"{language}.yaml").read_text("utf-8"))


def apply_profile(config: dict, language: str, section: str) -> dict:
    """Merge only the selected language's overrides into a fresh configuration."""
    overrides = load_profile(language).get(section, {})
    result = deepcopy(config)

    def merge(target, changes):
        for key, value in changes.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                merge(target[key], value)
            else:
                target[key] = deepcopy(value)

    merge(result, overrides)
    return result
