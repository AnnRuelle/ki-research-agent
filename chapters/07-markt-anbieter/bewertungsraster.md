# Bewertungsraster

## Überblick

Vergleich der KI-Plattform-Anbieter fuer kantonale Verwaltungen

| Anbieter | Deployment | CH-Region | Datenstandort | Zertifizierungen | Preismodell | Modelle | Staerken | Schwaechen |
|---|---|---|---|---|---|---|---|---|
| Azure OpenAI Service | Cloud | Switzerland North/West | Schweiz | ISO 27001, SOC 2, C5, ISAE 3402 | Pay-per-Token | GPT-4o, GPT-4o-mini, DALL-E, Whisper | CH-Region, Enterprise-Support, breites Modellportfolio, Bing Grounding | Vendor Lock-in, komplexe Kostenprognose |
| AWS Bedrock | Cloud | Zuerich (eu-central-2) | Schweiz | ISO 27001, SOC 2, C5 | Pay-per-Token | Claude, Llama, Mistral, Titan | Multi-Modell-Zugang, CH-Region, gute API | Weniger Enterprise-Features als Azure |
| Google Vertex AI | Cloud | Zuerich (europe-west6) | Schweiz | ISO 27001, SOC 2 | Pay-per-Token + Provisioned Throughput | Gemini Pro/Ultra, PaLM 2 | Starke Multimodalitaet, Grounding, Search-Integration | Weniger Verwaltungs-Referenzen in CH |
| Anthropic (Claude) | Cloud (via AWS/GCP) | Via AWS Zuerich oder GCP Zuerich | Abhaengig vom Hosting-Provider | SOC 2 Type II | Pay-per-Token | Claude Opus, Sonnet, Haiku | Starke Textqualitaet, Constitutional AI, grosse Kontextfenster | Kein eigenes CH-Hosting, keine Bing Grounding |
| BEGASOFT (Schweiz) | Private Cloud / On-Premise | Schweizer Rechenzentren | Schweiz (garantiert) | ISAE 3402, CH-spezifisch | Lizenz + Betrieb | Diverse Open-Source (Llama, Mistral) | Volle Datensouveraenitaet, CH-Firma, oeV-Erfahrung, SSGI-Auftrag | Kleineres Modellportfolio, weniger Skalierung |
| Abraxas (Schweiz) | Private Cloud | Schweizer Rechenzentren | Schweiz (garantiert) | ISO 27001, ISAE 3402 | Lizenz + Betrieb | Diverse, kantonal angepasst | Tiefe oeV-Integration, kantonale Referenzen, Ostschweizer Kantone | Regional fokussiert |

## Eigene Notizen



## Schlüsselquellen

| Quelle | Typ | Datum | URL | Credibility |
|--------|-----|-------|-----|-------------|
| AWS Official Documentation & Market Analysis | vendor | 2025-01-01 | https://aws.amazon.com/bedrock/ | high |
| Microsoft Azure & OpenAI Documentation | vendor | 2025-01-01 | https://azure.microsoft.com/en-us/products/ai-services/openai-service/ | high |
| Google Cloud Vertex AI Documentation | vendor | 2025-01-01 | https://cloud.google.com/vertex-ai | high |
| AlgorithmWatch CH – AI Impact Assessment Tool & Framework | academic | 2025-01-01 | https://algorithmwatch.ch/en/using-ai-responsibly/ | high |
| AlgorithmWatch CH – Framework für Algorithmen & KI | academic | 2025-01-01 | https://algorithmwatch.ch/en/ai-regulation/ | high |
| AlgorithmWatch CH – Could AI Chatbots influence a Government's Decisions? | academic | 2025-01-01 | https://algorithmwatch.ch/en/could-ai-chatbots-influence-governments/ | high |
| AlgorithmWatch CH – Discrimination through AI hiring tools | academic | 2025-01-01 | https://algorithmwatch.ch/en/discrimination-by-ai-in-algorithmic-hiring/ | high |
| AlgorithmWatch CH – RAISD Project | academic | 2025-01-01 | https://algorithmwatch.ch/en/raisd/ | high |
| IT-Markt.ch – Adesso Schweiz Führungswechsel | media | 2026-01-01 | https://it-markt.ch/tags/adesso | medium |
| NCSC – Nationale Zentrum für Cybersicherheit | government | 2025-01-01 | https://www.ncsc.admin.ch/ | high |
| EDÖB – Eidgenössischer Datenschutz- und Öffentlichkeitsbeauftragter | government | 2025-01-01 | https://www.edoeb.admin.ch/ | high |
| Bundeskanzlei – Digitale Transformation und IKT-Lenkung | government | 2025-01-01 | https://www.bk.admin.ch/bk/de/home/digitale-transformation.html | high |

## Changelog

- 2026-04-14: Bewertungsraster mit 12 Funden initialisiert: AWS Bedrock, Azure OpenAI, Google Vertex AI, AlgorithmWatch CH Framework (5 Quellen), Adesso Schweiz, NCSC, EDÖB, Bundeskanzlei; strukturierte Bewertungsdimensionen (Datenschutz, Sicherheit, Governance, Geschäftsmodelle, Support) und Marktübersicht etabliert (Auto-merged, Critic: pending)
- 2026-04-14: Critic-Feedback umgesetzt: EDÖB-Formulierung von «verbindliche Richtlinien» zu «Richtlinien und Empfehlungen» korrigiert; NCSC-Nachweispflicht entschärft zu Kompatibilitätsprüfung; «umfassendes Framework» bei AlgorithmWatch CH gestrichen; Adesso-Schweiz-Aussage als Medienbericht (IT-Markt.ch) gekennzeichnet; revDSG-Hinweis für alle Cloud-Anbieter ergänzt; Klarstellung zur Scoring-Gewichtung in «Praktische Anwendung» eingefügt; Integrationsbeschreibungen der drei Cloud-Anbieter neutralisiert; Schweizer Orthographie (ss statt ß) vereinheitlicht
