# CLAUDE.md — Projektanweisungen für Claude Code

## Projekt

KI-Wissensdatenbank: Agent-gestützte, wachsende Wissensdatenbank zum Thema "KI-Plattform für kantonale Verwaltung". 13 Kapitel, Living Documents, wöchentlich automatisch aktualisiert.

## Spec

Lies `ki-kb-spec-v6.md` für die vollständige Spezifikation.

## Goldene Regel

**Die PL reviewt Output, nie Code.** Nach jedem Build-Schritt:
1. Code schreiben
2. Test ausführen
3. Output zusammenfassen und der PL zeigen
4. Auf Feedback warten
5. Anpassen und erneut testen

Die PL tippt keine Befehle. Du führst alles aus, du zeigst Ergebnisse.

## Architektur-Kernpunkte

- **2 Config-Files im Root:** `config.yaml` (Steuerung) + `sources.yaml` (Quellen). Alles andere liest daraus.
- **LLM-Abstraktionsschicht:** `agents/llm/provider.py` (ABC). Pro Agent individuell konfigurierbarer Provider.
- **5+1 Agents:** Researcher → Writer → Critic → Resolver → Merger (Code) + Consistency Checker
- **Content:** Markdown in `chapters/`, Vier-Zonen-Template (Überblick, Eigene Notizen, Schlüsselquellen, Changelog)
- **Dashboard:** Auto-generierte Landing Page (`index.md`) mit Status, Frische-Indikator und Links pro Kapitel. Merger aktualisiert nach jedem Run.
- **Kapitel-Index:** Jede `chapters/XX/index.md` wird automatisch aktualisiert (Unterseiten-Übersicht + letztes Update). Vier-Zonen-Template, "Eigene Notizen" geschützt.
- **Globales Changelog:** `CHANGELOG.md` — kapitelübergreifend, 3 Monate, vom Merger gepflegt.
- **Betrieb:** GitHub Actions, kein Server. API-Keys als GitHub Secrets.

## Code-Stil

- Python 3.10+, Type Hints überall (erzwungen durch mypy strict)
- Minimal dependencies: `feedparser`, `anthropic`/`openai`, `pyyaml`, `jinja2`, `sendgrid`, `pydantic`
- Alle Config aus `config.yaml` und `sources.yaml` — keine hardcodierten Werte
- Agents sind unabhängige Scripts, einzeln ausführbar
- Kein `print()` — nur `logging` (structured, JSON-Format)
- Alle öffentlichen Funktionen haben Docstrings
- Max. Zeilenlänge: 120 Zeichen

## Projekt-Tooling

### Projekt-Setup
- **`pyproject.toml`** als zentrale Konfiguration (Ruff, mypy, pytest, Projekt-Metadaten)
- **`requirements.txt`** mit gepinnten Versionen (`==`) — reproduzierbare Builds
- **`requirements-dev.txt`** für Entwicklungstools (ruff, mypy, pytest, pre-commit)
- **`.env.example`** dokumentiert alle nötigen Umgebungsvariablen (API-Keys etc.)
- **`.gitignore`** für: `.env`, `__pycache__/`, `.venv/`, `tests/output/`, `*.pyc`, `.mypy_cache/`, `.ruff_cache/`

### Linting & Formatting
- **Ruff** als Linter + Formatter (ersetzt flake8, isort, black)
- **mypy** im strict mode — Type Hints ohne Checker sind nur Deko
- **Pre-commit Hooks** via `pre-commit` — kein unformatierter Code wird committet:
  - `ruff check --fix`
  - `ruff format`
  - `mypy`

### CI-Pipeline
Zusätzlich zu den operationalen Workflows (`daily-ingest`, `weekly-research`, `approve-reject`):
- **`.github/workflows/ci.yaml`** — läuft bei jedem Push und PR:
  1. `ruff check` + `ruff format --check`
  2. `mypy --strict`
  3. `pytest tests/` (Unit Tests)
- Ohne grüne CI kein Merge.

## Input-Validierung

### Pydantic-Modelle für Konfiguration
- `config.yaml` und `sources.yaml` werden beim Start gegen Pydantic-Modelle validiert
- Tippfehler, fehlende Felder, falsche Typen → klarer Fehler beim Start, nicht zur Laufzeit
- Agent-Outputs (Finding-JSON, Critic-JSON) ebenfalls gegen Pydantic-Schemas validiert

### Startup-Checks
- Beim Pipeline-Start: alle benötigten API-Keys vorhanden? → Klare Fehlermeldung statt kryptischem 401
- Config-Validierung vor dem ersten LLM-Call

## Error Handling & Resilience

### Retry-Logik
- LLM-API-Calls: Exponential Backoff mit max. 3 Retries (Rate Limits, Timeouts, 5xx)
- Konfigurierbar pro Agent in `config.yaml`:
  ```yaml
  agents:
    researcher: { provider: azure_openai, model: gpt-4o-mini, retries: 3, timeout: 60 }
  ```

### Circuit Breaker
- Wenn ein Provider N-mal hintereinander fehlschlägt → Pipeline überspringt restliche Kapitel für diesen Agent, loggt Warnung
- Kein blindes Retry gegen eine tote API für alle 13 Kapitel

### Graceful Degradation
- Fehler in einem Kapitel stoppt nicht die ganze Pipeline
- Fehlgeschlagene Kapitel werden geloggt und im Newsletter als "übersprungen" markiert
- Pipeline gibt am Ende eine Zusammenfassung: X erfolgreich, Y fehlgeschlagen, Z übersprungen

### Fehlerklassen
| Fehler | Verhalten |
|---|---|
| API-Key fehlt | Pipeline bricht sofort ab, klare Meldung |
| Rate Limit (429) | Retry mit Backoff |
| Timeout | Retry, dann Skip |
| Invalider LLM-Output | Retry (1x), dann Skip mit Warning |
| Config-Fehler | Pipeline startet nicht |
| Netzwerk-Fehler | Retry mit Backoff |

## Logging & Observability

### Structured Logging
- Alle Module nutzen `logging` mit JSON-Format (lesbar in GitHub Actions)
- Jeder Pipeline-Run bekommt eine **Run-ID** (UUID), die durch alle Agents propagiert wird
- Log-Level: `DEBUG` für Entwicklung, `INFO` für Produktion (konfigurierbar in `config.yaml`)

### Cost Tracking
- Jeder LLM-Call loggt: Agent, Modell, Input-Tokens, Output-Tokens, Kosten
- Am Ende jedes Runs: Kosten-Zusammenfassung pro Agent und gesamt
- Wird im Newsletter unter STATS angezeigt

### Run-Artefakte
```
updates/
└── YYYY-kwNN/
    ├── run-log.json          # Strukturiertes Log des gesamten Runs
    ├── cost-summary.json     # Token-Counts und Kosten pro Agent
    ├── merged.json
    ├── flagged.json
    └── rejected.json
```

## Test-Strategie

### Zwei Ebenen

**1. Unit Tests (pytest, deterministisch, kein LLM)**
- Vier-Zonen-Parser: korrekt trennen + zusammenfügen
- Config-Loader: valide/invalide YAML, fehlende Felder
- Merger: Changelog-Einträge, SUMMARY.md-Updates
- Changelog-Trimmer: 3-Monats-Logik
- Newsletter-Template-Rendering
- Pydantic-Schema-Validierung
- Retry/Backoff-Logik (mit Mocks)

**2. Integrations-Tests (Output-Review, mit LLM)**
- Das bestehende Test-Harness (`tests/run_*.py`)
- Produziert echte Outputs für PL-Review

### Testabdeckung
- Ziel: 90%+ für deterministische Komponenten (Merger, Parser, Config, Trimmer)
- LLM-Agents: nur Output-Struktur testbar (JSON-Schema, Zonen-Integrität), nicht Inhalt

## Vier-Zonen-Template

```markdown
# [Seitentitel]

## Überblick
[Agent-geschrieben]

## Eigene Notizen
[PL-only. Agents: NUR LESEN, NIE SCHREIBEN.]

## Schlüsselquellen
[Agent-geschrieben]

## Changelog
[Agent-geschrieben. Max 3 Monate.]
```

Parsing muss die Zonen sauber trennen und wieder zusammenfügen. Zone 2 darf nach einem Agent-Durchlauf NICHT verändert sein — das ist ein harter Test.

## Test-Harness

### Struktur

```
tests/
├── fixtures/
│   ├── sample_chapter.md
│   ├── sample_finding.json
│   ├── sample_sources/
│   └── sample_chapters_multi/
├── output/                        # ← PL reviewt hier
│   ├── researcher_findings.json
│   ├── writer_draft.md
│   ├── writer_diff.md
│   ├── critic_review.json
│   ├── resolver_final.md
│   ├── resolver_diff.md
│   ├── consistency_report.json
│   └── newsletter_preview.html
├── run_researcher.py
├── run_writer.py
├── run_critic.py
├── run_resolver.py
├── run_consistency.py
├── run_newsletter.py
├── run_full_pipeline.py
└── run_all_tests.py
```

### Nach jedem Build-Schritt

Du (Claude Code) führst den relevanten Test aus und zeigst der PL:

**Nach Researcher bauen:**
```
Ausgeführt: python tests/run_researcher.py --chapter 01-plattform-architektur
Output: tests/output/researcher_findings.json

Zusammenfassung:
- 7 Funde, davon 4 high confidence
- Quellen: 2× government, 3× media, 2× newsletter
- Top-Fund: "Azure AI Gateway Prompt Caching" (confidence 0.92)
- Schwächster Fund: "Blog-Post über KI-Hype" (confidence 0.45)

→ Bitte researcher_findings.json öffnen und reviewen.
  Fragen: Sind die Funde relevant? Stimmen die Credibility-Scores?
```

**Nach Writer bauen:**
```
Ausgeführt: python tests/run_writer.py --finding tests/output/researcher_findings.json
Output: tests/output/writer_draft.md + tests/output/writer_diff.md

Zusammenfassung:
- Seite ai-gateway.md aktualisiert
- 1 neuer Absatz im Überblick (Prompt Caching)
- 1 neue Schlüsselquelle hinzugefügt
- Eigene Notizen: ✓ unverändert
- Textlänge: 1420 → 1580 Wörter (+11%)

→ Bitte writer_diff.md öffnen und reviewen.
  Fragen: Liest sich der neue Text flüssig? Korrekt eingearbeitet?
```

**Nach Critic bauen:**
```
Ausgeführt: python tests/run_critic.py --draft tests/output/writer_draft.md
Output: tests/output/critic_review.json

Zusammenfassung:
- Verdict: revise (1 major issue)
- Issue: "Writer behauptet '40% Latenzreduktion', Quelle sagt 'up to 40%' — Nuance fehlt"
- Suggested fix: "Formulierung ändern zu 'bis zu 40%'"

→ Bitte critic_review.json öffnen und reviewen.
  Fragen: Ist die Kritik berechtigt? Zu streng? Zu lasch?
```

**Nach Resolver bauen:**
```
Ausgeführt: python tests/run_resolver.py
Output: tests/output/resolver_final.md + tests/output/resolver_diff.md

Zusammenfassung:
- Critic-Issue übernommen: "bis zu 40%" statt "40%"
- Restlicher Draft beibehalten
- Changelog-Eintrag vorbereitet

→ Bitte resolver_diff.md öffnen und reviewen.
  Frage: Besser als der Writer-Draft?
```

**Nach Newsletter bauen:**
```
Ausgeführt: python tests/run_newsletter.py
Output: tests/output/newsletter_preview.html

→ Bitte newsletter_preview.html im Browser öffnen.
  Fragen: Format klar? Kategorien richtig? Links plausibel?
```

**Volle Pipeline:**
```
Ausgeführt: python tests/run_full_pipeline.py --chapter 01-plattform-architektur
+ python tests/run_all_tests.py

Automatisierte Checks:
  ✓ Researcher-Output: valides JSON
  ✓ Writer: alle vier Zonen vorhanden
  ✓ Writer: Eigene Notizen unverändert
  ✓ Critic: valides JSON
  ✓ Resolver: Changelog-Eintrag vorhanden
  ✓ Newsletter: valides HTML
  ⚠️ Writer-Draft 18% länger als Original (Limit: 20%)

→ Alle Outputs in tests/output/. Bitte reviewen.
```

### Diff-Format

Kein git-diff. Menschenlesbar:

```markdown
## Änderungen

### Hinzugefügt
> Azure AI Gateway unterstützt seit März 2026 Prompt Caching,
> was die Latenz um bis zu 40% reduziert.
> (Quelle: Microsoft Tech Blog, 12.04.2026)

### Geändert
**Vorher:** "On-Premise bieten die höchste Datensouveränität."
**Nachher:** "On-Premise bieten die höchste Datensouveränität, erfordern
aber signifikant höhere Betriebskosten (vgl. Kap. 09)."

### Entfernt
~Nichts entfernt.~
```

## Build-Reihenfolge

### Phase 0: Projekt-Tooling
```
1. .gitignore
2. pyproject.toml (Ruff, mypy, pytest Config)
3. requirements.txt + requirements-dev.txt (gepinnte Versionen)
4. .env.example
5. .pre-commit-config.yaml
6. .github/workflows/ci.yaml (Ruff + mypy + pytest)
→ Zeige PL: Tooling-Setup, CI läuft grün
```

### Phase 1: Skeleton
```
1. Repo-Struktur erstellen
2. config.yaml + sources.yaml + Pydantic-Modelle dafür
3. Alle Kapitel-Stubs mit Vier-Zonen-Template
4. SUMMARY.md
5. templates/subpage.md + templates/newsletter.html
6. Vier-Zonen-Parser mit Unit Tests
→ Zeige PL: Kapitelstruktur + ein Beispiel-Stub + Tests grün
```

### Phase 2: Ingest
```
1. agents/ingest/rss_poller.py
2. agents/ingest/web_archive_checker.py
3. .github/workflows/daily-ingest.yaml
4. tests/run_ingest.py
→ Ausführen, zeige PL: ingested sources
```

### Phase 3: Agent Pipeline
Baue einen Agent, teste, zeige Output, warte auf Feedback. Dann nächster Agent.
```
1. agents/llm/provider.py (ABC)
2. agents/llm/azure_openai_provider.py + anthropic_provider.py
3. agents/researcher.py → teste → zeige researcher_findings.json
   WARTE AUF PL-FEEDBACK
4. agents/writer.py → teste → zeige writer_draft.md + writer_diff.md
   WARTE AUF PL-FEEDBACK
5. agents/critic.py → teste → zeige critic_review.json
   WARTE AUF PL-FEEDBACK
6. agents/resolver.py → teste → zeige resolver_final.md + resolver_diff.md
   WARTE AUF PL-FEEDBACK
7. agents/merger.py (Code, kein LLM) — inkl. Dashboard + Kapitel-Index-Update
8. agents/changelog_trimmer.py — inkl. CHANGELOG.md global
9. agents/consistency_checker.py → teste → zeige consistency_report.json
   WARTE AUF PL-FEEDBACK
```

### Phase 4: Newsletter & Workflow
```
1. agents/newsletter.py
2. → teste → zeige newsletter_preview.html
   WARTE AUF PL-FEEDBACK
3. .github/workflows/weekly-research.yaml
4. .github/workflows/approve-reject.yaml
5. → run_full_pipeline.py + run_all_tests.py → zeige alles
   WARTE AUF PL-FEEDBACK
```

## Automatisierte Checks (run_all_tests.py)

### Hart (müssen bestehen)
- Researcher-Output: valides JSON, alle Pflichtfelder
- Writer-Draft: alle vier Zonen-Header vorhanden
- Writer: "Eigene Notizen"-Zone byte-identisch mit Original
- Critic-Output: valides JSON mit verdict + issues
- Resolver-Output: Changelog-Eintrag vorhanden
- Newsletter-HTML: valide, Approve/Reject-Links vorhanden
- Dashboard: alle 13 Kapitel gelistet, Links valide, Frische-Indikator korrekt
- Kapitel-Index: Unterseiten-Liste stimmt mit Dateisystem überein
- CHANGELOG.md: keine Einträge >3 Monate, chronologisch sortiert
- Config-Parsing: config.yaml und sources.yaml fehlerfrei

### Weich (Warnungen)
- Writer-Draft nicht >20% länger als Original
- Writer-Draft nicht >20% kürzer als Original
- Researcher mindestens 1 Fund
- Critic mindestens 1 Issue pro 5 Findings
- Keine Duplikat-URLs in Schlüsselquellen
- Changelog keine Einträge >3 Monate

## Konventionen

- `[all]` in sources.yaml = alle 13 Kapitel
- Kapitel-IDs: `01-plattform-architektur`, `02-use-cases`, etc.
- Finding-IDs: `YYYY-MM-DD-{kürzel}-NNN`
- Commits: `[agent:{name}] {operation}: {beschreibung}`
- Changelog: `- YYYY-MM-DD: {was} ({Auto-merged|Manuell freigegeben}, Critic: ✓|⚠️)`
