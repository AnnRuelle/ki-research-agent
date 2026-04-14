# AWS Bedrock

## Überblick

AWS Bedrock ist ein vollständig verwalteter Dienst von Amazon Web Services, der Zugang zu Foundation Models verschiedener Anbieter (u.a. Anthropic Claude, Meta Llama, Mistral, Amazon Titan) über eine einheitliche API bereitstellt. Die Plattform positioniert sich als relevante Lösung für öffentliche Verwaltungen in der Schweiz, da sie Datenschutz durch regionale Datenverarbeitung und umfassende Compliance-Features für sensible Verwaltungsdaten bietet.

**Verfügbare AWS-Regionen und Datenhaltung**

Für Schweizer Kantone sind primär die europäischen AWS-Regionen relevant: eu-central-1 (Frankfurt) und eu-west-3 (Paris) ermöglichen eine Datenverarbeitung innerhalb der EU. Eine dedizierte Schweizer AWS-Region ist zum aktuellen Zeitpunkt nicht verfügbar – dieser Punkt ist für Kantone mit strengen Anforderungen an die Datenhaltung im Inland zu berücksichtigen und sollte vor einer Implementierung geprüft werden.

**Compliance und Zertifizierungen**

AWS Bedrock verfügt über ein breites Zertifizierungsportfolio, das für Schweizer Verwaltungen relevant ist: ISO 27001, SOC 2 Type II sowie den BSI C5-Testat (Cloud Computing Compliance Criteria Catalogue), der insbesondere für europäische Behörden als Referenzrahmen gilt. Zusätzlich steht mit AWS GovCloud eine gehärtete Umgebung für besonders schutzbedürftige Workloads zur Verfügung, die jedoch primär auf den US-amerikanischen Markt ausgerichtet ist.

**Vergleich mit Wettbewerbern**

Im Kontext der Schweizer Verwaltungslandschaft konkurriert Bedrock mit anderen etablierten Cloud-Plattformen:

- **Azure OpenAI Services** bieten GPT-4 und weitere Modelle mit europäischer Datenverarbeitung sowie enger Integration in Microsoft 365-Umgebungen, die in vielen Kantonen bereits im Einsatz sind. Azure verfügt ebenfalls über ISO 27001, SOC 2 und C5-Zertifizierungen.
- **Google Vertex AI** stellt eine umfassende ML-Plattform mit Foundation Models und Custom Training bereit, unterstützt durch ISO 27001 und SOC 2-Zertifizierungen sowie regionale Datenverarbeitung in Europa.

Bedrocks Differenzierungsmerkmal liegt in der Modellvielfalt über eine einheitliche API sowie in der nativen Integration mit dem bestehenden AWS-Ökosystem (IAM, VPC, CloudTrail für Audit-Logging). Eine detaillierte Gegenüberstellung der Plattformen findet sich auf der Seite [Bewertungsraster KI-Plattformen].

**Regulatorischer Rahmen**

Für den Einsatz von AWS Bedrock in Schweizer Kantonen sind folgende Institutionen und Rahmenbedingungen massgeblich:

- Das **Bundesamt für Cybersicherheit (BACS)** (ehemals NCSC) bietet Standards und Richtlinien für sichere KI-Implementierungen in der öffentlichen Verwaltung.
- Der **Eidgenössische Datenschutz- und Öffentlichkeitsbeauftragte (EDÖB)** gibt Richtlinien für datenschutzkonforme KI-Implementierungen vor, die für Kantone und Gemeinden als wichtige Orientierungshilfe dienen sollten.
- Das **Ressort für Digitale Transformation der Bundeskanzlei** koordiniert IKT-Lenkung und digitale Strategien auf Bundesebene; Kantone sind beim Alignment mit nationalen Digitalisierungszielen gefordert.

Governance-Anforderungen (Diskriminierungsrisiken, Transparenz, Accountability) sowie lokale Schweizer Anbieter werden auf den Seiten [Bewertungsraster KI-Plattformen] und [Schweizer Anbieter] behandelt.

## Eigene Notizen



## Schlüsselquellen

- AWS Official Documentation & Market Analysis (2025-01-01): https://aws.amazon.com/bedrock/
- Microsoft Azure & OpenAI Documentation (2025-01-01): https://azure.microsoft.com/en-us/products/ai-services/openai-service/
- Google Cloud Vertex AI Documentation (2025-01-01): https://cloud.google.com/vertex-ai
- BACS – Bundesamt für Cybersicherheit (ehemals NCSC) (2025-01-01): https://www.ncsc.admin.ch/
- EDÖB – Eidgenössischer Datenschutz- und Öffentlichkeitsbeauftragter (2025-01-01): https://www.edoeb.admin.ch/
- Bundeskanzlei – Digitale Transformation und IKT-Lenkung (2025-01-01): https://www.bk.admin.ch/bk/de/home/digitale-transformation.html

## Changelog

- 2026-04-14: Initiale Integration von 12 Funden: AWS Bedrock Marktposition, Azure OpenAI Integration, Google Vertex AI, Bewertungsraster für KI-Plattformen, AlgorithmWatch CH Governance-Framework, KI-Chatbots und Regierungsentscheidungen, Diskriminierung in KI-Einstellungssystemen, RAISD-Projekt, Adesso Schweiz Neupositionierung, NCSC Cybersecurity-Standards, EDÖB Datenschutz-Anforderungen, BK Digitale Transformation (Auto-merged, Critic: pending)
- 2026-04-14: Überarbeitung nach Critic-Review: Fokus auf AWS-Bedrock-spezifische Inhalte (Architektur, Modellauswahl, Regionen, Zertifizierungen); Governance-/AlgorithmWatch-/Adesso-Inhalte auf Zielseiten ausgelagert; EDÖB-Bindungswirkung korrigiert (bindend → Orientierungshilfe); NCSC zu BACS aktualisiert; Platzhalter-Satz entfernt; symmetrischer Wettbewerbsvergleich mit Bedrock-eigenen Compliance-Features ergänzt; AWS-Regionen für CH-Kantone spezifiziert
