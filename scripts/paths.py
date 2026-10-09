"""Resolve export / books directories for Starters Labo skills.

Priority (highest first):

1. Explicit CLI args (handled by callers)
2. ``STARTERSLABO_EXPORT_DIR`` / ``STARTERSLABO_BOOKS``
3. ``STARTERSLABO_DATA`` root + default subdirs ``export/`` and ``books/``
4. Config file from ``STARTERSLABO_CONFIG``, or first ``starterslabo.yaml``
   found walking parents of cwd / this file
5. Legacy defaults (skill ``rapport-export/``, walk for ``books/main.bean``)

Config YAML keys (all optional)::

    data_root: /absolute/or/relative   # base for relative export_dir/books_dir
    export_dir: export                 # relative to data_root or absolute
    books_dir: books

Relative paths in the YAML are resolved against the config file's directory
unless ``data_root`` is set (then against ``data_root``).
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

CONFIG_NAMES = ("starterslabo.yaml", "starterslabo.yml")
DEFAULT_EXPORT_SUBDIR = "export"
DEFAULT_BOOKS_SUBDIR = "books"
# Older skill default folder name (still accepted when present)
LEGACY_EXPORT_SUBDIR = "rapport-export"


def _skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_yaml(path: Path) -> dict:
    if yaml is None or not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def find_config_file() -> Path | None:
    env = (os.environ.get("STARTERSLABO_CONFIG") or "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        return p if p.is_file() else None

    search_roots = [Path.cwd().resolve(), *_skill_root().parents]
    seen: set[Path] = set()
    for root in search_roots:
        for parent in [root, *root.parents]:
            if parent in seen:
                continue
            seen.add(parent)
            for name in CONFIG_NAMES:
                candidate = parent / name
                if candidate.is_file():
                    return candidate
            # Common Phoenix / monorepo nesting
            for rel in (
                Path("nexus/starterslabo") / "starterslabo.yaml",
                Path("data/raw/StartersLabo") / "starterslabo.yaml",
            ):
                candidate = parent / rel
                if candidate.is_file():
                    return candidate
    return None


def load_config() -> dict:
    path = find_config_file()
    if not path:
        return {}
    cfg = _load_yaml(path)
    cfg["_config_path"] = str(path)
    cfg["_config_dir"] = str(path.parent)
    return cfg


def _resolve(path_value: str | Path, base: Path) -> Path:
    p = Path(path_value).expanduser()
    if not p.is_absolute():
        p = (base / p).resolve()
    else:
        p = p.resolve()
    return p


def data_root(config: dict | None = None) -> Path | None:
    cfg = config if config is not None else load_config()
    env = (os.environ.get("STARTERSLABO_DATA") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    if cfg.get("data_root"):
        base = Path(cfg.get("_config_dir") or Path.cwd())
        return _resolve(cfg["data_root"], base)
    if cfg.get("_config_dir"):
        # Config lives inside the data root (nexus/starterslabo/starterslabo.yaml)
        return Path(cfg["_config_dir"]).resolve()
    return None


def export_dir(
    *,
    cli: Path | None = None,
    config: dict | None = None,
) -> Path:
    """Directory for Rapport CSV flat files."""
    if cli is not None:
        return cli.expanduser().resolve()

    env = (os.environ.get("STARTERSLABO_EXPORT_DIR") or "").strip()
    if env:
        return Path(env).expanduser().resolve()

    cfg = config if config is not None else load_config()
    root = data_root(cfg)
    if cfg.get("export_dir"):
        base = root or Path(cfg.get("_config_dir") or Path.cwd())
        return _resolve(cfg["export_dir"], base)
    if root is not None:
        for name in (DEFAULT_EXPORT_SUBDIR, LEGACY_EXPORT_SUBDIR):
            candidate = root / name
            if candidate.is_dir() or name == DEFAULT_EXPORT_SUBDIR:
                return candidate if candidate.is_dir() else (root / DEFAULT_EXPORT_SUBDIR)

    # Legacy: skill-local rapport-export/
    legacy = _skill_root() / LEGACY_EXPORT_SUBDIR
    return legacy


def books_dir(
    *,
    cli: Path | None = None,
    config: dict | None = None,
) -> Path:
    """Directory containing main.bean (Beancount books root)."""
    if cli is not None:
        return cli.expanduser().resolve()

    env = (os.environ.get("STARTERSLABO_BOOKS") or "").strip()
    if env:
        return Path(env).expanduser().resolve()

    cfg = config if config is not None else load_config()
    root = data_root(cfg)
    if cfg.get("books_dir"):
        base = root or Path(cfg.get("_config_dir") or Path.cwd())
        return _resolve(cfg["books_dir"], base)
    if root is not None:
        return root / DEFAULT_BOOKS_SUBDIR

    # Walk for books/main.bean
    here = Path(__file__).resolve()
    for parent in [Path.cwd().resolve(), *here.parents]:
        candidate = parent / "books"
        if (candidate / "main.bean").exists():
            return candidate
        if parent.name == "books" and (parent / "main.bean").exists():
            return parent

    return _skill_root().parent.parent.parent / "books"  # weak fallback


def describe_paths() -> str:
    cfg = load_config()
    lines = [
        f"config: {cfg.get('_config_path') or '(none)'}",
        f"data_root: {data_root(cfg) or '(none)'}",
        f"export_dir: {export_dir(config=cfg)}",
        f"books_dir: {books_dir(config=cfg)}",
    ]
    return "\n".join(lines)
