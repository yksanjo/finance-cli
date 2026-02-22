# Production Readiness Checklist

## Engineering Gates

- [x] Unit or smoke tests exist for core execution path
- [x] CI workflow validates test execution
- [x] Security baseline files present (LICENSE, SECURITY, CONTRIBUTING)
- [x] Architecture and threat model documented

## Release Criteria

1. Test suite passes in CI
2. README quick-start is accurate
3. Critical configuration values are environment-driven
4. Errors are surfaced with clear operator context
