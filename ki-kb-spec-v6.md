# KI-Wissensdatenbank — Systemspezifikation v6 (Final)

## 1. Zweck

Wachsende, kuratierte Wissensdatenbank zum Thema "KI-Plattform für kantonale Verwaltung". Dient der Projektleiterin als Arbeits-KB über den gesamten Lebenszyklus: Studie → Variantenanalyse → Beschaffung → Einführung.

Sekundärzweck: selektives Teilen von Inhalten mit Stakeholdern (Steuerungsausschuss, Projektteam, Kaderleute) via publizierte Website und kuratiertem Newsletter.

## 2. Rahmenbedingungen

| Constraint | Detail |
|---|---|
| Endgeräte | Zwei verwaltete Laptops (EBP, GR), keine Admin-Rechte |
| Zugriff | Vollständig browser-basiert im Betrieb |
| Entwicklung | Privater Laptop mit Claude Code |
| LLM-Kosten | Azure OpenAI auf Projektkosten. Claude API privat, optional. |
| Portabilität | Kein Lock-in — Provider pro Agent jederzeit wechselbar |
| Datenklassifikation | Kuratiertes öffentliches Wissen + eigene Analyse, keine klassifizierten kantonalen Daten |
| Sprache | Mixed DE/EN |

### Voraussetzungen

| Was | Status |
|---|---|
| Azure OpenAI Resource im EBP-Tenant (+ Bing Grounding + GPT-4o/mini) | ☐ EBP-IT |
| Kostenverrechnung Azure auf Projekt | ☐ PL/Finanzen |
| GitHub Account | ✓ AnnRuelle |
| Claude Code auf privatem Laptop | ✓ |
| Python 3.10+ auf privatem Laptop | ☐ Prüfen |
| GitBook Account (gratis) | ☐ Einrichten |
| SendGrid Account (gratis) | ☐ Einrichten |

## 3. Architektur

```
┌─────────────────┐   scheduled    ┌───────────────────────────┐
│  GitHub          │◄──────────────│  GitHub Action             │
│  Repository      │  commit/PR    │  (Scheduler)               │
│  (Markdown)      │               └────────────┬──────────────┘
│                  │                             │
│  config.yaml     │               ┌─────────────▼─────────────┐
│  sources.yaml    │               │  Multi-Agent-Pipeline      │
│  /chapters       │               │                            │
│  /sources        │               │  Researcher → Writer →     │
│  /updates        │               │  Critic → Resolver → Merger│
│  /agents         │               │  + Consistency Checker     │
└──────┬───────────┘               └─────────────┬─────────────┘
       │ Git Sync                                │
       ▼                           ┌─────────────▼─────────────┐
┌──────────────┐                   │  LLM Abstraktionsschicht   │
│   GitBook    │                   │  Azure OpenAI (Default)    │
│   (Publish)  │                   │  Claude / OpenAI / Mistral │
└──────────────┘                   └────────────────────────────┘
```

Nach Entwicklung: läuft autonom. Kein Laptop, kein Server nötig. GitHub Actions führt Python-Scripts aus, diese rufen Azure OpenAI per HTTPS auf. Ergebnisse werden committed, GitBook rendert, Newsletter geht raus.

## 4. Konfiguration

Zwei Files im Repo-Root. Editierbar via github.dev (Browser). Kein Code-Change nötig.

### 4.1 config.yaml — Zentrale Steuerung

```yaml
# Provider pro Agent — eine Zeile ändern = Provider wechseln
agents:
  researcher:    { provider: azure_openai, model: gpt-4o-mini }
  writer:        { provider: azure_openai, model: gpt-4o-mini }
  critic:        { provider: azure_openai, model: gpt-4o }
  resolver:      { provider: azure_openai, model: gpt-4o }
  consistency_checker: { provider: azure_openai, model: gpt-4o }

# Zeitplan (UTC)
schedule:
  rss_ingest: "daily 06:00"
  web_archive_check: "sunday 05:00"
  research_pipeline: "sunday 06:00"
  consistency_check: "sunday 08:00"
  newsletter_send: "monday 07:00"

# Newsletter
newsletter:
  sender: "ki-kb@example.com"
  recipients: ["rahel@example.com"]
  batch_approve_threshold: 10

# Auto-Merge (erst nach Kalibrierung aktivieren)
auto_merge:
  enabled: false
  rules:
    critic_verdict: approve
    critic_severity_max: minor
    operations: [update_text, add_source]
  always_manual_chapters: ["05-regulatorik", "07-markt-anbieter"]
  always_manual_tags: ["rechtsgrundlage"]
  always_manual_origins: ["CN"]

# Scope pro Kapitel
chapter_scope:
  01-plattform-architektur:    { ch: true, dach: true, global: true,  chinese: true  }
  02-use-cases:                { ch: true, dach: true, global: true,  chinese: false }
  03-datenschutz:              { ch: true, dach: true, global: true,  chinese: false }
  04-governance:               { ch: true, dach: true, global: true,  chinese: true  }
  05-regulatorik:              { ch: true, dach: true, global: true,  chinese: true  }
  06-change-management:        { ch: true, dach: true, global: true,  chinese: false }
  07-markt-anbieter:           { ch: true, dach: true, global: true,  chinese: true  }
  08-integration:              { ch: true, dach: true, global: false, chinese: false }
  09-kosten:                   { ch: true, dach: true, global: true,  chinese: false }
  10-referenzprojekte:         { ch: true, dach: true, global: true,  chinese: true  }
  11-erfolgsmessung:           { ch: true, dach: true, global: true,  chinese: false }
  12-beschaffung:              { ch: true, dach: true, global: false, chinese: false }
  13-sustainable-it:           { ch: true, dach: true, global: true,  chinese: true  }
```

### 4.2 sources.yaml — Quellen

```yaml
rss:
  - name: "Superhuman AI (Zain Kahn)"
    url: "https://superhuman.beehiiv.com/feed"
    chapters: [all]
  - name: "The Code"
    url: "https://codenewsletter.ai/feed"
    chapters: ["01-architektur", "02-use-cases"]

websites:
  - name: "Digitale Verwaltung Schweiz"
    url: "https://www.digitale-verwaltung-schweiz.ch"
    chapters: [all]
  - name: "NCSC"
    url: "https://www.ncsc.admin.ch"
    chapters: ["03-datenschutz", "05-regulatorik"]
  - name: "EDÖB"
    url: "https://www.edoeb.admin.ch"
    chapters: ["03-datenschutz", "05-regulatorik"]
  - name: "EU AI Policy"
    url: "https://digital-strategy.ec.europa.eu/en/policies/european-approach-artificial-intelligence"
    chapters: ["05-regulatorik"]
  - name: "BK Digitale Transformation"
    url: "https://www.bk.admin.ch/bk/de/home/digitale-transformation-ikt-lenkung.html"
    chapters: ["04-governance", "01-architektur"]

archives:
  - name: "DVS Newsletter-Archiv"
    url: "https://www.digital-public-services-switzerland.ch/newsletters/"
    frequency: bimonthly
    chapters: [all]

gmail:
  enabled: false
```

Neue Quelle = drei Zeilen in sources.yaml, committen, fertig.

## 5. Content-Modell

### 5.1 Living Document

Jede Unterseite ist ein aktueller Fachtext. Neues wird integriert, Veraltetes korrigiert oder entfernt. Kein Append-Log.

### 5.2 Vier-Zonen-Template

```markdown
# [Seitentitel]

## Überblick
[Agent-geschrieben. State of the Art, Einordnung, Relevanz.
Soft-Limit: ~2000 Wörter.]

## Eigene Notizen
[PL-only. Agents lesen als Kontext, schreiben nie rein.
Konferenz-Inputs, interne Quellen, persönliche Einschätzungen.]

## Schlüsselquellen
- **[Titel]** ([Datum])
  [1-2 Sätze Einordnung.] → [URL]

## Changelog
- 2026-04-14: Ergänzt: ... (Auto-merged, Critic: ✓)
- 2026-04-07: Aktualisiert: ... (Manuell freigegeben)
[Letzte 3 Monate. Älteres in Git.]
```

### 5.3 Soft-Limits

| Element | Limit | Bei Überschreitung |
|---|---|---|
| Überblick | ~2000 Wörter | Komprimieren oder Split vorschlagen |
| Eigene Notizen | Kein Limit | PL-Verantwortung |
| Schlüsselquellen | ~15 Einträge | Älteste entfernen |
| Changelog | 3 Monate | Automatisch trimmen |

## 6. Multi-Agent-Pipeline

### 6.1 Agenten

```
Researcher ──► Writer ──► Critic ──► Resolver ──► Merger
  (LLM)        (LLM)      (LLM)      (LLM)       (Code)

              + Consistency Checker (LLM, wöchentlich nach allen Merges)
```

| Agent | Aufgabe | Default-Provider |
|---|---|---|
| **Researcher** | Funde aus Web Search, RSS, kuratierten Quellen | Azure GPT-4o-mini |
| **Writer** | Rewrite-Draft: Fund in bestehenden Text integrieren | Azure GPT-4o-mini |
| **Critic** | Adversarial: Draft auf Fehler, Verzerrungen, Halluzinationen prüfen | Azure GPT-4o |
| **Resolver** | Writer + Critic → finale Version oder Flag an PL | Azure GPT-4o |
| **Merger** | Commit, Changelog, SUMMARY.md (kein LLM, nur Code) | — |
| **Consistency Checker** | Kapitelübergreifende Widersprüche | Azure GPT-4o |

Provider pro Agent jederzeit umstellbar: eine Zeile in config.yaml.

### 6.2 Operationen

| # | Operation | Auto-Merge möglich? |
|---|---|---|
| 1 | Überblick-Text aktualisieren | ✓ Nach Kalibrierung (Critic: approve, keine major Issues) |
| 2 | Schlüsselquelle hinzufügen | ✓ Nach Kalibrierung |
| 3 | Obsoleszenz melden | ✗ Immer Flagged |
| 4 | Neue Unterseite vorschlagen | ✗ Immer Flagged |
| 5 | Seiten-Split vorschlagen | ✗ Immer Flagged |
| 6 | Kapitelübergreifender Widerspruch | ✗ Immer Flagged |

Kalibrierungsphase: 4-6 Wochen alles Flagged. Auto-Merge aktivieren via config.yaml: `auto_merge.enabled: true`.

### 6.3 Review-Kriterien

Kapitel die immer manuell bleiben (konfigurierbar in config.yaml):
- 05-regulatorik
- 07-markt-anbieter
- Alles mit Tag "rechtsgrundlage"
- Alle Funde aus CN

## 7. Kapitelstruktur

```
chapters/
├── 01-plattform-architektur/
│   ├── index.md
│   ├── ai-gateway.md
│   ├── multi-modell-strategie.md
│   └── cloud-vs-hybrid.md
├── 02-use-cases/
│   ├── index.md
│   ├── katalog.md
│   └── priorisierung.md
├── 03-datenschutz-informationssicherheit/
│   ├── index.md
│   ├── ndsg.md
│   ├── isds-konzept.md
│   └── datenklassifikation.md
├── 04-governance-betriebsmodell/
│   ├── index.md
│   ├── rollenmodell.md
│   ├── freigabeprozess.md
│   └── betriebsverantwortung.md
├── 05-regulatorik/
│   ├── index.md
│   ├── eu-ai-act.md
│   ├── ch-rechtsgrundlagen.md
│   └── haftung-transparenz.md
├── 06-change-management/
│   ├── index.md
│   ├── veraenderungsbereitschaft.md
│   ├── multiplikatoren.md
│   ├── kommunikation/
│   │   ├── index.md
│   │   ├── stakeholder-mapping.md
│   │   └── kommunikationsplan.md
│   └── schulung/
│       ├── index.md
│       ├── schulungskonzept.md
│       ├── train-the-trainer.md
│       └── prompt-literacy.md
├── 07-markt-anbieter/
│   ├── index.md
│   ├── azure-openai.md
│   ├── aws-bedrock.md
│   ├── google-vertex.md
│   ├── swiss-anbieter.md
│   └── bewertungsraster.md
├── 08-integration-it-landschaft/
│   ├── index.md
│   ├── fachanwendungen.md
│   ├── iam-sso.md
│   └── dms-schnittstellen.md
├── 09-kosten-lizenzmodelle/
│   ├── index.md
│   ├── tco-modelle.md
│   └── anbietervergleich.md
├── 10-referenzprojekte-kantone/
│   ├── index.md
│   ├── zuerich.md
│   ├── bern.md
│   ├── aargau.md
│   └── weitere.md
├── 11-erfolgsmessung/
│   ├── index.md
│   ├── kpis.md
│   └── pilotauswertung.md
├── 12-beschaffung/
│   ├── index.md
│   ├── ivoeb-verfahrenswahl.md
│   ├── eignungskriterien.md
│   ├── zuschlagskriterien.md
│   └── pflichtenheft-ki.md
└── 13-sustainable-it-ki/
    ├── index.md
    ├── energieverbrauch-llm.md
    ├── rz-standort-co2.md
    └── green-it-beschaffungskriterien.md
```

Agents können neue Unterseiten vorschlagen (immer Flagged). Kapitel 12 ↔ 13 sind querverlinkt (Nachhaltigkeitskriterien als Zuschlagskriterien).

## 8. Newsletter

### 8.1 Format

```
KI-KB Update — KW 16/2026

📗 NEU HINZUGEFÜGT (5)
   [Kapitel → Unterseite, Titel, Quelle, Critic-Verdict]

🟡 BRAUCHT DEIN GO (3)
   [Kapitel → Unterseite, Titel, Flag-Grund, Critic-Kommentar]
   ► Freigeben | ► Verwerfen

🆕 NEUE SEITE VORGESCHLAGEN
   [Kapitel → neuer Dateiname, Begründung]
   ► Freigeben | ► Verwerfen

🔶 VERALTET
   [Kapitel → Unterseite, was veraltet ist, Korrekturvorschlag]
   ► Korrektur freigeben | ► Verwerfen

⚡ WIDERSPRÜCHE
   [Kapitel A vs. Kapitel B, beide Stellen, Beschreibung]
   ► Kap. A anpassen | ► Kap. B anpassen | ► Beide prüfen

BATCH-AKTIONEN (bei >10 Items)
   ► Alle Text-Updates freigeben | ► Alle Quellen freigeben

STATS
   Gescannt: X | Auto-merged: X | Flagged: X | Verworfen: X
   Kosten: Azure $X (Projekt) | Claude $X (Privat)
```

### 8.2 Approve/Reject

Mail-basiert: Klick auf Link triggert GitHub Actions workflow_dispatch.
Batch-Approve für Kategorien. Fallback: github.dev.

### 8.3 Delivery

Automatisch: GitHub Action → SendGrid → Mail. Montag 07:00 UTC.

## 9. Geographischer Scope

| Kapitel | CH | DACH | Global | CN |
|---|---|---|---|---|
| 01 Plattform-Architektur | ✓ | ✓ | ✓ | ✓ |
| 02 Use Cases | ✓ | ✓ | ✓ | ✗ |
| 03 Datenschutz | ✓ | ✓ | ✓ | ✗ |
| 04 Governance | ✓ | ✓ | ✓ | ✓ |
| 05 Regulatorik | ✓ | ✓ | ✓ | ✓ |
| 06 Change Management | ✓ | ✓ | ✓ | ✗ |
| 07 Markt & Anbieter | ✓ | ✓ | ✓ | ✓ |
| 08 Integration | ✓ | ✓ | ✗ | ✗ |
| 09 Kosten | ✓ | ✓ | ✓ | ✗ |
| 10 Referenzprojekte | ✓ | ✓ | ✓ | ✓ |
| 11 Erfolgsmessung | ✓ | ✓ | ✓ | ✗ |
| 12 Beschaffung | ✓ | ✓ | ✗ | ✗ |
| 13 Sustainable IT | ✓ | ✓ | ✓ | ✓ |

CN-Funde sind immer Flagged.

## 10. LLM-Abstraktionsschicht

```python
class LLMProvider(ABC):
    def research(self, prompt, web_search=True) -> LLMResponse: ...
    def rewrite(self, current_text, finding, instructions) -> LLMResponse: ...
    def critique(self, original, draft, finding) -> LLMResponse: ...
    def resolve(self, draft, critique) -> LLMResponse: ...
    def check_consistency(self, chapters) -> LLMResponse: ...
    def translate(self, text, target_lang) -> LLMResponse: ...

# Implementierungen:
# AzureOpenAIProvider  — Default, Projektkosten
# AnthropicProvider    — Optional, privat
# OpenAIProvider       — Fallback
# MistralProvider      — Fallback
# CopilotProvider      — Fallback, gratis via EBP
```

Provider wechseln = eine Zeile in config.yaml.

## 11. Test-Harness

### 11.1 Prinzip

Du reviewst Output, nicht Code. Jeder Agent hat einen Test der echten Output produziert den du lesen und beurteilen kannst. Kein Unit-Test der "passed/failed" sagt — sondern ein Review-Artefakt das du öffnest und inhaltlich bewertest.

### 11.2 Test-Verzeichnis

```
tests/
├── fixtures/
│   ├── sample_chapter.md          # Beispiel-Unterseite mit bestehendem Content
│   ├── sample_finding.json        # Beispiel-Fund eines Researchers
│   ├── sample_sources/            # Beispiel-RSS/Web-Inhalte
│   └── sample_chapters_multi/     # Mehrere Kapitel für Consistency Check
├── output/                        # ← HIER SCHAUST DU REIN
│   ├── researcher_findings.json   # Was hat der Researcher gefunden?
│   ├── writer_draft.md            # Wie sieht der Rewrite aus?
│   ├── writer_diff.md             # Was hat sich geändert? (Vorher/Nachher)
│   ├── critic_review.json         # Was sagt der Critic?
│   ├── resolver_final.md          # Finale Version nach Critic-Feedback
│   ├── resolver_diff.md           # Diff: Writer-Draft vs. Resolver-Final
│   ├── consistency_report.json    # Widersprüche zwischen Kapiteln
│   └── newsletter_preview.html    # So sieht der Newsletter aus
├── run_researcher.py              # Einzeln ausführbar
├── run_writer.py
├── run_critic.py
├── run_resolver.py
├── run_consistency.py
├── run_newsletter.py
├── run_full_pipeline.py           # Alles hintereinander
└── run_all_tests.py               # Automatisierte Qualitäts-Checks
```

### 11.3 Workflow

Du tippst keine Befehle. Claude Code baut, testet, und zeigt dir die Ergebnisse:

```
Du: "Baue den Researcher Agent"

Claude Code:
  1. Schreibt den Code
  2. Führt python tests/run_researcher.py aus
  3. Fasst zusammen: "7 Funde, 4 high confidence, Top-Fund: Azure AI Gateway..."
  4. Sagt: "Öffne tests/output/researcher_findings.json und sag mir was besser werden muss"

Du: öffnest die Datei, liest, gibst Feedback

Claude Code:
  1. Passt an
  2. Testet erneut
  3. Zeigt neuen Output
```

Das gleiche Muster für jeden Agent: Writer → Critic → Resolver → Newsletter.

### 11.4 Review-Fragen pro Agent

**Researcher-Output reviewen** (`researcher_findings.json`):
- Sind die Funde relevant für kantonale Verwaltung?
- Stimmen die Credibility-Einschätzungen?
- Fehlt etwas Offensichtliches?
- Sind Duplikate dabei?

**Writer-Output reviewen** (`writer_draft.md` + `writer_diff.md`):
- Liest sich der aktualisierte Text flüssig?
- Ist der neue Fund korrekt eingearbeitet?
- Wurde bestehender Content unnötig verändert?
- Ist die "Eigene Notizen"-Zone unberührt?
- Ist die neue Schlüsselquelle sinnvoll eingeordnet?

**Critic-Output reviewen** (`critic_review.json`):
- Sind die gefundenen Issues berechtigt?
- Werden echte Probleme erkannt (Halluzination, Verzerrung)?
- Ist der Critic zu streng oder zu lasch?

**Resolver-Output reviewen** (`resolver_final.md` + `resolver_diff.md`):
- Hat der Resolver die Critic-Punkte sinnvoll umgesetzt?
- Ist das Ergebnis besser als der Writer-Draft?
- Gibt es Fälle die der Resolver falsch aufgelöst hat?

**Consistency-Output reviewen** (`consistency_report.json`):
- Sind die gemeldeten Widersprüche echt?
- Fehlen offensichtliche Widersprüche?

**Newsletter reviewen** (`newsletter_preview.html`):
- Ist das Format klar und lesbar?
- Stimmen die Kategorien (📗🟡🆕🔶⚡)?
- Funktionieren die Approve/Reject-Links?

### 11.5 Automatisierte Qualitäts-Checks

Zusätzlich zu deinem manuellen Review gibt es automatische Checks:

```python
# tests/run_all_tests.py

# Strukturelle Tests (bestehen/nicht bestehen)
- [ ] Researcher-Output ist valides JSON mit allen Pflichtfeldern
- [ ] Writer-Draft enthält alle vier Zonen
- [ ] Writer hat "Eigene Notizen"-Zone nicht verändert
- [ ] Critic-Output ist valides JSON mit verdict + issues
- [ ] Resolver-Output enthält Changelog-Eintrag
- [ ] Newsletter-HTML ist valide, Links sind korrekt
- [ ] SUMMARY.md ist nach neuem Seiten-Vorschlag aktualisiert
- [ ] Changelog-Einträge älter als 3 Monate sind entfernt

# Qualitäts-Checks (Warnungen, kein hartes Fail)
- [ ] Writer-Draft ist nicht >20% länger als Original (Aufblähung)
- [ ] Writer-Draft ist nicht >20% kürzer als Original (Informationsverlust)
- [ ] Researcher hat mindestens 1 Fund pro Kapitel
- [ ] Critic hat mindestens 1 Issue pro 5 Findings (sonst zu unkritisch)
- [ ] Keine Duplikate in Schlüsselquellen
```

## 12. Repo-Struktur (final)

```
ki-kb/
├── config.yaml                    # ← Admin: Agents, Provider, Zeitplan, Regeln
├── sources.yaml                   # ← Admin: Quellen verwalten
├── CLAUDE.md                      # Claude Code Projektanweisungen
├── SUMMARY.md                     # GitBook TOC
├── README.md
├── requirements.txt
│
├── .github/
│   └── workflows/
│       ├── daily-ingest.yaml
│       ├── weekly-research.yaml
│       └── approve-reject.yaml
│
├── agents/
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── provider.py            # ABC
│   │   ├── azure_openai_provider.py
│   │   ├── anthropic_provider.py
│   │   ├── openai_provider.py
│   │   ├── mistral_provider.py
│   │   └── copilot_provider.py
│   ├── ingest/
│   │   ├── rss_poller.py
│   │   ├── web_archive_checker.py
│   │   └── gmail_poller.py
│   ├── researcher.py
│   ├── writer.py
│   ├── critic.py
│   ├── resolver.py
│   ├── consistency_checker.py
│   ├── merger.py
│   ├── changelog_trimmer.py
│   └── newsletter.py
│
├── chapters/
│   └── [13 Kapitel, nested, Vier-Zonen-Template]
│
├── sources/
│   ├── newsletters/
│   ├── web-archives/
│   └── copilot/
│
├── updates/
│   └── [YYYY-kwNN-merged/flagged/rejected.json]
│
├── templates/
│   ├── newsletter.html
│   └── subpage.md
│
└── tests/
    ├── fixtures/
    │   ├── sample_chapter.md
    │   ├── sample_finding.json
    │   ├── sample_sources/
    │   └── sample_chapters_multi/
    ├── output/                    # ← REVIEW-ARTEFAKTE
    ├── run_researcher.py
    ├── run_writer.py
    ├── run_critic.py
    ├── run_resolver.py
    ├── run_consistency.py
    ├── run_newsletter.py
    ├── run_full_pipeline.py
    └── run_all_tests.py
```

## 13. Entwicklungssetup

### Wo
Privater Laptop mit Claude Code. Nach Entwicklung: Laptop nicht mehr nötig.

### Wie
Claude Code bekommt die Spec (dieses Dokument) + CLAUDE.md als Kontext. Baut Phase für Phase. Führt nach jedem Schritt die Tests selbst aus und zeigt dir den Output.

### Review-Workflow während Entwicklung

```
Du:          "Baue Phase 3: Researcher Agent"
Claude Code:  Schreibt Code → führt Test aus → zeigt Output-Zusammenfassung
Du:          Öffnest tests/output/researcher_findings.json → gibst Feedback
Claude Code:  Passt an → testet erneut → zeigt neuen Output
Du:          "Gut. Nächster Agent: Writer."
Claude Code:  Baut Writer → testet → zeigt writer_draft.md + writer_diff.md
...
```

Du tippst nie `python ...`. Du öffnest nie ein Terminal. Du reviewst Markdown, JSON und HTML.

## 14. Kadenz (Betrieb)

| Komponente | Frequenz | Zeitpunkt |
|---|---|---|
| RSS Ingest | Täglich | 06:00 UTC |
| Web Archive Check | Wöchentlich | So 05:00 |
| Researcher + Writer | Wöchentlich | So 06:00 |
| Critic + Resolver | Wöchentlich | So 07:00 |
| Consistency Checker | Wöchentlich | So 08:00 |
| Changelog-Trimming | Wöchentlich | So 08:30 |
| Newsletter + Versand | Wöchentlich | Mo 07:00 |
| GitBook Sync | Bei jedem Push | Automatisch |

## 15. Schwachstellen & Mitigationen

| # | Schwachstelle | Mitigation |
|---|---|---|
| 1 | Rewrite-Qualität | Critic-Agent. Kalibrierungsphase. Bei Bedarf: Critic auf Claude. |
| 2 | Halluzinationen | Critic prüft explizit. Test-Harness macht Output sichtbar. |
| 3 | Quellenverarmung | "Eigene Notizen"-Zone. Manuelle Kuration. |
| 4 | Newsletter-Fatigue | Batch-Approve. Digest bei >10 Items. |
| 5 | Mail-Approve fragil | Batch-Approve + Fallback github.dev. |
| 6 | Seiten-Drift | Commit-Hash-URLs für stabile Referenzierung. |
| 7 | Kosten | GPT-4o-mini für Masse, GPT-4o nur wo nötig. Per-Agent Config. |
| 8 | Einpersonenrisiko | Pipeline staut, verliert nichts. Flagged Items warten. |

## 16. Kostenschätzung

| Konfiguration | Projektkosten | Private Kosten |
|---|---|---|
| **Default: Alles Azure** | **$4–9/Monat** | **$0** |
| Hybrid: Azure + Claude Critic | $3–7/Monat | $2–4/Monat |
| Alles Claude | $0 | $40–80/Monat |

## 17. Phasenplan

| Phase | Was | Dauer |
|---|---|---|
| 1 | Skeleton: Repo, Kapitel, Config, GitBook Sync | 1 Tag |
| 2 | Ingest: RSS Poller, Web Archive Checker, GitHub Action | 1 Tag |
| 3 | Agents: Abstraktionsschicht, Researcher→Writer→Critic→Resolver→Merger | 3-4 Tage |
| 4 | Newsletter: Generator, Template, Approve/Reject, Consistency Checker | 1-2 Tage |
| 5 | Go Live: Secrets, Actions aktivieren, Kalibrierung (4-6 Wochen) | Laufend |
| 6 | Erweiterungen: CN-Quellen, weitere Sources, Segmentierung | Laufend |

## 18. Entscheide-Log

| # | Entscheid |
|---|---|
| 1 | Kommunikation + Schulung als Unterkapitel von Change Management |
| 2 | Beschaffung als Kapitel 12, Sustainable IT als Kapitel 13, querverlinkt |
| 3 | Geographischer Scope: CH → DACH → Global inkl. CN, per-Kapitel CN-Flag |
| 4 | Approve-Workflow: Mail-basiert mit Batch-Approve |
| 5 | Kadenz: Alle Kapitel gleichzeitig, wöchentlich |
| 6 | Newsletter: Automatischer Versand |
| 7 | Kapitel: Nested von Anfang an, Agents dürfen neue vorschlagen (Flagged) |
| 8 | Copilot: Eingebaut als Fallback |
| 9 | Sprache: Mixed DE/EN |
| 10 | Quellen: RSS + Web Scrape + Gmail-Fallback |
| 11 | CN-Quellen: Per-Kapitel Flag, immer Flagged |
| 12 | Content: Living Document, Vier-Zonen-Template |
| 13 | Agents: 5+1 Pipeline (Researcher, Writer, Critic, Resolver, Merger, Consistency) |
| 14 | Default-Provider: Azure OpenAI (Projektkosten) |
| 15 | Provider: Pro Agent jederzeit umstellbar |
| 16 | Changelog: 3 Monate auf Seite, Rest in Git |
| 17 | Config: 2 Files im Root (config.yaml, sources.yaml) |
| 18 | Entwicklung: Privater Laptop + Claude Code |
| 19 | Test-Harness: Output-Review statt Code-Review |
