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
- **Betrieb:** GitHub Actions, kein Server. API-Keys als GitHub Secrets.

## Code-Stil

- Python 3.10+, Type Hints überall
- Minimal dependencies: `feedparser`, `anthropic`/`openai`, `pyyaml`, `jinja2`, `sendgrid`
- Alle Config aus `config.yaml` und `sources.yaml` — keine hardcodierten Werte
- Agents sind unabhängige Scripts, einzeln ausführbar

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

### Phase 1: Skeleton
```
1. Repo-Struktur erstellen
2. config.yaml + sources.yaml
3. Alle Kapitel-Stubs mit Vier-Zonen-Template
4. SUMMARY.md
5. templates/subpage.md + templates/newsletter.html
6. requirements.txt
→ Zeige PL: Kapitelstruktur + ein Beispiel-Stub
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
7. agents/merger.py (Code, kein LLM)
8. agents/changelog_trimmer.py
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
