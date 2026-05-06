from __future__ import annotations

import argparse
import fnmatch
import json
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

PHASE = "4B.4.3.6.6.24A"
DEFAULT_EXCLUDE_PATTERNS = (
    ".venv/**",
    "venv/**",
    "env/**",
    ".pytest_cache/**",
    "**/__pycache__/**",
    ".tradebot/**",
    "logs/**",
    "*.log",
    "all_output.log",
    "dashboard_error.txt",
    "config.local.yaml",
    ".env",
    ".env.*",
    "*.bak",
    "*.tmp",
    "*.broken_before_*.py",
    "FIX_REPORT*.txt",
    "reports/acceptance_logs/**",
)
SENSITIVE_CONFIG_RE = re.compile(
    r"(?im)^\s*(api_key|api_secret|secret|token|password)\s*[:=]\s*['\"]?([^'\"\s#][^#\r\n]*)"
)
PLACEHOLDER_VALUES = {
    "",
    "none",
    "null",
    "[redacted]",
    "redacted",
    "changeme",
    "change_me",
    "your_api_key_here",
    "your_api_secret_here",
    "<api_key>",
    "<api_secret>",
}


@dataclass(frozen=True)
class ReleaseBuildResult:
    ok: bool
    archive_path: str
    file_count: int
    excluded_count: int
    secret_hits: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "archive_path": self.archive_path,
            "file_count": self.file_count,
            "excluded_count": self.excluded_count,
            "secret_hits": self.secret_hits,
        }


def _normalize(path: Path | str) -> str:
    return Path(path).as_posix().lstrip("./")


def load_releaseignore(root: Path) -> list[str]:
    path = root / ".releaseignore"
    patterns = list(DEFAULT_EXCLUDE_PATTERNS)
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            item = line.strip()
            if not item or item.startswith("#"):
                continue
            if item not in patterns:
                patterns.append(item)
    return patterns


def is_excluded(rel_path: str, patterns: Iterable[str]) -> bool:
    rel = _normalize(rel_path)
    parts = rel.split("/")
    for pattern in patterns:
        pat = _normalize(pattern)
        if fnmatch.fnmatch(rel, pat):
            return True
        if pat.endswith("/**"):
            prefix = pat[:-3].rstrip("/")
            if rel == prefix or rel.startswith(prefix + "/"):
                return True
        if pat.startswith("**/") and len(parts) > 1:
            suffix = pat[3:]
            if fnmatch.fnmatch(rel, suffix) or fnmatch.fnmatch("/".join(parts[1:]), suffix):
                return True
    return False


def iter_release_files(root: Path, patterns: Iterable[str]) -> tuple[list[Path], int]:
    files: list[Path] = []
    excluded = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if is_excluded(rel, patterns):
            excluded += 1
            continue
        files.append(path)
    return files, excluded


def _looks_like_secret(value: str) -> bool:
    clean = value.strip().strip("'\"").strip()
    if clean.lower() in PLACEHOLDER_VALUES:
        return False
    if clean.startswith("${") and clean.endswith("}"):
        return False
    if "[REDACTED]" in clean.upper():
        return False
    return len(clean) >= 12


def scan_file_for_plain_secrets(path: Path, root: Path) -> list[str]:
    rel = path.relative_to(root).as_posix()
    if path.suffix.lower() not in {".yaml", ".yml", ".env", ".json", ".toml"}:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    hits: list[str] = []
    for match in SENSITIVE_CONFIG_RE.finditer(text):
        key = match.group(1)
        value = match.group(2)
        if _looks_like_secret(value):
            hits.append(f"{rel}:{key}")
    return hits


def scan_release_files_for_plain_secrets(files: Iterable[Path], root: Path) -> list[str]:
    hits: list[str] = []
    for path in files:
        hits.extend(scan_file_for_plain_secrets(path, root))
    return hits


def build_release_archive(root: Path, out_dir: Path | None = None, *, fail_on_secret: bool = True) -> ReleaseBuildResult:
    root = root.resolve()
    out_dir = (out_dir or (root / "dist")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    patterns = load_releaseignore(root)
    files, excluded_count = iter_release_files(root, patterns)
    secret_hits = scan_release_files_for_plain_secrets(files, root)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = out_dir / f"trade_botV2_{PHASE.replace('.', '')}_clean_release_{timestamp}.zip"
    ok = not secret_hits
    if fail_on_secret and secret_hits:
        return ReleaseBuildResult(False, archive_path.as_posix(), len(files), excluded_count, secret_hits)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            rel = path.relative_to(root).as_posix()
            zf.write(path, rel)
    return ReleaseBuildResult(ok, archive_path.as_posix(), len(files), excluded_count, secret_hits)


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Build clean release archive for {PHASE}")
    parser.add_argument("--root", default=".", help="Project root")
    parser.add_argument("--out-dir", default="dist", help="Output directory")
    parser.add_argument("--allow-secret-hits", action="store_true", help="Do not fail on plain secret hits")
    args = parser.parse_args()
    result = build_release_archive(
        Path(args.root),
        Path(args.out_dir),
        fail_on_secret=not args.allow_secret_hits,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if result.ok or args.allow_secret_hits else 2


if __name__ == "__main__":
    raise SystemExit(main())
