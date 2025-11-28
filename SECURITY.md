# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 3.2.x   | ✅ Active support  |
| 3.1.x   | ✅ Security fixes  |
| 3.0.x   | ⚠️ Critical only   |
| < 3.0   | ❌ End of life     |

## Reporting a Vulnerability

If you discover a security vulnerability in M4STCLAW, please report it responsibly:

1. **Do NOT** open a public GitHub issue
2. Email: m4stanuj@users.noreply.github.com
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Suggested fix (if any)

### Response Timeline
- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 5 business days
- **Fix & Disclosure**: Within 30 days (coordinated disclosure)

## Security Measures

M4STCLAW implements the following security controls:

- **Localhost-only binding** — No external network exposure by default
- **Safety guard** — All shell commands are validated against destructive patterns before execution
- **API key isolation** — Keys stored exclusively in `.env`, never in source code
- **Rate limiting** — Per-provider request throttling prevents abuse
- **Input sanitization** — All user inputs are sanitized before LLM processing
