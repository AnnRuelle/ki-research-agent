# IAM & SSO

## Überblick

Identity and Access Management (IAM) sowie Single Sign-On (SSO) sind zentrale Infrastrukturkomponenten für die sichere und effiziente Integration von KI-Systemen in kantonale Verwaltungen. Sie ermöglichen es, Benutzeridentitäten zu verwalten, Zugriffe zu kontrollieren und Authentifizierungsprozesse zu standardisieren.

> **Hinweis:** Für dieses Kapitel liegen derzeit keine spezifisch IAM/SSO-relevanten Funde vor. Die nachfolgenden Abschnitte beschreiben den konzeptionellen Rahmen; konkrete Quellen zu Implementierungen in kantonalen Verwaltungen (z. B. eIAM des Bundes, CH-LOGIN, SAML/OIDC-Integrationen) werden bei Verfügbarkeit ergänzt.

### Konzeptioneller Rahmen

Für kantonale Verwaltungen sind folgende IAM/SSO-Themen besonders relevant:

- **Föderale Identitätssysteme:** Der Bund betreibt mit eIAM (Electronic Identity and Access Management) eine zentrale Infrastruktur, die Kantonen und Behörden standardisierte Authentifizierungsdienste bereitstellt. CH-LOGIN ist der zugehörige Bürger-Login-Dienst.
- **Protokollstandards:** SAML 2.0, OAuth 2.0 und OpenID Connect (OIDC) sind die gängigen Protokolle für föderierte Identitäten und SSO-Integrationen. KI-Plattformen sollten diese Standards unterstützen, um eine nahtlose Integration in bestehende Verwaltungsinfrastrukturen zu ermöglichen.
- **Multi-organisationale Umgebungen:** In föderalen Strukturen (Bund, Kantone, Gemeinden) entstehen komplexe Anforderungen an Identitätsföderation und rollenbasierte Zugriffskontrolle (RBAC), die bei der Evaluation von KI-Plattformen berücksichtigt werden müssen.
- **Datenschutz und Compliance:** IAM-Systeme in kantonalen Verwaltungen müssen den Anforderungen des revidierten Datenschutzgesetzes (revDSG) sowie kantonaler Datenschutzgesetzgebung entsprechen.

### Relevanz für kantonale Entscheidungsträger

Bei der Evaluation von KI-Plattformen sollten Kantone folgende IAM/SSO-Kriterien prüfen:

- Unterstützung von SAML 2.0 / OIDC für Integration in bestehende Verzeichnisdienste (Active Directory, LDAP)
- Kompatibilität mit eIAM / CH-LOGIN des Bundes
- Rollenbasierte Zugriffskontrolle (RBAC) und Mandantenfähigkeit für multi-organisationale Nutzung
- Audit-Logging und Nachvollziehbarkeit von Zugriffen auf KI-Systeme
- Unterstützung von Multi-Faktor-Authentifizierung (MFA)

## Eigene Notizen



## Schlüsselquellen

*Derzeit keine verifizierten IAM/SSO-spezifischen Quellen vorhanden. Zu ergänzen: Dokumentation eIAM (BIT), CH-LOGIN, kantonale IAM-Implementierungen.*

## Changelog

- 2026-04-14: Initiale Erstellung des IAM & SSO-Kapitels als konzeptionellen Rahmen; keine IAM/SSO-spezifischen Funde aus dem Recherche-Batch verfügbar (Funde betrafen Fachanwendungen/Governance und wurden nicht integriert, da kein IAM/SSO-Bezug); Seite als Platzhalter mit konzeptionellem Rahmen und Evaluationskriterien angelegt — Flag für PL: IAM/SSO-spezifische Quellen (eIAM, CH-LOGIN, SAML/OIDC-Implementierungen) noch zu recherchieren
