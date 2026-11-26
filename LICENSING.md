# Licensing

Weavers of the Void is free software. Using it costs nothing: personal use, commercial use, self-hosting on your own machine, inside a company or in your own cloud account, with every feature and every expansion. There is no license fee, no seat count and no artificial limit on users, universes or epochs. Your hardware is the only limit.

This file explains which license covers which part of the repository and what each one asks of you. The license texts themselves are binding. This summary is not legal advice.

## At a glance

| What | License | SPDX identifier | Text |
|---|---|---|---|
| Everything in this repository unless listed below: the engine and The Loom, the agent infrastructure, agent instructions and prompts, the provider layer, the data model, the API server, the frontend, the documentation and the images | GNU Affero General Public License v3.0 only, with an additional permission for outputs | `AGPL-3.0-only` | [LICENSE](LICENSE) |
| The image worker (`image-worker/`) | Apache License 2.0 | `Apache-2.0` | [image-worker/LICENSE](image-worker/LICENSE) |
| The open format specifications: the World Package, the Codex and the HTTP API | Creative Commons Attribution 4.0 International | `CC-BY-4.0` | [LICENSES/CC-BY-4.0.txt](LICENSES/CC-BY-4.0.txt) |
| The KayKit 3D models (`frontend/public/models/kaykit/`) | CC0 1.0 Universal | `CC0-1.0` | [LICENSES/CC0-1.0.txt](LICENSES/CC0-1.0.txt) |
| Other third-party code, fonts, models, services and agent programs | their own licenses | various | [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) |

Copies of every license used by the project's own files are kept in [LICENSES/](LICENSES/). The machine-readable map of paths to licenses is [REUSE.toml](REUSE.toml), in the format of the [REUSE specification](https://reuse.software/). The source files carry no license headers, because the project's code has no comments of any kind; `REUSE.toml` is where each file's license is recorded.

## What you may do

- Run Weavers of the Void for any purpose, including commercial work for clients.
- Study and change the source code.
- Self-host it for yourself, your team or your organisation, on your own hardware or in your own cloud account.
- Fork it and publish your fork, commercially or not, under your own name and brand.
- Offer it as a hosted service to others and set your own prices.

## What the AGPL asks of you

- **When you distribute the software** (a copy, a fork, a Docker image, an installer), pass on the AGPL-3.0 with it and make the complete corresponding source code available, as section 6 of the license describes.
- **When you run a modified version on a server that other people use over a network**, section 13 of the license applies: offer those users the corresponding source code of your modified version, for example through a link in the application. Running an unmodified release adds no obligation beyond the license itself, though pointing your users to the source is good practice.
- Keep the copyright and license notices intact, including [NOTICE](NOTICE), and mark your changes with a date.
- The license gives no warranty. See sections 15 and 16 of the [LICENSE](LICENSE).

The AGPL-3.0 covers the software and works based on it. It does not reach the worlds you make with it (see below), the AI providers you connect, or the separate programs that run next to the application.

## Your worlds are yours

The universes you create and everything the software produces for you belong to you: the lore, the chronicle, the Universe Book (HTML and PDF), the Codex (Markdown and ZIP), the World Package (`.aerona`) and the generated images. The project claims no license fee, royalty or other right over them, and they do not fall under the AGPL because the software made them.

Two things still apply to your outputs: the terms of the AI providers whose models you connect, and the law where you live and publish.

### Additional permission for outputs

The software places some of its own material into the files it produces for you, such as the layout, styles and markup of the Universe Book and the Codex, the structure of a World Package and the project's mark on the book. So that your outputs carry no license obligations, the copyright holders grant this additional permission under section 7 of the AGPL-3.0:

> You may use, copy, modify and distribute the Universe Book, the Codex, the World Package, the generated images and any other output of Weavers of the Void, including the parts of the software that the software itself placed in that output, under terms of your choice, without the requirements of the GNU Affero General Public License. This permission does not cover third-party material that keeps its own license, such as fonts embedded in a document, and it does not grant any right to the Weavers of the Void trademarks beyond what TRADEMARKS.md allows.

Anyone who distributes a modified version may remove this permission from their version, as section 7 allows.

## The open format specifications

The descriptions of the three formats through which worlds leave the application are published under CC BY 4.0, so that anyone can write readers, writers, importers and integrations under any license:

| Format | Specification |
|---|---|
| World Package (`.aerona`) | Section 23.1 "Package format `.aerona`" of [docs/spec/02-world-core.md](docs/spec/02-world-core.md), and the package manifest under "Export" in section 4 "Lifecycle acts" of [docs/spec/20-library-of-universes.md](docs/spec/20-library-of-universes.md) |
| Codex | Section 10.1 "Codex" of [docs/spec/07-gods-and-progression.md](docs/spec/07-gods-and-progression.md) |
| HTTP API | [docs/spec/11-api.md](docs/spec/11-api.md) as a whole, and the OpenAPI document the server publishes at `/openapi.json` |

The CC BY 4.0 covers the description of each format: its text, tables and schemas. The rest of those documents stays under the AGPL-3.0, and so does the code that implements the formats in this repository. Attribution can read: "Format specification by the Weavers of the Void project, licensed under CC BY 4.0."

## The image worker

The image worker in [`image-worker/`](image-worker/) is a standalone text-to-image service behind a small HTTP contract. It is licensed under the Apache License 2.0 so that it can be used on its own, in other projects and in closed products. It holds no model weights; it downloads them at first use, and they keep the licenses on their model cards.

## AI providers, the gateway and the agent programs

Weavers of the Void connects to language and image models that you choose: API keys and local model servers through the Bifrost gateway, and subscription logins through the vendors' own agent programs (Claude Code, the Codex CLI, the Gemini CLI and the GitHub Copilot CLI) driven over the Agent Client Protocol.

- These programs are separate works. None of them is stored in this repository; `npm ci`, `uv sync` or `docker compose build` downloads them on your machine, and you accept them under their vendors' terms.
- Bifrost, the ACP adapters, the Codex CLI and the Gemini CLI are open source (Apache-2.0). **Claude Code and the Claude Agent SDK are proprietary (Anthropic, all rights reserved), and the GitHub Copilot CLI is proprietary under its own license.** Anyone who publishes a built image or installer must follow the rules in section 1 of [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md): leave the Anthropic packages out unless Anthropic has permitted otherwise, and keep the Copilot license in the build.
- Your use of each provider, its models and its subscriptions is governed by that provider's terms. Several vendors forbid using a personal subscription in another product or for other people; the application shows this warning on every subscription card, and a hosted service for others connects API keys instead.
- The project has no agreement with any provider and receives nothing from your use of one. You pay your provider directly.

## Names and logos

The AGPL-3.0 covers the code and files, not the name. "Weavers of the Void", its logo and its visual identity are the project's trademarks. You may say truthfully that your product or service is compatible with Weavers of the Void or based on it, but a fork or a hosted service must carry its own name and must not look like the official product. The rules are in [TRADEMARKS.md](TRADEMARKS.md). They never restrict the rights that the software licenses give you.

## Contributions

Contributions are accepted under the license of the files they change, including the additional permission for outputs, and every commit is signed off under the [Developer Certificate of Origin](DCO). See [CONTRIBUTING.md](CONTRIBUTING.md).

## Questions

Licensing questions go to a GitHub issue with the `licensing` label. Security reports never go to a public issue; see [SECURITY.md](SECURITY.md).
