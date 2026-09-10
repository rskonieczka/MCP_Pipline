# Specyfikacja koperty (YAML envelope)

Koperta jest jedynym formalnym noznikiem danych miedzy stacjami pipeline'u. Zgodnie z `pipeline_sklills.md`, kontekst konwersacji sluzy wylacznie do uzasadnien i rozumowania, nie do przenoszenia pol kontraktu.

## 1. Struktura koperty

```yaml
KOPERTA:
  run_id: "<YYYY-MM-DD>-<skrot-zamiaru>"
  sciezka: szybki | pelny | doglebny
  stacja_aktualna: <nazwa-stacji>
  stacja_poprzednia: <nazwa-stacji> | null
  stan:                      # skumulowane pola kluczowe z wszystkich poprzednich stacji
    zamiar: ""
    klasyfikacja: ""
    punkt_wejscia: ""
  pola_stacji:               # wyjscia poszczegolnych stacji (kluczowe pola kontraktu)
    inicjuj:
      klasyfikacja: ""
      punkt_wejscia: ""
      uzasadnienie: ""
      ryzyka: []
    zmienne:
      variables: []
      relations: []
      sources_used: []
      missing_data_resolution: {}
      analysis_object:
        name: ""
    analiza:
      raport_streszczenie: ""
      pewnosc: ""
      ograniczenia: []
      wnioski: []
    dekompozycja:
      podproblemy: []
      zaleznosci: []
      kolejnosc: []
      krytyczne: []
    dobierz:
      status_doboru: ""
      metoda_doboru: ""
      warianty: []
      kryteria: []
      porownanie: {}
      rekomendacja: {}
      ryzyka_i_warunki_rewizji: []
      najblizszy_krok: ""
    routing:
      sciezka: ""
      stawka: ""
      ryzyko: ""
      stacje_uruchomione: []
      stacje_pominiete: []
      stacje_poglebione: []
    planuj:
      cel: ""
      sytuacja: ""
      kroki: []
      zasoby: []
      ryzyka: []
      kryteria_sukcesu: []
      punkty_kontrolne: []
    realizuj:
      kroki_wykonane: []
      kroki_pominiete: []
      kroki_zablokowane: []
      zmiany: []
      status: ""
    weryfikacja:
      werdykty: []
      konflikty_zrodel: []
      braki_dowodowe: []
      podsumowanie: ""
    sprawdzenie:
      status_audytu: ""
      ocena_calkowita: ""
      werdykt: ""
      wymiary: {}
      poprawiona_odpowiedz: ""
    ewaluacja:
      typ_ewaluacji: ""
      ocena_ogolna: ""
      wymiary: {}
      wnioski: []
      rekomendacje: []
      status: ""
    utrwal:
      typ_wiedzy: ""
      miejsca_zapisu: []
      akcje: []
      status: ""
    monitoruj:
      checkpointy: []
      blokady: []
      odchylenia: []
      warunki_przejscia: []
      status: ""
  walidacja:                 # walidacja kompletnosci przed przejsciem do stacji nastepnej
    stacja_docelowa: <nazwa-stacji>
    pola_wymagane: []         # z kontraktu wejscia stacji docelowej
    pola_obecne: []
    pola_brakujace: []
    status: gotowy | wnioskowane | niekompletne
    akcja_naprawcza: ""       # gdy niekompletne: pytanie do uzytkownika / agent_inference / powrot
  relacje:                    # jawne relacje miedzy encjami w run'ie (zapisywane do Memgraph)
    - zrodlo: "stacja:analiza"
      cel: "stacja:zmienne"
      typ: nastapila_po
      pola: [analysis_object.name]
    - zrodlo: "zmienna:V001"
      cel: "zmienna:V003"
      typ: zalezy_od
  rtm:                       # Requirements Traceability Matrix - sledzenie wymagan
    - req_id: "REQ-001"
      opis: "Opis wymagania"
      zrodlo: "zmiar"         # zrodlo: zamiar | zmienne | kontekst | zrodla | agent_inference
      stacje_adresujace: ["zmienne"]  # stacje odpowiedzialne za to wymaganie
      stacja_weryfikujaca: "weryfikacja"  # stacja weryfikujaca
      stacja_niespelnienia: ""    # stacja, ktora oznaczyla wymaganie jako niespelnione (U6)
      status: "adresowane"    # nieadresowane | adresowane | zrealizowane | weryfikowane | niespelnione
      artefakty: []           # linki do wyjsc stacji (pola_stacji.<stacja>.<pole>)
      checkpoint_weryfikacji: ""  # ktory checkpoint potwierdza
  wejscie:                    # wejscie uzytkownika z start_run (U8)
    kontekst: ""
    zrodla: []
    tryb_inicjacji: ""
  client_id: ""               # identyfikator klienta (pusty = tryb legacy)
  timestamp: ""               # timestamp ostatniej aktualizacji
```

## 2. Zasady koperty

### 2.1. Emituj na koncu

Kazda stacja merytoryczna konczy wyjscie blokiem `KOPERTA`. Serwer po wywolaniu `execute_station` aktualizuje koperte na podstawie przekazanego wyjscia stacji.

### 2.2. Konsumuj na poczatku

Stacja nastepna rozpoczyna od odczytu koperty z wyjscia poprzedniej stacji. Serwer udostepnia koperte przez narzedzie `get_envelope`.

### 2.3. Kumuluj stan

Sekcja `stan` zawiera pola kluczowe skumulowane ze wszystkich poprzednich stacji. Sekcja `pola_stacji` zawiera wyjscia poszczegolnych stacji w sekcjach nazwanych wedlug stacji.

Pola kumulowane w `stan`:
- `zamiar` - od `inicjuj` (niezmienne przez caly run)
- `klasyfikacja` - od `inicjuj`
- `punkt_wejscia` - od `inicjuj`

### 2.4. Waliduj przed przejsciem

Przed przekazaniem do stacji nastepnej serwer sprawdza `pola_wymagane` vs `pola_obecne`. Jesli brakuje pol wymaganych, ustawia `status: niekompletne` i wskazuje `akcja_naprawcza`.

Statusy walidacji:
- `gotowy` - wszystkie pola wymagane obecnne bezposrednio
- `wnioskowane` - brakujace pola moga byc wyprowadzone przez `agent_inference`
- `niekompletne` - brakuje pol wymaganych, potrzebna interwencja

### 2.5. Nie duplikuj w kontekscie

Pola kontraktowe przekazywane wylacznie przez koperte, nie przez powtarzanie w tresci konwersacji. Serwer wymusza to przez walidacje `execute_station`.

### 2.6. Kompresuj w sciezce doglebny

Po stacjach `analiza`, `dobierz`, `sprawdzenie` serwer moze usunac starsze sekcje `pola_stacji` z koperty w kontekscie konwersacji, jesli zostaly zapisane w checkpoincie. Pozostawia tylko `stan` i sekcje stacji biezacej.

## 3. Cykl zycia koperty

```
1. start_run -> pusta koperta (stan.zamiar = zamiar)
2. execute_station("inicjuj", output) -> koperta z pola_stacji.inicjuj
3. execute_station("zmienne", output) -> koperta z pola_stacji.zmienne
4. ... kolejne stacje ...
5. quality_gate -> ewentualny powrot (nowy checkpoint z sufiksem _iter<N>)
6. close_run -> ostateczna koperta zapisana jako envelope_final.yaml
```

## 4. Relacje w kopercie

Sekcja `relacje` zawiera jawne relacje miedzy encjami w run'ie. Po kazdej stacji serwer zapisuje te relacje do Memgraph.

Typy relacji:
- `nastapila_po` - stacja nastapila po innej stacji
- `zawiera` - run zawiera stacje
- `wyprodukowala` - stacja wyprodukowala zmienna/decyzje/werdykt
- `zalezy_od` - zmienna zalezy od innej zmiennej
- `oparta_na` - decyzja oparta na zmiennnej
- `dotyczy` - werdykt dotyczy twierdzenia
- `wyprowadzony_z` - wniosek wyprowadzony z analizy
- `rozwiuzyje` - podproblem rozwiuzyje problem
- `realizuje` - krok planu realizuje cel
- `weryfikuje` - weryfikacja weryfikuje twierdzenie
- `zapisana_w` - encja zapisana w checkpoincie
- `kontynuacja` - run jest kontynuacja innego run'u
- `naprawia` - run naprawia inny run
- `ponowne_uruchomienie` - run jest ponownym uruchomieniem
- `ADRESUJE` - stacja adresuje wymaganie (Stacja -> Wymaganie, z RTM)
- `WERYFIKUJE` - stacja weryfikuje wymaganie (Stacja -> Wymaganie, z RTM)

## 5. Implementacja w serwerze

Koperta jest reprezentowana przez model Pydantic `Envelope` w `models.py`:

```python
class Envelope(BaseModel):
    run_id: str
    sciezka: Literal["szybki", "pelny", "doglebny"]
    stacja_aktualna: str
    stacja_poprzednia: str | None
    stan: Stan
    pola_stacji: dict[str, dict]
    walidacja: Walidacja
    relacje: list[Relacja]
    rtm: list[RTMEntry]            # Requirements Traceability Matrix
    wejscie: dict                  # wejscie uzytkownika z start_run (U8)
    client_id: str                 # identyfikator klienta (pusty = legacy)
    timestamp: str                 # timestamp ostatniej aktualizacji
```

Model `RTMEntry` w `models.py`:

```python
class RTMEntry(BaseModel):
    req_id: str                    # identyfikator wymagania (np. "REQ-001")
    opis: str = ""                 # opis wymagania
    zrodlo: str = "zamiar"         # zrodlo pochodzenia
    stacje_adresujace: list[str]   # stacje odpowiedzialne za adresowanie
    stacja_weryfikujaca: str = ""  # stacja weryfikujaca
    stacja_niespelnienia: str = "" # stacja oznaczajaca niespelnienie (U6, nie nadpisuje stacja_weryfikujaca)
    status: RTMStatus = "nieadresowane"  # status sledzenia
    artefakty: list[str]           # linki do artefaktow (pola_stacji.<stacja>.<pole>)
    checkpoint_weryfikacji: str = ""  # checkpoint potwierdzajacy
```

Statusy `RTMStatus`: `nieadresowane` -> `adresowane` -> `zrealizowane` -> `weryfikowane` / `niespelnione`.

Operacje na kopercie w `envelope.py`:
- `create_envelope(run_id, zamiar, sciezka, client_id)` - inicjalna koperta
- `update_station_fields(envelope, station, output)` - aktualizacja `pola_stacji.<station>`
- `accumulate_state(envelope, station, output)` - kumulacja pol w `stan`
- `validate_transition(envelope, target_station)` - walidacja przed przejsciem
- `compress_envelope(envelope, keep_last_n=3)` - kompresja w sciezce doglebny
- `serialize_envelope(envelope)` - serializacja do YAML
- `deserialize_envelope(yaml_str)` - deserializacja z YAML
