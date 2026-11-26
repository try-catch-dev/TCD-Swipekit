# Security Policy

## Supported Versions

Security fixes are applied to the latest release on the `main` branch.

| Version | Supported |
| :--- | :--- |
| `0.1.x` / `main` | Yes |

## Reporting a Vulnerability

If you discover a security vulnerability (for example, template injection, unsafe local file disclosure, or credential leakage), **please do not open a public GitHub issue**.

Instead, please report it privately via **GitHub Security Advisories** (`Security` → `Advisories` → `Report a vulnerability` on this repository). Include:

- A description of the issue and affected version
- Steps to reproduce or a minimal proof-of-concept YAML/command
- Suggested mitigation if available

We aim to acknowledge reports within 72 hours and provide a fix promptly.

## Security Notes for Users

- **Untrusted URLs (`sites.yml`):** `swipekit generate web` opens target URLs in a headless Chromium browser via Playwright. Only point `sites.yml` at websites you trust.
- **API Tokens (`GITHUB_TOKEN`, `OPENAI_API_KEY`):** Credentials are read exclusively from environment variables and are never written into `deck.yaml`, `caption.md`, or `preview.html`.
- **HTML Escaping:** User-provided titles, descriptions, and code snippets are HTML-escaped via Jinja2 autoescaping and safe inline formatters before rendering.
