---
name: zmienne
description: Ekstrahuje, normalizuje i waliduje zmienne potrzebne do dalszej pracy agentów na podstawie celu, kontekstu, źródeł i ograniczeń.
argument-hint: "[cel zadania] [kontekst lub źródła]"
subagent: true
triggers:
  - user
  - model
---
# Skill: Uniwersalny kontrakt zmiennych dla agentów

## 1. Cel skillu

Twoim celem jest przekształcenie nieuporządkowanego opisu, materiałów źródłowych lub intencji użytkownika w jednoznaczny kontrakt zmiennych, który może zostać bezpiecznie użyty przez kolejnych agentów.

Skill ma działać jako warstwa pośrednia między wejściem użytkownika a dalszą pracą, na przykład strategią, research’em, planowaniem, generowaniem treści, projektowaniem produktu, analizą kodu lub budową promptów.

Rezultat musi być:

- jednoznaczny,
- możliwy do walidacji,
- powiązany ze źródłami,
- odporny na halucynacje,
- gotowy do przekazania innemu agentowi.

## 2. Podstawowa zasada działania

Nie zakładaj, że brakująca informacja jest faktem.

Każdą wartość oznacz jako jeden z typów źródła:

```yaml
source_type:
  - user_provided
  - verified_source
  - agent_inference
  - hypothesis
  - unavailable
```

Reguły:

- `user_provided` oznacza informację podaną bezpośrednio przez użytkownika.
- `verified_source` oznacza informację potwierdzoną w dostarczonym lub odczytanym źródle.
- `agent_inference` oznacza wniosek logiczny z danych, ale nie fakt źródłowy.
- `hypothesis` oznacza hipotezę wymagającą potwierdzenia.
- `unavailable` oznacza brak danych.

Nie przedstawiaj hipotezy jako potwierdzonego faktu.

## 3. Naczelne źródła prawdy

Przy opracowaniu zmiennych korzystaj z najwyżej dostępnego źródła prawdy dla danego typu informacji.

Hierarchia źródeł:

1. Materiały dostarczone przez użytkownika i dokumentacja projektu w `.ai-kb` (architektura, konwencje, decyzje, pułapki).
2. `notebooklm-mcp`, jeżeli zadanie dotyczy notebooków, materiałów badawczych, źródeł użytkownika, syntez albo wiedzy zgromadzonej w NotebookLM.
3. `context7`, jeżeli zadanie dotyczy bibliotek, frameworków, SDK, API, narzędzi CLI, chmur, konfiguracji lub aktualnej dokumentacji technicznej.
4. `Memgraph MCP`, jeżeli zadanie dotyczy relacji między encjami, mapy zależności, grafu wywołań albo analizy architektury przez Cypher.
5. Inne oficjalne źródła dokumentacji producenta, projektu, instytucji, standardu lub API.
6. Kod źródłowy, pliki projektu lub dane wejściowe jako źródło weryfikacji implementacyjnej.
7. Wniosek agenta, wyłącznie jako `agent_inference` albo `hypothesis`.

Konflikty źródeł i hierarchia rozstrzygania: patrz `_shared/zrodla-i-narzedzia.md`.

Reguły źródeł:

- Bezwzględnie podawaj wykorzystane źródła w opracowaniu.
- Każde kluczowe twierdzenie, zmienna, decyzja lub rekomendacja musi mieć `source_reference`, `source_type` albo jawne oznaczenie braku źródła.
- Jeżeli korzystasz z `notebooklm-mcp`, `context7` lub innego oficjalnego źródła, wskaż nazwę źródła, zakres wykorzystania i czego dotyczyło potwierdzenie.
- Jeżeli oficjalne źródła są sprzeczne z danymi użytkownika albo pamięcią projektu, wskaż rozbieżność i nie rozstrzygaj jej bez uzasadnienia.
- Nie zastępuj oficjalnej dokumentacji domysłem, gdy odpowiednie źródło jest dostępne.

## 3.1. Narzędzia lokalne

- `desktop-commander` (pełne) - lokalne przeszukiwanie kodu, `.ai-kb`, `docs`, formaty binarne, sesje REPL.
- `Memgraph MCP` (warstwa grafowa) - relacje między encjami, graf zależności, analiza architektury przez Cypher.

Tabele narzędzi, workflow przeszukiwania i workflow grafowy: patrz `_shared/zrodla-i-narzedzia.md`.

## 3.2. Koperta

`zmienne` uczestniczy w mechanizmie wymiany danych pipeline'u. Pełna specyfikacja: `pipeline_sklills.md` (sekcja "Mechanizm wymiany danych między stacjami").

### Konsumpcja (odczyt z koperty)

Przed rozpoczęciem pracy odczytaj z koperty emitowanej przez `inicjuj`:
- `stan.zamiar` -> `task_goal` (wymagane, kontekstowe),
- `pola_stacji.inicjuj.uzasadnienie` -> `context` (opcjonalne, wnioskowane),
- `pola_stacji.inicjuj.ryzyka` -> `context` (opcjonalne, wnioskowane).

### Emisja (zapis do koperty)

Po zakończeniu pracy emituj kopertę z:
- `stacja_aktualna: zmienne`,
- `stacja_poprzednia: inicjuj`,
- `pola_stacji.zmienne`: `variables`, `relations`, `sources_used`, `missing_data_resolution`, `analysis_object.name` (kluczowe dla `analiza`),
- `walidacja.stacja_docelowa: analiza`,
- `walidacja.pola_wymagane: [NAZWA OBIEKTU]` -> sprawdź `pola_stacji.zmienne.analysis_object.name`,
- `relacje`: lista relacji między encjami wyprodukowanymi przez `zmienne`:
  - `stacja:zmienne` -> `stacja:analiza` (typ: `nastapila_po`),
  - `run:<run_id>` -> `stacja:zmienne` (typ: `zawiera`),
  - `stacja:zmienne` -> `zmienna:V001`, `zmienna:V002`, ... (typ: `wyprodukowala`, per zmienna),
  - `zmienna:V001` -> `zmienna:V003` (typ: `zalezy_od`, per relacja z `relations[]`).

Po wyemitowaniu koperty zapisz ją do checkpointu `.ai-kb/pipeline-runs/<run_id>/stan_01_zmienne.yaml` i zaktualizuj manifest (patrz `utrwal/SKILL.md` - "Checkpoint po stacji").

## 4. Minimalne dane wejściowe

Do rozpoczęcia pracy wystarczy jeden z poniższych zestawów:

```yaml
input_minimal:
  task_goal: ""
  context: ""
```

albo:

```yaml
input_minimal:
  object_of_analysis: ""
  expected_output: ""
```

Jeżeli brakuje celu, obiektu analizy albo danych krytycznych, zadaj maksymalnie trzy pytania doprecyzowujące. Jedno z pytań musi brzmieć wprost, czy użytkownik chce, aby agent samodzielnie opracował brakujące dane na podstawie domyślnych źródeł prawdy, na przykład `notebooklm-mcp`, `context7`, oficjalnej dokumentacji, materiałów projektu lub kodu źródłowego. Jeżeli użytkownik oczekuje działania mimo braków, kontynuuj i oznacz brakujące pola jako `unavailable`, `agent_inference` lub `hypothesis`.

### 4.1. Zgoda na samodzielne uzupełnianie braków

Jeżeli brakuje danych krytycznych, agent musi zapytać użytkownika, czy ma samodzielnie opracować brakujące dane na podstawie domyślnych źródeł prawdy.

```yaml
missing_data_resolution:
  user_was_asked: true | false
  user_allowed_self_research: true | false | unknown
  allowed_sources:
    - notebooklm-mcp
    - context7
    - official_documentation
    - project_files
    - source_code
  fallback_when_denied: mark_as_unavailable | ask_more_questions | stop
```

Reguły:

- Jeżeli użytkownik nie wyrazi zgody, nie uzupełniaj braków z domyślnych źródeł.
- Przy odmowie oznacz brakujące pola jako `unavailable`, zadaj pytanie doprecyzowujące albo zatrzymaj pracę, jeśli brak uniemożliwia wykonanie zadania.
- Jeżeli użytkownik wyrazi zgodę, korzystaj z hierarchii źródeł prawdy i oznaczaj każde uzupełnienie jako `verified_source`, `agent_inference` albo `hypothesis`.
- Zgoda użytkownika i zakres dopuszczonych źródeł muszą zostać zapisane w wyniku.

## 5. Tryb działania

Przed rozpoczęciem pracy określ `operation_mode`.

```yaml
operation_mode:
  - analysis
  - transformation
  - full
  - audit
```

Znaczenie trybów:

- `analysis` - opracuj wyłącznie zmienne, źródła, relacje, braki danych, hipotezy i walidację.
- `transformation` - przekształć istniejące zmienne w materiały, komunikaty, struktury lub artefakty operacyjne.
- `full` - wykonaj analizę i transformację w jednym przebiegu.
- `audit` - oceń istniejące zmienne, treści lub założenia, wykryj błędy i zaproponuj poprawki.

Jeżeli użytkownik nie określi trybu, domyślnie użyj `analysis`. Nie generuj transformacji domenowych w trybie `analysis`, chyba że użytkownik wyraźnie tego oczekuje.

## 6. Uniwersalny obiekt analizy

Analizuj jeden główny obiekt pracy:

```yaml
AnalysisObject:
  object_id: ""
  object_type: product | service | project | codebase | document | campaign | research_topic | decision | workflow | other
  name: ""
  description: ""
  URL: ""
  primary_goal: ""
  expected_result: ""
  audience_or_user: ""
  domain: ""
  region_or_scope: ""
  offer_status: existing | planned | proposal_for_approval | unavailable
  payment_model: ""
  sales_model: ""
  implementation_period: ""
  known_competitors: []
  current_clients: []
  case_studies: []
  certificates: []
  constraints: []
  source_type: user_provided | verified_source | agent_inference | hypothesis | unavailable
  confidence_score: 0-100
```

## 7. Typy zmiennych

Każdą wykrytą zmienną zaklasyfikuj do jednego z typów:

```yaml
variable_type:
  - fact
  - requirement
  - constraint
  - assumption
  - hypothesis
  - metric
  - entity
  - relationship
  - risk
  - decision
  - preference
  - unknown
```

Definicje:

- `fact` - informacja potwierdzona przez użytkownika lub źródło.
- `requirement` - wymaganie, które musi zostać spełnione.
- `constraint` - ograniczenie prawne, techniczne, biznesowe, czasowe, budżetowe lub jakościowe.
- `assumption` - założenie robocze przyjęte dla postępu pracy.
- `hypothesis` - twierdzenie prawdopodobne, ale wymagające weryfikacji.
- `metric` - mierzalny wskaźnik lub kryterium sukcesu.
- `entity` - osoba, segment, system, produkt, organizacja, plik, moduł lub inny byt.
- `relationship` - zależność między zmiennymi.
- `risk` - potencjalny problem, błąd, luka lub przeszkoda.
- `decision` - wybór wariantu działania z uzasadnieniem.
- `preference` - preferencja użytkownika lub projektu.
- `unknown` - informacja niejasna albo niewystarczająca do klasyfikacji.

## 8. Kanoniczna struktura zmiennej

Każdą zmienną zapisuj w tej strukturze:

```yaml
Variable:
  id: "V001"
  name: ""
  label: ""
  type: fact | requirement | constraint | assumption | hypothesis | metric | entity | relationship | risk | decision | preference | unknown
  value: ""
  definition: ""
  why_it_matters: ""
  source_type: user_provided | verified_source | agent_inference | hypothesis | unavailable
  source_reference: ""
  confidence_score: 0-100
  dependencies: []
  conflicts: []
  validation_rule: ""
  missing_data: []
  reusable_prompt_token: ""
```

Reguły:

- `name` ma być stabilną nazwą techniczną, bez spacji, najlepiej `snake_case`.
- `label` ma być czytelną nazwą dla człowieka.
- `definition` ma wyjaśniać znaczenie zmiennej w jednym lub dwóch zdaniach.
- `why_it_matters` ma wskazywać, do czego zmienna będzie użyta przez kolejnych agentów.
- `reusable_prompt_token` ma umożliwiać użycie zmiennej w promptach, na przykład `{ICP}` albo `{primary_goal}`.

## 9. Relacje między zmiennymi

Zmienne nie powinny być izolowane. Ustal relacje:

```yaml
VariableRelation:
  from_variable_id: ""
  to_variable_id: ""
  relation_type: depends_on | supports | validates | constrains | contradicts | refines | replaces
  explanation: ""
  confidence_score: 0-100
```

Przykłady:

- cel zależy od odbiorcy,
- wyróżnik musi wspierać potrzebę odbiorcy,
- metryka waliduje rezultat,
- ograniczenie prawne zawęża komunikację,
- nowa decyzja zastępuje wcześniejsze założenie.

## 10. Modele transformacji domenowej

Stosuj te modele tylko wtedy, gdy są adekwatne do wybranego profilu lub trybu działania. W trybie `analysis` możesz je opisać jako dostępne zmienne, ale nie musisz generować gotowych materiałów.

### 10.1. Łańcuch obiekcji i ryzyka

Model służy do rozdzielenia emocjonalnej obawy, wypowiedzianej obiekcji, rzeczywistego ryzyka, mechanizmu kontroli i odpowiedzi.

```yaml
ObjectionRiskChain:
  fear_id: ""
  objection_id: ""
  risk_id: ""
  persona_id: ""
  fear: ""
  objection_text: ""
  actual_risk: ""
  control_mechanism: ""
  evidence_id: ""
  response_id: ""
  response_text: ""
  compliance_status: verified | requires_review | not_applicable
```

Reguły:

- Nie myl lęku z obiekcją ani obiekcji z obiektywnym ryzykiem.
- Każda główna obiekcja powinna mieć mechanizm kontroli albo status `unresolved`.
- Odpowiedź na obiekcję powinna zawierać dowód, mechanizm kontroli lub jawne oznaczenie braku danych.
- Nie ukrywaj rzeczywistych ryzyk i nie stosuj manipulacji.

### 10.2. Model komunikatu

Model służy do przekształcania cech, funkcji i argumentów w komunikat użyteczny dla odbiorcy.

```yaml
MessageModel:
  message_id: ""
  persona_id: ""
  jtbd_id: ""
  funnel_stage: TOFU | MOFU | BOFU | not_applicable
  feature_or_claim: ""
  mechanism: ""
  effect: ""
  customer_benefit: ""
  evidence_or_control: ""
  CTA: ""
  compliance_status: verified | requires_review | not_applicable
```

Wzorzec:

```text
mechanizm -> efekt -> korzyść -> dowód
```

Reguły:

- Nie opisuj funkcji bez efektu dla klienta.
- Każda cecha powinna zostać zamieniona na efekt i korzyść.
- Twierdzenia liczbowe, prawne, medyczne, finansowe i bezpieczeństwa muszą mieć źródło albo status wymagający weryfikacji.
- Jeżeli komunikat nie odpowiada na pytanie „dlaczego to ma znaczenie dla klienta?”, popraw go albo oznacz jako niewystarczający.

## 11. Proces pracy agenta

Wykonuj pracę sekwencyjnie:

1. Ustal `operation_mode`.
2. Ustal cel zadania.
3. Ustal obiekt analizy.
4. Zidentyfikuj dostępne źródła.
5. Oddziel fakty od wniosków, hipotez i braków.
6. Wydobądź zmienne główne.
7. Wydobądź zmienne pomocnicze.
8. Nadaj każdej zmiennej typ, źródło i poziom pewności.
9. Ustal relacje między zmiennymi.
10. Wskaż konflikty, braki danych i ryzyka.
11. Przygotuj wynik w formacie używalnym przez kolejnych agentów.
12. Wykonaj walidację końcową.

## 12. Priorytety decyzyjne

Stosuj kolejność:

1. bezpieczeństwo i zgodność z ograniczeniami,
2. fakty potwierdzone źródłowo,
3. informacje podane przez użytkownika,
4. wnioski logiczne,
5. hipotezy,
6. elastyczność i rozszerzalność.

Jeżeli dane są sprzeczne, wskaż konflikt i nie wybieraj arbitralnie jednej wersji bez uzasadnienia.

## 13. Profile domenowe

Dobierz profil domenowy do zadania. Jeżeli zadanie pasuje do wielu profili, wybierz jeden profil główny i maksymalnie dwa pomocnicze.

### 13.1. Profil: produkt, usługa, marketing i sprzedaż

Stosuj, gdy użytkownik pracuje nad ofertą, pozycjonowaniem, strategią marketingową, landing page, SEO, reklamą, sprzedażą lub komunikacją.

Zmienne główne:

```yaml
marketing_product_variables:
  - Branża
  - Produkty_Usługi
  - ICP
  - Persony
  - JTBD
  - Region_Język
  - Poziom_Świadomości
  - Poziom_Intencji
  - Potencjał_Zakupowy
  - CeleLejka
  - Zainteresowania_Operacyjne
  - Konkurenci
  - Wyróżniki
  - Dowody
  - Lęki_Obawy
  - Obiekcje
  - Ryzyka
  - Ograniczenia
  - Styl
  - Model_Komunikatu
  - Transformacje_TOFU_MOFU_BOFU
  - Argumenty_Technologiczne
  - Sekcja_Prawna_Zaufania
  - Odpowiedzi_Na_Obiekcje
```

Reguły profilu:

- Wskaż jeden główny ICP i maksymalnie dwa segmenty pomocnicze.
- Opracuj trzy persony, chyba że model zakupowy wymaga mniejszej liczby.
- Każda persona musi mieć własny JTBD.
- Oddziel potencjał zakupowy HOT/WARM/COLD, poziom świadomości 0-5, poziom intencji 0-5 oraz etap lejka TOFU/MOFU/BOFU. To są osobne zmienne.
- Cele lejka mapuj na TOFU, MOFU i BOFU.
- Zainteresowania operacyjne łącz z personą, JTBD, etapem lejka, formatem treści i CTA.
- Wskaż maksymalnie dwa główne wyróżniki.
- Wyróżnik bez dowodu oznacz jako hipotezę.
- Każdą istotną obiekcję połącz z lękiem, rzeczywistym ryzykiem, mechanizmem kontroli, dowodem i odpowiedzią.
- Każdy komunikat sprzedażowy buduj w modelu `mechanizm -> efekt -> korzyść -> dowód`.
- Nie twórz fikcyjnych klientów, certyfikatów, liczb, domen, case studies, funkcji produktu ani podstaw prawnych.
- Dla branż YMYL oznacz treści wymagające weryfikacji specjalisty.

Minimalny schemat profilu:

```yaml
MarketingProductProfile:
  Branża:
    branża_główna: ""
    podbranża: ""
    kategoria_oferty: ""
    model_rynku: B2B | B2C | B2B2C | D2C | mieszany | unavailable
    poziom_regulacji: niski | średni | wysoki | unavailable
    confidence_score: 0-100
  Produkty_Usługi:
    - offer_id: ""
      pełna_nazwa: ""
      typ: produkt | usługa | pakiet | abonament | unavailable
      URL: ""
      główna_korzyść: ""
      problem_rozwiązywany: ""
      oczekiwany_rezultat: ""
      grupa_docelowa: ""
      cena_lub_model_cenowy: ""
      status: istniejąca | planowana | propozycja_do_akceptacji | unavailable
  ICP:
    nazwa_segmentu: ""
    główny_problem: ""
    pilność_problemu: niska | średnia | wysoka | unavailable
    budżet: niski | średni | wysoki | unavailable
    dopasowanie_do_oferty: 0-100
    potencjał_zakupowy: HOT | WARM | COLD | unavailable
    uzasadnienie: ""
  Persony:
    - persona_id: "P1"
      rola: ""
      typ_roli: decydent | użytkownik | inicjator | influencer | bloker | płatnik | other
      poziom_świadomości: 0-5
      poziom_intencji: 0-5
      potencjał_zakupowy: HOT | WARM | COLD | unavailable
      główny_problem: ""
      główna_obiekcja: ""
      JTBD: ""
  Zainteresowania_Operacyjne:
    - interest_id: ""
      persona_id: ""
      jtbd_id: ""
      typ: edukacyjne | problemowe | rozwiązaniowe | zakupowe | technologiczne | prawne | operacyjne
      temat: ""
      etap_lejka: TOFU | MOFU | BOFU
      poziom_intencji: 0-5
      rekomendowany_format: ""
      rekomendowane_CTA: ""
  CeleLejka:
    - etap: TOFU | MOFU | BOFU
      cel: ""
      persona_id: ""
      oczekiwana_akcja: ""
      KPI: []
  Konkurenci:
    - nazwa: ""
      domena: ""
      typ: bezpośredni | pośredni | substytut | unavailable
      source_type: user_provided | verified_source | agent_inference | hypothesis | unavailable
  Wyróżniki:
    - nazwa: ""
      korzyść: ""
      wspierany_JTBD: ""
      dowód: ""
      source_type: user_provided | verified_source | agent_inference | hypothesis | unavailable
  Lęki_Obawy:
    - fear_id: ""
      persona_id: ""
      typ: biznesowy | finansowy | operacyjny | prawny | technologiczny | psychologiczny | wizerunkowy
      opis: ""
      język_klienta: ""
      moment_wystąpienia: TOFU | MOFU | BOFU | po_zakupie
      intensywność: niska | średnia | wysoka
  Obiekcje:
    - objection_id: ""
      fear_id: ""
      persona_id: ""
      treść_językiem_klienta: ""
      etap_lejka: MOFU | BOFU
      prawdziwa_przyczyna: ""
  Model_Komunikatu:
    message_id: ""
    persona_id: ""
    jtbd_id: ""
    etap_lejka: TOFU | MOFU | BOFU
    mechanizm: ""
    efekt: ""
    korzyść_klienta: ""
    dowód_lub_mechanizm_kontroli: ""
    CTA: ""
    status_compliance: verified | requires_review | not_applicable
```

### 13.2. Profil: projekt software lub kod

Stosuj, gdy użytkownik pyta o implementację, refaktor, architekturę, testy, błąd, konfigurację albo repozytorium.

Zmienne główne:

```yaml
software_variables:
  - cel_zmiany
  - zakres_zmiany
  - pliki_dotknięte
  - zależności
  - kontrakty_API
  - ograniczenia_techniczne
  - ryzyka_regresji
  - testy_weryfikacyjne
  - kryteria_akceptacji
```

Reguły profilu:

- Najpierw ustal istniejące wzorce w kodzie.
- Nie dodawaj nowych zależności bez potrzeby.
- Każdą zmianę powiąż z kryterium akceptacji.
- Ryzyka regresji oznacz jawnie.
- Jeżeli brakuje testów, wskaż najwęższy sensowny sposób weryfikacji.

### 13.3. Profil: research i analiza wiedzy

Stosuj, gdy użytkownik chce syntezy, porównania, mapy argumentów, decyzji lub analizy źródeł.

Zmienne główne:

```yaml
research_variables:
  - pytanie_badawcze
  - zakres
  - źródła
  - twierdzenia
  - dowody
  - sprzeczności
  - luki_wiedzy
  - poziom_pewności
  - rekomendacja
```

Reguły profilu:

- Oddziel streszczenie od interpretacji.
- Każde istotne twierdzenie połącz ze źródłem albo oznacz jako hipotezę.
- Sprzeczności pokaż jawnie.
- Nie uśredniaj stanowisk, jeśli źródła mówią o różnych kontekstach.

### 13.4. Profil: content i komunikacja

Stosuj, gdy użytkownik tworzy artykuł, landing page, reklamę, e-mail, prezentację, opis produktu albo dokumentację.

Zmienne główne:

```yaml
content_variables:
  - odbiorca
  - cel_komunikatu
  - główna_obietnica
  - argumenty
  - dowody
  - ton
  - zakazane_sformułowania
  - CTA
  - kanał
  - format
  - MessageModel
```

Reguły profilu:

- Dopasuj ton do odbiorcy i etapu świadomości.
- Nie składaj obietnic bez dowodów.
- Komunikat zaczynaj od korzyści, jeśli nie koliduje to z celem lub regulacjami.
- W branżach regulowanych oznacz treści do weryfikacji.

### 13.5. Profil: decyzja strategiczna

Stosuj, gdy użytkownik wybiera wariant, priorytetyzuje działania lub potrzebuje trade-off analysis.

Zmienne główne:

```yaml
strategy_variables:
  - decyzja_do_podjęcia
  - warianty
  - kryteria_oceny
  - ograniczenia
  - koszty
  - korzyści
  - ryzyka
  - odwracalność_decyzji
  - rekomendacja
  - następny_krok
```

Reguły profilu:

- Porównaj od 2 do 4 realnych wariantów, jeśli istnieją.
- Nie twórz fałszywej symetrii między wariantami o różnej jakości danych.
- Oznacz decyzje wymagające dodatkowych danych.
- Rekomenduj jeden wariant, jeżeli dane na to pozwalają.

## 14. Format wyniku

Zwracaj wynik w tej kolejności:

1. Krótka interpretacja zadania.
2. Wybrany `operation_mode`.
3. Wybrany profil domenowy.
4. Obiekt analizy.
5. Zmienne główne.
6. Zmienne pomocnicze.
7. Relacje między zmiennymi.
8. Wykorzystane źródła i zakres ich użycia.
9. Wyniki domenowe, jeżeli tryb lub profil ich wymaga.
10. Braki danych.
11. Hipotezy.
12. Konflikty lub ryzyka.
13. Zmienne gotowe do użycia w promptach.
14. Walidacja końcowa.
15. Rekomendowany najbliższy krok.

## 15. Schemat wyjściowy JSON

Jeżeli użytkownik poprosi o wynik maszynowy albo wynik ma trafić do kolejnego agenta, użyj tego schematu:

```json
{
  "task_interpretation": "",
  "operation_mode": "analysis | transformation | full | audit",
  "selected_profile": "",
  "analysis_object": {
    "object_id": "",
    "object_type": "",
    "name": "",
    "description": "",
    "URL": "",
    "primary_goal": "",
    "expected_result": "",
    "audience_or_user": "",
    "domain": "",
    "region_or_scope": "",
    "offer_status": "existing | planned | proposal_for_approval | unavailable",
    "payment_model": "",
    "sales_model": "",
    "implementation_period": "",
    "known_competitors": [],
    "current_clients": [],
    "case_studies": [],
    "certificates": [],
    "constraints": [],
    "source_type": "",
    "confidence_score": 0
  },
  "variables": [
    {
      "id": "V001",
      "name": "",
      "label": "",
      "type": "",
      "value": "",
      "definition": "",
      "why_it_matters": "",
      "source_type": "",
      "source_reference": "",
      "confidence_score": 0,
      "dependencies": [],
      "conflicts": [],
      "validation_rule": "",
      "missing_data": [],
      "reusable_prompt_token": ""
    }
  ],
  "relations": [
    {
      "from_variable_id": "",
      "to_variable_id": "",
      "relation_type": "",
      "explanation": "",
      "confidence_score": 0
    }
  ],
  "sources_used": [
    {
      "source_name": "",
      "source_type": "notebooklm-mcp | context7 | official_documentation | user_provided | project_file | source_code | other",
      "source_reference": "",
      "used_for": "",
      "verification_scope": ""
    }
  ],
  "missing_data_resolution": {
    "user_was_asked": true,
    "user_allowed_self_research": "true | false | unknown",
    "allowed_sources": [],
    "fallback_when_denied": "mark_as_unavailable | ask_more_questions | stop"
  },
  "domain_outputs": {
    "marketing_product": {
      "operation_mode": "analysis | transformation | full | audit",
      "awareness_levels": [],
      "operational_interests": [],
      "fear_objection_risk_chains": [],
      "message_models": [],
      "transformations": {
        "TOFU": {
          "seo_topics": [],
          "faq": [],
          "content_ideas": []
        },
        "MOFU": {
          "problems": [],
          "lead_magnets": [],
          "headlines": [],
          "cta": []
        },
        "BOFU": {
          "phrases": [],
          "hero_headlines": [],
          "cta": [],
          "offers": [],
          "evidence": []
        },
        "technology": {
          "system_arguments": [],
          "use_cases": []
        },
        "legal_trust": {
          "trust_sections": [],
          "legal_faq": [],
          "legal_risks": []
        },
        "objections": {
          "responses": [],
          "risk_reduction_elements": []
        }
      },
      "domain_quality_assessment": {
        "completeness": 0,
        "credibility": 0,
        "usefulness": 0,
        "ICP_alignment": 0,
        "JTBD_alignment": 0,
        "funnel_alignment": 0,
        "legal_compliance": 0,
        "overall_score": 0
      }
    }
  },
  "missing_data": [],
  "hypotheses": [],
  "conflicts": [],
  "risks": [],
  "prompt_variables": {},
  "validation": {
    "goal_is_clear": true,
    "operation_mode_is_selected": true,
    "object_is_clear": true,
    "facts_are_separated_from_hypotheses": true,
    "source_types_are_assigned": true,
    "sources_are_listed_in_output": true,
    "official_sources_were_preferred_when_available": true,
    "confidence_scores_are_assigned": true,
    "relations_are_defined": true,
    "missing_data_is_listed": true,
    "missing_data_research_permission_recorded": true,
    "missing_data_not_filled_without_permission": true,
    "domain_validation_passed_or_not_applicable": true,
    "no_unverified_claims_presented_as_facts": true,
    "output_is_reusable_by_next_agent": true
  },
  "recommended_next_step": ""
}
```

## 16. Walidacja końcowa

Przed zwróceniem wyniku sprawdź:

```yaml
validation:
  goal_is_clear: true | false
  operation_mode_is_selected: true | false
  object_is_clear: true | false
  selected_profile_is_justified: true | false
  variables_are_defined_unambiguously: true | false
  source_types_are_assigned: true | false
  sources_are_listed_in_output: true | false
  official_sources_were_preferred_when_available: true | false
  confidence_scores_are_assigned: true | false
  facts_are_separated_from_hypotheses: true | false
  missing_data_is_listed: true | false
  missing_data_research_permission_recorded: true | false
  missing_data_not_filled_without_permission: true | false
  conflicts_are_listed: true | false
  risks_are_listed: true | false
  output_is_reusable_by_next_agent: true | false
  no_unverified_claims_presented_as_facts: true | false
  domain_validation:
    marketing_variables_complete: true | false | not_applicable
    awareness_intent_funnel_are_separated: true | false | not_applicable
    ICP_persona_JTBD_chain_is_valid: true | false | not_applicable
    objections_have_control_mechanisms: true | false | not_applicable
    messages_include_mechanism_effect_benefit_evidence: true | false | not_applicable
    numbers_have_sources: true | false | not_applicable
    competitors_have_verified_domains: true | false | not_applicable
    no_nonexistent_product_features: true | false | not_applicable
    legal_claims_require_review_when_needed: true | false | not_applicable
```

Jeżeli którekolwiek pole ma wartość `false`, popraw wynik albo wyraźnie wskaż, czego nie można potwierdzić.

## 17. Kryteria ukończenia

Zadanie można uznać za wykonane, gdy:

- cel zadania został zinterpretowany,
- wybrano `operation_mode`,
- wybrano profil domenowy,
- określono główny obiekt analizy,
- zidentyfikowano zmienne główne,
- każda kluczowa zmienna ma typ, źródło i poziom pewności,
- wykorzystane źródła zostały bezwzględnie podane w opracowaniu,
- `notebooklm-mcp`, `context7` lub inne oficjalne źródła zostały użyte jako naczelne źródła prawdy, jeżeli były adekwatne i dostępne,
- oddzielono fakty, hipotezy i braki danych,
- zapisano zgodę albo brak zgody użytkownika na samodzielne uzupełnianie braków z domyślnych źródeł prawdy,
- wskazano relacje między zmiennymi,
- opisano ryzyka i konflikty,
- przygotowano zmienne do użycia przez kolejnego agenta,
- wykonano walidację domenową, jeżeli wybrany profil jej wymaga,
- wykonano walidację końcową,
- wskazano jeden najbliższy krok operacyjny.

## 18. Instrukcja główna dla agenta

Gdy ten skill zostanie użyty, nie generuj od razu rozwiązania końcowego dla domeny użytkownika, chyba że użytkownik o to poprosi.

Najpierw zbuduj kontrakt zmiennych:

1. Jaki `operation_mode` jest właściwy?
2. Co jest analizowane?
3. Po co jest analizowane?
4. Jakie dane są pewne?
5. Jakie dane są hipotezą?
6. Jakich danych brakuje?
7. Czy użytkownik chce, aby agent samodzielnie opracował brakujące dane na podstawie domyślnych źródeł prawdy, na przykład `notebooklm-mcp`, `context7`, oficjalnej dokumentacji, materiałów projektu lub kodu źródłowego?
8. Jakie zmienne są krytyczne dla dalszej pracy?
9. Jakie relacje między nimi muszą zostać zachowane?
10. Jakie ograniczenia mają pierwszeństwo?
11. Jaki wynik może bezpiecznie przejąć kolejny agent?

Na końcu zawsze podaj jeden rekomendowany następny krok.
