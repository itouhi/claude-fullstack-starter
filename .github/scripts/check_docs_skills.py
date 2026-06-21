#!/usr/bin/env python3
"""docs / skills の静的整合チェック (外部依存なし)。

開発環境の構成要素のうち「文章で表現される層」を検証する:

- A: 各スキルの SKILL.md に name/description があり、name がディレクトリ名と一致する
- B: CLAUDE.md のスキル一覧と .claude/skills/ の実ディレクトリ集合が一致する
- C: docs の日英ペア (X.md <-> X.en.md) と README の日英ペアが揃っている

CI でもローカルでも実行できる:

    python3 .github/scripts/check_docs_skills.py

問題があれば内容を表示して終了コード 1 を返す。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = ROOT / ".claude" / "skills"
CLAUDE_MD = ROOT / "CLAUDE.md"
DOCS_DIR = ROOT / "docs"

# CLAUDE.md のスキル一覧行 (例: "- `add-api-endpoint` — FastAPI エンドポイント追加")
SKILL_BULLET = re.compile(r"^- +`([a-z0-9][a-z0-9-]*)` +—")


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """先頭の `---` で囲まれた frontmatter を単純な key: value として読む。

    Args:
        text: ファイル全文。

    Returns:
        frontmatter の辞書。frontmatter が無ければ None。
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    data: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return data
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            data[m.group(1)] = m.group(2).strip()
    return None  # 閉じ `---` が無い


def check_skills(errors: list[str]) -> set[str]:
    """A: 各 SKILL.md の frontmatter を検証し、スキル名集合を返す。"""
    found: set[str] = set()
    if not SKILLS_DIR.is_dir():
        errors.append(f"[A] スキルディレクトリが無い: {SKILLS_DIR}")
        return found
    for entry in sorted(SKILLS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        found.add(entry.name)
        skill_md = entry / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"[A] {entry.name}: SKILL.md が無い")
            continue
        fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        if fm is None:
            errors.append(f"[A] {entry.name}/SKILL.md: frontmatter (--- で囲む) が無い")
            continue
        if not fm.get("name"):
            errors.append(f"[A] {entry.name}/SKILL.md: name がない")
        elif fm["name"] != entry.name:
            errors.append(
                f"[A] {entry.name}/SKILL.md: name '{fm['name']}' が"
                f"ディレクトリ名 '{entry.name}' と一致しない"
            )
        if not fm.get("description"):
            errors.append(f"[A] {entry.name}/SKILL.md: description がない")
    return found


def check_claude_md(errors: list[str], actual: set[str]) -> None:
    """B: CLAUDE.md のスキル一覧と実ディレクトリ集合を突き合わせる。"""
    if not CLAUDE_MD.is_file():
        errors.append(f"[B] {CLAUDE_MD} が無い")
        return
    documented = {
        m.group(1)
        for line in CLAUDE_MD.read_text(encoding="utf-8").splitlines()
        if (m := SKILL_BULLET.match(line))
    }
    if not documented:
        errors.append("[B] CLAUDE.md からスキル一覧 (- `name` — ...) を抽出できなかった")
        return
    missing = actual - documented  # 実在するが CLAUDE.md 未記載
    extra = documented - actual  # CLAUDE.md にあるが実体が無い
    for name in sorted(missing):
        errors.append(f"[B] スキル '{name}' が CLAUDE.md の一覧に未記載")
    for name in sorted(extra):
        errors.append(f"[B] CLAUDE.md のスキル '{name}' に対応するディレクトリが無い")


def check_bilingual(errors: list[str]) -> None:
    """C: docs と README の日英ペア (X.md <-> X.en.md) を検証する。"""
    targets: list[Path] = []
    if DOCS_DIR.is_dir():
        targets += sorted(DOCS_DIR.glob("*.md"))
    readme = ROOT / "README.md"
    if readme.is_file() or (ROOT / "README.en.md").is_file():
        targets += [readme, ROOT / "README.en.md"]
    for path in targets:
        if path.name.endswith(".en.md"):
            ja = path.with_name(path.name[: -len(".en.md")] + ".md")
            if not ja.is_file():
                errors.append(f"[C] {path.relative_to(ROOT)} に対応する日本語版が無い")
        elif path.name.endswith(".md"):
            en = path.with_name(path.name[: -len(".md")] + ".en.md")
            if not en.is_file():
                errors.append(f"[C] {path.relative_to(ROOT)} に対応する英語版 (.en.md) が無い")


def main() -> int:
    """全チェックを実行し、問題があれば 1 を返す。"""
    errors: list[str] = []
    actual = check_skills(errors)
    check_claude_md(errors, actual)
    check_bilingual(errors)

    if errors:
        print("docs/skills チェックに失敗しました:\n")
        for e in errors:
            print(f"  - {e}")
        print(f"\n{len(errors)} 件の問題があります。")
        return 1
    print(f"docs/skills チェック OK (スキル {len(actual)} 件・日英ペア・CLAUDE.md 整合)。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
