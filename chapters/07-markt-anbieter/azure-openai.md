# Azure OpenAI

## Überblick

Azure OpenAI Services stellen für Schweizer Kantone und Gemeinden eine KI-Plattform dar, die GPT-4 und weitere Foundation Models mit europäischer Datenverarbeitung bereitstellt. Die Dienste nutzen EU-Rechenzentren und adressieren damit zentrale Compliance-Anforderungen für die öffentliche Verwaltung, insbesondere die DSGVO. Für Schweizer Kantone ist zusätzlich das revidierte Datenschutzgesetz (revDSG, in Kraft seit 1. September 2023) massgeblich – die Schweiz ist kein EU-Mitglied und das revDSG stellt eigenständige Anforderungen an die Datenverarbeitung. Ob Azure OpenAI spezifische Zertifizierungen für die Schweiz (über EU-Zertifizierungen hinaus) vorweisen kann, sollte im Rahmen einer Beschaffungsevaluation geprüft werden. Eine besondere Stärke liegt in der nahtlosen Integration mit Microsoft 365, das in vielen Kantonen bereits etabliert ist.

### Azure OpenAI: Kernfunktionen und Einsatzszenarien

Azure OpenAI bietet Zugang zu Foundation Models (u. a. GPT-4, GPT-4o) über eine verwaltete Cloud-Infrastruktur mit folgenden für Verwaltungen relevanten Eigenschaften:

- **Datenhaltung in der EU**: Verarbeitung in europäischen Rechenzentren, keine Übermittlung in Drittländer (konfigurierbar)
- **Compliance-Zertifizierungen**: ISO 27001, SOC 2 und weitere Standards; spezifische Schweizer Anforderungen (revDSG) sind im Einzelfall zu prüfen
- **Integration**: Nahtlose Anbindung an Microsoft 365, Azure Active Directory und bestehende Verwaltungs-IT
- **Einsatzszenarien in Kantonen**: Dokumentenanalyse, interne Wissenssuche, Unterstützung bei Textredaktion, Bürger-Chatbots (mit entsprechenden Governance-Vorkehrungen)

### Marktkontext und Anbietervergleich

Im Markt der KI-Plattformen für öffentliche Verwaltungen konkurrieren neben Azure OpenAI weitere etablierte Anbieter: AWS Bedrock bietet als verwaltete Dienst-Plattform für Foundation Models regionale Datenverarbeitung und spezialisierte Compliance-Features für sensible Verwaltungsdaten. Google Vertex AI stellt eine umfassende ML-Plattform mit Custom-Training-Optionen bereit und verfügt über Compliance-Zertifizierungen (ISO 27001, SOC 2) sowie regionale Datenverarbeitungsmöglichkeiten. Auf Schweizer Ebene positioniert sich Adesso Schweiz als lokaler Anbieter für Verwaltungslösungen und KI-Integration; gemäss IT-Markt.ch (Stand 2026) wurden eine neue CEO und ein neuer CTO mit Hintergrund aus der Aargauer Verwaltung ernannt (Quellenqualität: Medium, Konfidenz eingeschränkt).

### Bewertungskriterien für die Anbieterauswahl

Die Auswahl einer KI-Plattform sollte sich an einem strukturierten Bewertungsraster orientieren, das folgende Dimensionen abdeckt:

- **Datenhaltung**: Verarbeitung in der Schweiz oder EU (nicht in Drittländern)
- **Zertifizierungen**: ISO 27001, SOC 2, C5 und weitere relevante Standards
- **Preismodelle**: Pay-as-you-go versus Subscription-Modelle
- **Compliance**: DSGVO, revDSG (Schweizer Datenschutzgesetz), Anforderungen des EDÖB
- **Transparenz**: Nachvollziehbarkeit von Algorithmen und Entscheidungsprozessen
- **Support und Governance**: Lokale Support-Strukturen und Governance-Mechanismen

AlgorithmWatch Schweiz bietet mit seinem Impact Assessment Tool und Framework für Algorithmen & KI wichtige Orientierungshilfen für diese Bewertung. Das Framework adressiert speziell Diskriminierungsrisiken, Transparenzanforderungen und Accountability-Mechanismen – zentral für die verantwortungsvolle Einführung von KI in Kantonen und Gemeinden.

### Governance und Risikomanagement

Bei der Implementierung von KI-Plattformen in der öffentlichen Verwaltung sind Governance-Strukturen essentiell. KI-Chatbots und automatisierte Entscheidungshilfen können Entscheidungsprozesse in Regierungen beeinflussen und bergen Risiken von Bias und Diskriminierung – etwa in HR-Anwendungen oder bei algorithmischen Einstellungssystemen. Verwaltungen müssen daher Transparenz und menschliche Kontrolle sicherstellen sowie regelmässige Audit-Mechanismen zur Vermeidung von Diskriminierung implementieren.

Das RAISD-Projekt von AlgorithmWatch Schweiz untersucht systematisch, wie KI-Systeme Demokratie und Gesellschaft beeinflussen, und bietet Governance-Anforderungen für die Einführung von KI-Plattformen.

### Regulatorischer Rahmen und Standards

Auf nationaler Ebene setzen mehrere Institutionen Standards für sichere und datenschutzkonforme KI-Implementierungen:

- Das **Nationale Zentrum für Cybersicherheit (NCSC)** setzt Cybersecurity-Standards für die öffentliche Verwaltung, die auch für KI-Implementierungen relevant sind. Spezifische KI-Richtlinien des NCSC sollten direkt auf der NCSC-Website geprüft werden, da die allgemeine Cybersecurity-Mandate-Seite keinen expliziten KI-Fokus ausweist.
- Der **Eidgenössische Datenschutz- und Öffentlichkeitsbeauftragte (EDÖB)** gibt Richtlinien für datenschutzkonforme KI-Implementierungen vor und adressiert speziell die Verarbeitung personenbezogener Daten durch Anbieter.
- Die **Bundeskanzlei – Ressort Digitale Transformation** koordiniert IKT-Lenkung und digitale Strategien auf Bundesebene und setzt damit den Rahmen für Alignment mit nationalen Digitalisierungszielen bei der KI-Plattform-Auswahl in Kantonen.

Diese Governance-Strukturen sind zentral für eine verantwortungsvolle und rechtskonforme Einführung von KI-Plattformen wie Azure OpenAI in der Schweizer Verwaltungslandschaft.

## Eigene Notizen



## Schlüsselquellen

| Quelle | URL | Datum | Typ | Glaubwürdigkeit |
|--------|-----|-------|-----|-----------------|
| Microsoft Azure & OpenAI Documentation | https://azure.microsoft.com/en-us/products/ai-services/openai-service/ | 2026-04-14 | Vendor | High |
| AWS Official Documentation & Market Analysis | https://aws.amazon.com/bedrock/ | 2026-04-14 | Vendor | High |
| Google Cloud Vertex AI Documentation | https://cloud.google.com/vertex-ai | 2026-04-14 | Vendor | High |
| AlgorithmWatch CH – AI Impact Assessment Tool & Framework | https://algorithmwatch.ch/en/using-ai-responsibly/ | 2026-04-14 | Civil Society | High |
| AlgorithmWatch CH – Framework für Algorithmen & KI | https://algorithmwatch.ch/en/ai-regulation/ | 2026-04-14 | Civil Society | High |
| AlgorithmWatch CH – Could AI Chatbots influence a Government's Decisions? | https://algorithmwatch.ch/en/could-ai-chatbots-influence-governments/ | 2026-04-14 | Civil Society | High |
| AlgorithmWatch CH – Discrimination through AI hiring tools | https://algorithmwatch.ch/en/discrimination-by-ai-in-algorithmic-hiring/ | 2026-04-14 | Civil Society | High |
| AlgorithmWatch CH – RAISD Project | https://algorithmwatch.ch/en/raisd/ | 2026-04-14 | Civil Society | High |
| IT-Markt.ch – Adesso Schweiz Führungswechsel | https://it-markt.ch/tags/adesso | 2026-04-14 | Media | Medium |
| NCSC – Nationale Zentrum für Cybersicherheit | https://www.ncsc.admin.ch/ | 2026-04-14 | Government | High |
| EDÖB – Eidgenössischer Datenschutz- und Öffentlichkeitsbeauftragter | https://www.edoeb.admin.ch/ | 2026-04-14 | Government | High |
| Bundeskanzlei – Digitale Transformation und IKT-Lenkung | https://www.bk.admin.ch/bk/de/home/digitale-transformation.html | 2026-04-14 | Government | High |

## Changelog

- 2026-04-14: Umfassende Erstbefüllung mit Marktüberblick (Azure OpenAI, AWS Bedrock, Google Vertex AI), Bewertungsraster für KI-Plattformen, Governance-Framework von AlgorithmWatch CH, Risikomanagement (Bias, Diskriminierung, Chatbot-Einfluss), regulatorischer Rahmen (NCSC, EDÖB, BK Digitale Transformation), lokale Anbieter (Adesso Schweiz). Alle 12 Funde integriert.
- 2026-04-14: Überarbeitung nach Critic-Review: Azure OpenAI als Hauptthema ausgebaut (Kernfunktionen, Einsatzszenarien); revDSG explizit als eigenständige Schweizer Anforderung ergänzt; NCSC-Formulierung abgeschwächt (keine belegte KI-spezifische Richtlinie); Adesso-Angabe mit Quellenvorbehalt versehen (Medium-Credibility, Konfidenz eingeschränkt); AlgorithmWatch-Quellentyp von «Academic» auf «Civil Society» korrigiert; Quelldaten auf Recherche-Datum 2026-04-14 vereinheitlicht; Status-Marker aus Changelog entfernt.
