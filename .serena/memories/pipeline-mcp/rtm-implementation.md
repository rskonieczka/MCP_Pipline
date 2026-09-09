# RTM (Requirements Traceability Matrix) - implementacja

## Decyzja D9 (2026-09-09)

RTM dodane jako modul + narzedzia MCP (Wariant A), nie jako nowa stacja.

**Dlaczego**: Pipeline nie mial formalnego sledzenia wymagan. RTM mapuje wymagania (ekstrahowane z `variables` typu `requirement` po `zmienne`) na stacje adresujace, weryfikujace i artefakty.

**Odrzucone**: Nowa stacja `rtm` (lamie 3 sciezki), tylko pole w Envelope (pasywne).

## Zakres (commits 82d8226, f5b9bde)

- Modul `rtm.py`, modele `RTMEntry`/`RTMStatus` w `models.py`
- Pole `rtm: list[RTMEntry]` w `Envelope` (opcjonalne, default puste)
- 4 narzedzia MCP: `get_rtm`, `update_rtm`, `add_rtm_entry`, `validate_rtm_coverage`
- Auto-aktualizacja w `execute_station` po `zmienne`/`realizuj`/`weryfikacja`/`sprawdzenie`
- Memgraph: wezel `:Wymaganie`, relacje `:ADRESUJE`, `:WERYFIKUJE` (`write_rtm_nodes`)
- 38 testow w `test_rtm.py` (total 55, wszystkie PASS)

## Statusy

`nieadresowane` -> `adresowane` -> `zrealizowane` -> `weryfikowane` / `niespelnione`

## Liczniki (2026-09-09)

17 modulow, 26 narzedzi MCP, 55 testow.