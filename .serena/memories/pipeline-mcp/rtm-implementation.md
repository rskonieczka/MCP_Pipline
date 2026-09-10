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

## Liczniki (2026-09-10, po dodaniu wieloklientowosci D10)

21 modulow, ~49 narzedzi MCP, 131 testow. Node IDs Memgraph dla Wymaganie zawieraja client_id: `wymaganie:<client_id>:<run_id>:<req_id>`.