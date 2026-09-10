"""Ladowanie wbudowanych skilli z pakietu (src/pipeline_mcp/skills/).

Skille sa wbudowane w pakiet i ladowane przez importlib.resources.
Serwer nie zalezy od zewnetrznych katalogow skilli.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import SkillNotFoundError
from .stations import STATION_TO_SKILL_DIR, STATIONS


def _get_skills_dir() -> Path:
    """Zwraca sciezke katalogu wbudowanych skilli."""
    # skills/ jest obok tego pliku w pakiecie
    return Path(__file__).parent / "skills"


def load_skill(station_name: str) -> dict[str, Any]:
    """Ladowanie wbudowanego skilla stacji z pakietu.

    Zwraca slownik z kluczami: name, description, version, content, frontmatter.
    """
    skill_dir_name = STATION_TO_SKILL_DIR.get(station_name)
    if skill_dir_name is None:
        raise SkillNotFoundError(
            f"Stacja '{station_name}' nie ma mapowania na katalog skilla. "
            f"Dostepne: {list(STATION_TO_SKILL_DIR.keys())}"
        )

    skill_path = _get_skills_dir() / skill_dir_name / "SKILL.md"

    if not skill_path.exists():
        raise SkillNotFoundError(
            f"Plik skilla nie istnieje: {skill_path}"
        )

    skill_text = skill_path.read_text(encoding="utf-8")

    # Parsuj frontmatter
    frontmatter: dict[str, Any] = {}
    content = skill_text

    if skill_text.startswith("---"):
        parts = skill_text.split("---", 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1]) or {}
            content = parts[2].strip()

    return {
        "name": frontmatter.get("name", station_name),
        "description": frontmatter.get("description", ""),
        "version": frontmatter.get("version", ""),
        "content": content,
        "frontmatter": frontmatter,
    }


def get_skill_prompt(station_name: str, envelope_dict: dict[str, Any] | None = None) -> str:
    """Budowanie promptu dla stacji z wstrzyknieciem koperty."""
    skill = load_skill(station_name)
    skill_prompt = skill["content"]

    if envelope_dict:
        envelope_yaml = yaml.dump(
            envelope_dict,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )
        return f"""{skill_prompt}

---

AKTUALNA KOPERTA RUN'U:
{envelope_yaml}

WYKONAJ STACJE '{station_name}' NA PODSTAWIE POWYZSZEGO SKILLA I KOPERTY.
ZWROC WYJSCIE STACJI ORAZ ZAKONCZ BLOKIEM KOPERTA ZAKTUALIZOWANYM O TWOJE WYJSCIE.
"""
    return skill_prompt


def list_available_skills() -> list[str]:
    """Lista dostepnych wbudowanych skilli."""
    return list(STATIONS.keys())


def verify_skills_integrity() -> list[str]:
    """Weryfikuje integralnosc wbudowanych skilli. Zwraca liste bledow."""
    errors: list[str] = []
    skills_dir = _get_skills_dir()

    for station_name, skill_dir_name in STATION_TO_SKILL_DIR.items():
        skill_path = skills_dir / skill_dir_name / "SKILL.md"
        if not skill_path.exists():
            errors.append(f"Brak skilla dla stacji '{station_name}': {skill_path}")
            continue

        try:
            skill = load_skill(station_name)
            if not skill["content"]:
                errors.append(f"Pusty content skilla dla stacji '{station_name}'")
        except Exception as e:
            errors.append(f"Blad ladowania skilla '{station_name}': {e}")

    # Sprawdz pliki specyfikacji
    for spec_file in ["pipeline_sklills.md", "kontrakty_pipelines.md"]:
        path = skills_dir / spec_file
        if not path.exists():
            errors.append(f"Brak pliku specyfikacji: {path}")

    # Sprawdz _shared
    shared_dir = skills_dir / "_shared"
    if not shared_dir.exists():
        errors.append(f"Brak katalogu _shared: {shared_dir}")
    else:
        for shared_file in ["zrodla-i-narzedzia.md", "graf-pipeline.md"]:
            path = shared_dir / shared_file
            if not path.exists():
                errors.append(f"Brak pliku _shared: {path}")

    return errors
