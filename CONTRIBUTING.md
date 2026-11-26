# Contributing to Weavers of the Void

Thank you for helping. Issues, ideas, reviews and pull requests are all welcome. This guide covers how to set up, the rules every change follows, and the legal side of contributing.

## Before you start

- **Bugs:** open an issue with the bug template. Say what you did, what you expected and what happened, with the version and the logs.
- **Features, expansions and mechanics:** open an issue first and describe the idea, so that it can be discussed before you spend time on it.
- **Security problems:** never in public. Follow [SECURITY.md](SECURITY.md).
- Everyone in the project follows the [Code of Conduct](CODE_OF_CONDUCT.md).

## Setting up

```sh
make install
make dev
```

The backend runs at http://127.0.0.1:8000 and the frontend at http://127.0.0.1:5173. The [README](README.md#local-development) has the details, including Docker, the image worker and the provider setup.

Turn on the commit hooks once:

```sh
git config core.hooksPath .githooks
```

## The rules every change follows

The project holds itself to eight standing rules. They are written out in full in [CLAUDE.md](CLAUDE.md) and summarised in the README under [Engineering principles](README.md#engineering-principles). They bind human and AI contributors alike, and most are checked by the scripts in [`scripts/`](scripts/) and the commit hooks.

1. **Only the tests that matter.** Run the static checks and the tests that cover your change.
2. **The lore follows the seed.** No text the model sees may push an image, theme, tone, conflict, gender or look that the player's seed did not ask for. `scripts/check_prompt_bias.py` checks it.
3. **Every dynamic is fully wired.** Anything new reaches the engine, the agent tools, the prompts, the API, the screens, the Codex, the book, the integrity checks and the spec.
4. **No comments or docstrings, in any language.** Code explains itself through names and structure. `scripts/check_source_rules.py` must report zero violations. This is also why source files carry no license headers; [REUSE.toml](REUSE.toml) records each file's license instead.
5. **A production-grade, gamified frontend** built from the design system, with every state covered, from phone width up, in light and dark.
6. **The god controls everything.** Everything the engine creates or changes can be created, edited, held and deleted from the app.
7. **Every change reaches the book and the Codex.**
8. **Every defect closes its class:** a test that fails on the old code, a guard so it cannot return, and a search for its siblings.

Checks to run before you push, for the parts you touched:

| Part | Checks |
|---|---|
| Backend | `ruff check`, `ruff format --check`, `mypy`, `lint-imports`, and the test files that cover the change |
| Frontend | `npx tsc -b`, `npx eslint`, `npx prettier --check`, and the vitest files that cover the change |
| Everything | `python scripts/check_source_rules.py` and the other `scripts/check_*.py` guards the hooks run |

## Pull requests

- Keep one pull request to one change, and describe what it changes and why.
- Write commit messages that say what the change does for the world or the player.
- Fill in the pull request template.
- A maintainer reviews every pull request. See [GOVERNANCE.md](GOVERNANCE.md) for how decisions are made.

## Licensing of contributions

By contributing, you agree that your contribution is licensed under the license of the files it changes: the [GNU AGPL-3.0](LICENSE) for most of the repository, including the additional permission for outputs described in [LICENSING.md](LICENSING.md); the [Apache License 2.0](image-worker/LICENSE) for `image-worker/`; and [CC BY 4.0](LICENSES/CC-BY-4.0.txt) for the format specifications. You keep the copyright in your contribution. There is no copyright assignment and no contributor license agreement.

Do not submit code, text, images or models that you may not license this way, such as code copied from a project with an incompatible license, or assets without a clear license. If you add a third-party component, add it to [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and, if it lives in this repository, to [REUSE.toml](REUSE.toml), in the same pull request.

### Sign off every commit

Every commit must carry a `Signed-off-by` line, which certifies the [Developer Certificate of Origin](DCO): that you wrote the change or otherwise have the right to submit it under the project's licenses.

```sh
git commit -s -m "Your message"
```

This adds a line such as:

```
Signed-off-by: Your Name <you@example.com>
```

Use your real name or a name you are known by, and an e-mail address that reaches you. A check on every pull request fails when a commit has no sign-off. To sign off commits you already made, run `git rebase --signoff main` and push again.

### Contributions made with AI tools

You may use AI tools. You are still the contributor: you must review and understand everything you submit, be able to sign off on it under the DCO, and make sure it follows the rules above, including the lore rule.

## Payment

Contributions are voluntary. The project does not pay for contributions and promises no payment; see [GOVERNANCE.md](GOVERNANCE.md#how-the-project-pays-for-itself).
