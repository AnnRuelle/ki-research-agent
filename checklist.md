# KI-KB — Was du brauchst & was du tun musst

## Voraussetzungen (einmalig klären)

### Bei EBP-IT klären
- [ ] Azure OpenAI Resource: Eigene provisionieren oder zentrale mitnutzen?
- [ ] Grounding with Bing Search: Aktiviert oder aktivierbar?
- [ ] GPT-4o + GPT-4o-mini Deployments: Verfügbar?
- [ ] API-Endpoint + API-Key für die Azure OpenAI Resource erhalten

### Bei PL/Finanzen klären
- [ ] Azure OpenAI Kosten (~$5-13/Monat) auf KI-GR-Projekt verrechenbar?

### Accounts (hast du vermutlich schon)
- [ ] GitHub Account (hast du: AnnRuelle)
- [ ] Claude Pro/Max Abo (für Claude Code Entwicklung auf privatem Laptop)
- [ ] GitBook Account (gratis, mit GitHub-Login)
- [ ] SendGrid Account (gratis, für Newsletter-Versand)

### Auf deinem privaten Laptop
- [ ] Claude Code installiert (hast du)
- [ ] Git installiert (hast du vermutlich)
- [ ] Python 3.10+ installiert
- [ ] Das war's — nach der Entwicklung brauchst du den Laptop nicht mehr

### Auf den verwalteten Laptops
- [ ] Nichts. Alles läuft im Browser (github.dev, GitBook, Mail).

---

## Quellen-Vorbereitung
- [ ] RSS-Feed-URL von Superhuman AI verifizieren (https://superhuman.beehiiv.com/feed testen)
- [ ] RSS-Feed-URL von The Code verifizieren (https://codenewsletter.ai/feed testen)
- [ ] Liste weiterer Newsletter/Websites die du einbinden willst

---

## Entwicklung (auf privatem Laptop mit Claude Code)

### Phase 1 — Skeleton (1 Tag)
- [ ] GitHub Repo erstellen (privat)
- [ ] Kapitelstruktur mit allen Unterseiten + Vier-Zonen-Template
- [ ] config.yaml + sources.yaml
- [ ] SUMMARY.md (GitBook TOC)
- [ ] requirements.txt
- [ ] GitBook verbinden (Git Sync aktivieren)
- [ ] Prüfen: GitBook rendert die Kapitel korrekt

### Phase 2 — Ingest Pipeline (1 Tag)
- [ ] RSS Poller (feedparser)
- [ ] Web Archive Checker
- [ ] GitHub Action: daily-ingest.yaml
- [ ] Testen: RSS-Feeds werden in sources/newsletters/ gespeichert

### Phase 3 — Agent Pipeline (3-4 Tage)
- [ ] LLM-Abstraktionsschicht (AzureOpenAIProvider + AnthropicProvider)
- [ ] Researcher Agent
- [ ] Writer Agent
- [ ] Critic Agent
- [ ] Resolver Agent
- [ ] Merger (Code, kein LLM)
- [ ] Changelog Trimmer
- [ ] Testen: Vollständiger Durchlauf mit 2-3 Kapiteln

### Phase 4 — Newsletter & Workflow (1-2 Tage)
- [ ] Newsletter-Generator (alle Kategorien: 📗🟡🆕✂️🔶⚡)
- [ ] HTML-Template
- [ ] SendGrid-Integration
- [ ] Approve/Reject-Webhook (GitHub Action: approve-reject.yaml)
- [ ] Batch-Approve-Mechanismus
- [ ] Consistency Checker
- [ ] Testen: Newsletter wird generiert und versendet

### Phase 5 — Go Live
- [ ] Alle GitHub Secrets setzen:
  - AZURE_OPENAI_ENDPOINT
  - AZURE_OPENAI_API_KEY
  - ANTHROPIC_API_KEY (optional, nur wenn Claude genutzt)
  - SENDGRID_API_KEY
- [ ] GitHub Action: weekly-research.yaml aktivieren
- [ ] Erster automatischer Lauf abwarten (Sonntag)
- [ ] Ersten Newsletter erhalten (Montag)
- [ ] 4-6 Wochen: Alles Flagged, Qualität prüfen, kalibrieren

---

## Laufender Betrieb (nur Browser, kein Laptop nötig)

### Wöchentlich (~15-30 Min)
- [ ] Newsletter lesen (Montag morgen)
- [ ] Flagged Items approven/rejecten (Klick in Mail)
- [ ] Optional: Eigene Notizen in Kapitel eintragen (github.dev)

### Bei Bedarf
- [ ] Neue Quelle hinzufügen → sources.yaml editieren (github.dev)
- [ ] Agent-Provider umstellen → config.yaml editieren (github.dev)
- [ ] Auto-Merge aktivieren → config.yaml: auto_merge.enabled: true
- [ ] Neuen Newsletter-Empfänger → config.yaml: recipients ergänzen
- [ ] Chinesische Quellen für ein Kapitel → config.yaml: chapter_scope ändern

---

## Kosten laufend

| Was | Kosten | Wer zahlt |
|---|---|---|
| Azure OpenAI API | ~$5-13/Monat | Projekt |
| GitHub (Private Repo + Actions) | $0 | — |
| GitBook (Free Tier) | $0 | — |
| SendGrid (Free Tier) | $0 | — |
| Claude API (optional, einzelne Agents) | $2-8/Monat | Privat |
| **Total** | **$5-13/Monat** | **Projekt** |
