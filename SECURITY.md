# Security Policy

## Supported Versions

The following versions of RDagent are currently supported with security updates:

| Version | Supported | Notes |
|---------|-----------|-------|
| v0.1.x  | ✅ Yes    | Currently maintained and receiving security updates |
| < v0.1  | ❌ No     | Older versions are no longer supported |

## Reporting a Vulnerability

We take security seriously and appreciate responsible disclosure of security vulnerabilities.

### Reporting Process

**DO NOT** open public GitHub issues for security vulnerabilities. Instead, please email your security report to:

📧 **security@example.com**

Please include the following information in your report:

- **Description**: Clear description of the vulnerability
- **Steps to Reproduce**: Detailed steps needed to reproduce the issue
- **Impact Assessment**: Potential impact and severity of the vulnerability
- **Suggested Fix**: Any proposed solution or mitigation (if available)

### Response Timeline

- **Acknowledgment**: You will receive acknowledgment of your report within 48 hours
- **Initial Assessment**: We will provide an initial assessment within 7 days
- **Resolution**: We work to patch confirmed vulnerabilities and release updates as quickly as possible

## Disclosure Policy

- Security fixes are released publicly immediately after a patch is deployed
- We will provide credit to security reporters in release notes (with your permission)
- Please allow us reasonable time to address the issue before public disclosure

## Security Best Practices

When using RDagent, please follow these security best practices:

### Secret Management

- **Never hardcode API keys** or sensitive credentials in your code
- **Use `.env` file** for storing sensitive configuration (see `.env.example` for reference)
- Ensure your `.env` file is added to `.gitignore` to prevent accidental commits

### Code Execution Security

- Always run untrusted code in **Docker sandbox environment**
- The Docker container provides isolation and prevents direct system access
- Configure resource limits (CPU, memory) to prevent denial-of-service attacks

### Sensitive Data Handling

- RDagent includes built-in redaction for sensitive fields
- The `observability/redaction.py` module automatically sanitizes sensitive information in logs
- Review logs carefully to ensure sensitive data is properly redacted before sharing

## Questions or Concerns?

If you have questions about this security policy or need to report an issue, please contact us at security@example.com.

---

Last Updated: 2026-03-09
