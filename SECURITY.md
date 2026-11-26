# Security Policy

## Reporting a vulnerability

Please do not report security vulnerabilities in public issues, discussions or pull requests.

Report them privately through GitHub: open the repository's **Security** tab and choose **Report a vulnerability**, or go straight to [the private report form](https://github.com/egedursun/weavers-of-the-void/security/advisories/new).

Include what you can of the following:

- the affected version or commit;
- the component (backend, frontend, image worker, provider gateway setup, Docker setup);
- how to reproduce it, and what an attacker could do with it;
- any idea of a fix.

## What happens next

- You get an acknowledgement within 5 working days.
- The maintainers confirm the problem, judge its severity and keep you informed while a fix is prepared.
- The fix is released, and a GitHub security advisory is published with credit to you, unless you prefer to stay anonymous.
- Please give the maintainers a reasonable time to release a fix before you disclose the problem; 90 days is the usual limit.

## Supported versions

Security fixes go into the latest release. Weavers of the Void is self-hosted, so upgrading to the latest release is how an installation receives them.

## Scope

In scope: the code in this repository and the official Docker setup.

Out of scope, and best reported to their own projects: vulnerabilities in third-party dependencies, the Bifrost gateway, the vendors' agent programs and the AI providers themselves. If such a problem affects Weavers of the Void in a way the project can mitigate, report that part here.

## Keeping an installation safe

- Keep the server behind HTTPS and set `AERONA_COOKIE_SECURE=true`.
- Set a strong `AERONA_SECRET_KEY`; provider credentials are encrypted with it.
- Do not expose the gateway, the media store or the image worker to the internet; the Docker setup keeps them on its internal network or binds them to `127.0.0.1`.
- Treat world packages from strangers like any other uploaded file; imports are checked, but keep the server up to date.
