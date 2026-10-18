#!/usr/bin/env python3
"""Проверка проекта перед публикацией: утечки ключей, игнор-файлы, тесты, сборка.

Запуск из корня репозитория:  python3 .claude/skills/lead-finder/scripts/check_release.py
Значения ключей никогда не печатаются — только имя переменной и файл, где оно нашлось.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SKIP_DIRS = {".venv", "node_modules", "data", ".git", "__pycache__", ".pytest_cache", "dist"}
MUST_IGNORE = [".env", "data/", ".venv/", "node_modules/"]
# Похожие на ключи строки, даже если их нет в .env (OpenAI / ProxyAPI и т.п.)
KEY_PATTERNS = [re.compile(r"sk-[A-Za-z0-9_-]{20,}")]

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'✓' if ok else '✗'} {name}{f' — {detail}' if detail else ''}", flush=True)


def env_secrets() -> list[tuple[str, str]]:
    env = ROOT / ".env"
    if not env.exists():
        return []
    secrets = []
    for line in env.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Z_]*(?:KEY|SECRET|TOKEN|PASSWORD)[A-Z_]*)=(.+)$", line.strip())
        if match and not match.group(2).startswith("your-") and len(match.group(2)) >= 8:
            secrets.append((match.group(1), match.group(2)))
    return secrets


def scan_secrets() -> None:
    secrets = env_secrets()
    leaks = []
    for path in ROOT.rglob("*"):
        if path.is_dir() or path.name == ".env" or SKIP_DIRS & set(path.relative_to(ROOT).parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = path.relative_to(ROOT)
        leaks += [f"{rel} ({name})" for name, value in secrets if value in text]
        leaks += [f"{rel} (похоже на API-ключ)" for p in KEY_PATTERNS if p.search(text)]
    check("Ключи из .env не попали в файлы проекта", not leaks, ", ".join(leaks))


def check_gitignore() -> None:
    gitignore = ROOT / ".gitignore"
    lines = gitignore.read_text().splitlines() if gitignore.exists() else []
    missing = [item for item in MUST_IGNORE if item not in lines]
    check(".gitignore закрывает .env, data/, .venv/, node_modules/", not missing, f"нет: {missing}" if missing else "")

    if (ROOT / ".git").exists():
        tracked = subprocess.run(
            ["git", "ls-files", ".env", "data"], cwd=ROOT, capture_output=True, text=True
        ).stdout.strip()
        check(".env и data/ не отслеживаются git", not tracked, tracked.replace("\n", ", "))


def run(name: str, cmd: list[str], cwd: Path = ROOT) -> None:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-1:] or [""]
    check(name, proc.returncode == 0, tail[0])


def main() -> int:
    print(f"Проект: {ROOT}\n")
    scan_secrets()
    check_gitignore()
    check(".env.example на месте", (ROOT / ".env.example").exists())

    if (ROOT / ".venv/bin/pytest").exists():
        run("Тесты бэкенда (pytest)", [str(ROOT / ".venv/bin/pytest"), "-q"])
    else:
        check("Тесты бэкенда (pytest)", False, "нет .venv — запустите ./start.sh один раз")

    frontend = ROOT / "frontend"
    if (frontend / "node_modules").exists():
        run("Юнит-тесты интерфейса", ["npm", "test", "--silent"], frontend)
        run("Сборка интерфейса (TypeScript + Vite)", ["npm", "run", "build", "--silent"], frontend)
    else:
        check("Интерфейс", False, "нет node_modules — запустите ./start.sh один раз")

    failed = [name for name, ok, _ in results if not ok]
    print(f"\n{'Готово к публикации' if not failed else f'Нужно исправить: {len(failed)}'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
