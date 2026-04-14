# AI Gateway

## Überblick

Ein AI Gateway dient als zentrale Schnittstelle zwischen Fachanwendungen und LLM-Providern. Es ermöglicht einheitliches Routing, Monitoring und Policy-Enforcement für alle KI-Anfragen innerhalb der kantonalen IT-Landschaft.

Wichtige Aspekte:
- **Routing:** Anfragen können je nach Modell, Kosten oder Latenz an verschiedene Provider weitergeleitet werden.
- **Sicherheit:** Zentrale Authentifizierung und Autorisierung.
- **Monitoring:** Token-Verbrauch und Kosten werden zentral erfasst.

## Eigene Notizen

Gespräch mit IT-Leiter GR (2026-03-15): Bevorzugt Azure-basierte Lösung wegen bestehendem Enterprise Agreement. Bedenken bezüglich Latenz bei On-Premise-Gateway.

TODO: Abklären ob APIM (Azure API Management) als Gateway genutzt werden kann.

## Schlüsselquellen

- **Azure AI Gateway Architecture** (2026-02-20)
  Referenzarchitektur von Microsoft für Enterprise AI Gateway. → https://learn.microsoft.com/azure/ai-gateway

- **Swiss Government Cloud Strategy** (2026-01-15)
  Bundesstrategie für Cloud-Nutzung in der Verwaltung. → https://www.bk.admin.ch/cloud-strategie

## Changelog

- 2026-04-07: Aktualisiert: Azure AI Gateway Referenzarchitektur ergänzt (Auto-merged, Critic: ✓)
- 2026-03-15: Erstellt: Initiale Version basierend auf Plattform-Evaluation (Manuell freigegeben)
