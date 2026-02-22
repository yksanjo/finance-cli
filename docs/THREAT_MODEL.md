# Threat Model

## Assets

- Customer and operational data
- Security/compliance findings and reports
- API keys and credentials from environment variables

## Trust Boundaries

1. CLI or API input surface
2. External integrations (email, payment APIs, WHOIS, web requests)
3. Local persistence and generated reports

## Primary Threats

- Input injection and malformed content parsing
- Credential leakage through logs or committed files
- Insecure dependency or vulnerable package versions
- False-negative risk in compliance/security assessments

## Controls

- Strict parsing and input validation in core modules
- Environment-variable based secret handling only
- CI test gate on every push/PR
- Repository-level security policy and responsible disclosure path
