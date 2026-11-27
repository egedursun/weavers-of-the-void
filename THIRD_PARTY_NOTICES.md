# Third-Party Notices

Weavers of the Void is built on open-source software, a few free assets and some programs from other vendors. Each of them keeps its own license. This file lists them so that anyone who uses, hosts or redistributes Weavers of the Void knows what comes with it. The project's own licensing is described in [LICENSING.md](LICENSING.md).

The inventory was taken on 2026-11-26 from the lock files: `frontend/package-lock.json`, `backend/uv.lock`, `image-worker/uv.lock` and `deploy/agents/package-lock.json`. It covers the provider gateway and the agent programs of the provider layer. Only runtime dependencies are listed. Development tools (linters, type checkers, test runners, build plugins) are not shipped. The inventory is refreshed before every release.

## Contents

1. [What needs attention before redistributing](#1-what-needs-attention-before-redistributing)
2. [Included in this repository](#2-included-in-this-repository)
3. [Fonts](#3-fonts)
4. [Models downloaded at first use](#4-models-downloaded-at-first-use)
5. [Services started next to the application](#5-services-started-next-to-the-application)
6. [Agent programs](#6-agent-programs)
7. [Frontend runtime packages (npm)](#7-frontend-runtime-packages-npm)
8. [Backend runtime packages (Python)](#8-backend-runtime-packages-python)
9. [Image worker runtime packages (Python)](#9-image-worker-runtime-packages-python)
10. [Agent programs and their packages (npm)](#10-agent-programs-and-their-packages-npm)

## 1. What needs attention before redistributing

Nothing below is stored in this repository. Each program is downloaded by `npm ci`, `uv sync`, `docker compose build` or on first use, on the machine of the person who installs Weavers of the Void, and is accepted under its vendor's terms by that person. These notes matter only to someone who publishes a built copy, such as a Docker image, an installer or a hosted service.

| Program | License | What a redistributor must do |
|---|---|---|
| Claude Code (`@anthropic-ai/claude-code`) and the Claude Agent SDK (`@anthropic-ai/claude-agent-sdk`) | Proprietary. "© Anthropic PBC. All rights reserved", use subject to Anthropic's legal agreements | Do not include them in a published image or package unless Anthropic has permitted it in writing. A published build leaves them out, and the person who installs it adds them with `npm ci` in `deploy/agents`. |
| GitHub Copilot CLI (`@github/copilot`) | Proprietary GitHub Copilot CLI License | Redistribution is allowed only unmodified, only as part of an application with more functionality than the CLI, never on its own, with a copy of its license and its notices kept. Weavers of the Void meets these conditions; a redistributor keeps `node_modules/@github/copilot/LICENSE.md` in the build. |
| NVIDIA CUDA libraries (`nvidia-*`, `cuda-*`, the `nvidia/cuda` base image) | Proprietary NVIDIA Software License Agreement and CUDA Toolkit EULA | They come with the image worker's `diffusers` backend. The EULA allows redistributing the runtime parts with an application; the NVIDIA notices stay in the image. |
| Vendor subscriptions and accounts (Claude, ChatGPT, Gemini, GitHub Copilot) | The vendors' terms of service | A subscription login belongs to the person who signs in. Several vendors forbid using a personal subscription inside another product or for others, which is why the application warns on every subscription card. A hosted service connects API keys through the gateway instead. |

All other components are under open-source licenses compatible with the project's AGPL-3.0-only license. The copyleft ones among them:

- **EbookLib** (AGPL-3.0-or-later) is used by the backend only, not by the Apache-licensed image worker.
- **pycountry** (LGPL-2.1-only) and **pyte** (LGPL-3.0) are used as unmodified libraries.
- **Pyphen** is offered under a choice of GPL-2.0-or-later, LGPL-2.1-or-later or MPL-1.1; the project uses it under the LGPL.
- **lightningcss** (MPL-2.0) is used unmodified in the frontend build.
- **MinIO** (AGPL-3.0, the `pgsty/minio` build) and **socat** (GPL-2.0) run as separate containers and are not linked into the application.
- **pypdfium2** bundles PDFium, which carries further notices inside the wheel.

## 2. Included in this repository

| Component | Where | License | Notes |
|---|---|---|---|
| shadcn-admin (Sat Naing) | parts of `frontend/src` | MIT | Full notice in [`frontend/THIRD_PARTY_LICENSE_shadcn-admin.txt`](frontend/THIRD_PARTY_LICENSE_shadcn-admin.txt). |
| KayKit: Halloween Bits 1.0 (Kay Lousberg) | `frontend/public/models/kaykit/halloween/` | CC0-1.0 | Notice in the folder's `LICENSE.txt`. Credit is welcome, not required. |
| KayKit: Medieval Hexagon Pack 1.0 (Kay Lousberg) | `frontend/public/models/kaykit/hexagon/` | CC0-1.0 | Notice in the folder's `LICENSE.txt`. Credit is welcome, not required. |

## 3. Fonts

The fonts are installed from npm and bundled into the built frontend. The SIL Open Font License allows bundling them with software and embedding them in documents, and does not allow selling the fonts on their own.

| Font | Package | License |
|---|---|---|
| Inter | `@fontsource-variable/inter` | OFL-1.1 |
| Nunito Sans | `@fontsource-variable/nunito-sans` | OFL-1.1 |
| Cinzel | `@fontsource/cinzel` | OFL-1.1 |
| Cinzel Decorative | `@fontsource/cinzel-decorative` | OFL-1.1 |

## 4. Models downloaded at first use

No model weights are stored in this repository or in the Docker images. The application downloads them from Hugging Face the first time they are needed, and they stay under the license on their model cards.

| Model | Used by | License on the model card |
|---|---|---|
| `Xenova/multilingual-e5-small` (ONNX export of `intfloat/multilingual-e5-small`) | backend, local text embeddings | MIT (upstream `intfloat/multilingual-e5-small`) |
| `intfloat/multilingual-e5-small` (vocabulary file) | backend, local text embeddings | MIT |
| `mflux-community/z-image-turbo-mflux-q4` | image worker, MLX backend default | Apache-2.0 |
| `unsloth/Z-Image-Turbo-unsloth-bnb-4bit` | image worker, diffusers backend default | Apache-2.0 |

An operator can configure any other model, and its license is then the operator's to check. Language models reached through a provider (an API key, a subscription or a local model server) are used under that provider's terms.

## 5. Services started next to the application

`docker compose` and `make dev` start these programs as separate processes. They talk to the application over the network and are not linked into it.

| Service | Image or package | License | Role |
|---|---|---|---|
| Bifrost | `maximhq/bifrost:v2.6.0` (Docker); `@maximhq/bifrost@1.6.3` launcher with transport `v2.6.0` (`make gateway`) | Apache-2.0 | The provider gateway: API keys and local model servers are reached through it. Its configuration is `deploy/bifrost/config.json`. |
| MinIO | `pgsty/minio` | AGPL-3.0 | The S3-compatible media store. |
| socat | `alpine/socat` | GPL-2.0 | The optional port bridge for the MinIO console. |
| nginx | `nginxinc/nginx-unprivileged` | BSD-2-Clause | Serves the built frontend. |
| Node.js | `node:24` (build stage; the `node` binary is copied into the backend image to run the agent programs) | MIT, with the notices of its bundled libraries | Runs the agent programs. |
| Python | `python:3.13-slim-trixie`, `ghcr.io/astral-sh/uv` | PSF-2.0; uv is MIT OR Apache-2.0 | Runs the backend. |
| NVIDIA CUDA | `nvidia/cuda:13.0.3-base-ubuntu24.04` | NVIDIA Software License Agreement | Base of the GPU image worker. |

The Debian and Ubuntu base images contain operating system packages under their own licenses, listed in each image's `/usr/share/doc/*/copyright`.

## 6. Agent programs

`deploy/agents/package.json` installs the vendors' own agent programs, which the server drives for subscription logins through the Agent Client Protocol. The backend image installs them in `/opt/agents`; `make install` installs them locally. Their full dependency trees are in [section 10](#10-agent-programs-and-their-packages-npm).

| Program | Package | Version | License |
|---|---|---|---|
| Claude agent for ACP | `@agentclientprotocol/claude-agent-acp` | 0.112.0 | Apache-2.0 |
| Codex agent for ACP | `@agentclientprotocol/codex-acp` | 2.12.0 | Apache-2.0 |
| Claude Code | `@anthropic-ai/claude-code` | 2.1.332 | Proprietary (Anthropic). See section 1. |
| GitHub Copilot CLI | `@github/copilot` | 1.0.116 | Proprietary (GitHub Copilot CLI License). See section 1. |
| Gemini CLI | `@google/gemini-cli` | 0.71.1 | Apache-2.0 |
| Codex CLI | `@openai/codex` | 0.172.0 | Apache-2.0 |

## 7. Frontend runtime packages (npm)

| Package | Version | License |
|---|---|---|
| @babel/runtime | 7.29.10 | MIT |
| @dimforge/rapier3d-compat | 0.12.0 | Apache-2.0 |
| @floating-ui/core | 1.8.0 | MIT |
| @floating-ui/dom | 1.8.0 | MIT |
| @floating-ui/react-dom | 2.1.9 | MIT |
| @floating-ui/utils | 0.2.12 | MIT |
| @fontsource-variable/inter | 5.3.0 | OFL-1.1 |
| @fontsource-variable/nunito-sans | 5.3.0 | OFL-1.1 |
| @fontsource/cinzel | 5.3.0 | OFL-1.1 |
| @fontsource/cinzel-decorative | 5.3.0 | OFL-1.1 |
| @hookform/resolvers | 5.9.2 | MIT |
| @jridgewell/gen-mapping | 0.3.13 | MIT |
| @jridgewell/remapping | 2.3.5 | MIT |
| @jridgewell/resolve-uri | 3.1.2 | MIT |
| @jridgewell/sourcemap-codec | 1.6.0 | MIT |
| @jridgewell/trace-mapping | 0.3.31 | MIT |
| @mediapipe/tasks-vision | 0.10.17 | Apache-2.0 |
| @monogrid/gainmap-js | 3.7.2 | MIT |
| @oxc-project/types | 0.156.0 | MIT |
| @radix-ui/number | 1.1.3 | MIT |
| @radix-ui/primitive | 1.2.0 | MIT |
| @radix-ui/react-alert-dialog | 1.2.1 | MIT |
| @radix-ui/react-arrow | 1.1.17 | MIT |
| @radix-ui/react-avatar | 1.3.1 | MIT |
| @radix-ui/react-checkbox | 1.4.1 | MIT |
| @radix-ui/react-collapsible | 1.2.1 | MIT |
| @radix-ui/react-collection | 1.2.0 | MIT |
| @radix-ui/react-compose-refs | 1.1.5 | MIT |
| @radix-ui/react-context | 1.3.0 | MIT |
| @radix-ui/react-dialog | 1.3.1 | MIT |
| @radix-ui/react-direction | 1.2.0 | MIT |
| @radix-ui/react-dismissable-layer | 1.2.1 | MIT |
| @radix-ui/react-dropdown-menu | 2.2.1 | MIT |
| @radix-ui/react-focus-guards | 1.2.0 | MIT |
| @radix-ui/react-focus-scope | 1.3.1 | MIT |
| @radix-ui/react-icons | 1.3.2 | MIT |
| @radix-ui/react-id | 1.1.4 | MIT |
| @radix-ui/react-label | 2.1.17 | MIT |
| @radix-ui/react-menu | 2.2.1 | MIT |
| @radix-ui/react-popover | 1.3.1 | MIT |
| @radix-ui/react-popper | 1.4.0 | MIT |
| @radix-ui/react-portal | 1.2.0 | MIT |
| @radix-ui/react-presence | 1.1.11 | MIT |
| @radix-ui/react-primitive | 2.2.0 | MIT |
| @radix-ui/react-progress | 1.2.1 | MIT |
| @radix-ui/react-radio-group | 1.5.1 | MIT |
| @radix-ui/react-roving-focus | 1.2.1 | MIT |
| @radix-ui/react-scroll-area | 1.4.0 | MIT |
| @radix-ui/react-select | 2.4.1 | MIT |
| @radix-ui/react-separator | 1.2.0 | MIT |
| @radix-ui/react-slot | 1.5.0 | MIT |
| @radix-ui/react-switch | 1.4.1 | MIT |
| @radix-ui/react-tabs | 1.2.1 | MIT |
| @radix-ui/react-toggle | 1.2.1 | MIT |
| @radix-ui/react-toggle-group | 1.2.1 | MIT |
| @radix-ui/react-tooltip | 1.4.1 | MIT |
| @radix-ui/react-use-callback-ref | 1.1.5 | MIT |
| @radix-ui/react-use-controllable-state | 1.3.0 | MIT |
| @radix-ui/react-use-effect-event | 0.0.5 | MIT |
| @radix-ui/react-use-is-hydrated | 0.1.3 | MIT |
| @radix-ui/react-use-layout-effect | 1.1.4 | MIT |
| @radix-ui/react-use-rect | 1.1.4 | MIT |
| @radix-ui/react-use-size | 1.1.5 | MIT |
| @radix-ui/react-visually-hidden | 1.2.13 | MIT |
| @radix-ui/rect | 1.1.3 | MIT |
| @react-three/drei | 10.7.9 | MIT |
| @react-three/fiber | 9.8.2 | MIT |
| @reduxjs/toolkit | 2.13.0 | MIT |
| @rolldown/binding-darwin-arm64 | 1.2.16 | MIT |
| @rolldown/pluginutils | 1.0.1 | MIT |
| @standard-schema/spec | 1.1.0 | MIT |
| @standard-schema/utils | 0.3.0 | MIT |
| @tailwindcss/node | 4.3.3 | MIT |
| @tailwindcss/oxide | 4.3.3 | MIT |
| @tailwindcss/oxide-darwin-arm64 | 4.3.3 | MIT |
| @tailwindcss/vite | 4.3.3 | MIT |
| @tanstack/history | 1.162.5 | MIT |
| @tanstack/query-core | 5.105.0 | MIT |
| @tanstack/react-query | 5.105.0 | MIT |
| @tanstack/react-router | 1.170.46 | MIT |
| @tanstack/react-store | 0.11.2 | MIT |
| @tanstack/react-table | 8.21.3 | MIT |
| @tanstack/react-virtual | 3.14.24 | MIT |
| @tanstack/router-core | 1.171.39 | MIT |
| @tanstack/store | 0.11.2 | MIT |
| @tanstack/table-core | 8.21.3 | MIT |
| @tanstack/virtual-core | 3.19.9 | MIT |
| @tweenjs/tween.js | 23.1.3 | MIT |
| @types/d3-array | 3.2.2 | MIT |
| @types/d3-color | 3.1.3 | MIT |
| @types/d3-ease | 3.0.2 | MIT |
| @types/d3-interpolate | 3.0.4 | MIT |
| @types/d3-path | 3.1.1 | MIT |
| @types/d3-scale | 4.0.9 | MIT |
| @types/d3-shape | 3.2.0 | MIT |
| @types/d3-time | 3.0.4 | MIT |
| @types/d3-timer | 3.0.2 | MIT |
| @types/debug | 4.1.13 | MIT |
| @types/draco3d | 1.4.10 | MIT |
| @types/estree | 1.0.10 | MIT |
| @types/estree-jsx | 1.0.5 | MIT |
| @types/hast | 3.0.5 | MIT |
| @types/mdast | 4.0.4 | MIT |
| @types/ms | 2.1.0 | MIT |
| @types/node | 25.9.9 | MIT |
| @types/offscreencanvas | 2019.7.3 | MIT |
| @types/react | 19.3.0 | MIT |
| @types/react-dom | 19.3.0 | MIT |
| @types/react-reconciler | 0.28.9 | MIT |
| @types/stats.js | 0.17.4 | MIT |
| @types/three | 0.187.0 | MIT |
| @types/unist | 3.0.3 | MIT |
| @types/unist | 2.0.11 | MIT |
| @types/use-sync-external-store | 0.0.6 | MIT |
| @types/webxr | 0.5.24 | MIT |
| @ungap/structured-clone | 1.4.0 | ISC |
| @use-gesture/core | 10.3.1 | MIT |
| @use-gesture/react | 10.3.1 | MIT |
| aria-hidden | 1.2.6 | MIT |
| bail | 2.0.2 | MIT |
| base64-js | 1.5.1 | MIT |
| bezier-js | 6.1.4 | MIT |
| bidi-js | 1.1.0 | MIT |
| buffer | 6.0.3 | MIT |
| camera-controls | 3.1.2 | MIT |
| canvas-color-tracker | 1.3.2 | MIT |
| ccount | 2.0.1 | MIT |
| character-entities | 2.0.2 | MIT |
| character-entities-html4 | 2.1.0 | MIT |
| character-entities-legacy | 3.0.0 | MIT |
| character-reference-invalid | 2.0.1 | MIT |
| class-variance-authority | 0.7.1 | Apache-2.0 |
| clsx | 2.1.1 | MIT |
| cmdk | 1.1.1 | MIT |
| comma-separated-tokens | 2.0.3 | MIT |
| cookie-es | 3.1.1 | MIT |
| cross-env | 7.0.3 | MIT |
| cross-spawn | 7.0.6 | MIT |
| csstype | 3.2.3 | MIT |
| d3-array | 3.2.4 | ISC |
| d3-binarytree | 1.0.2 | MIT |
| d3-color | 3.1.0 | ISC |
| d3-dispatch | 3.0.1 | ISC |
| d3-drag | 3.0.0 | ISC |
| d3-ease | 3.0.1 | BSD-3-Clause |
| d3-force-3d | 3.0.6 | MIT |
| d3-format | 3.1.2 | ISC |
| d3-interpolate | 3.0.1 | ISC |
| d3-octree | 1.1.0 | MIT |
| d3-path | 3.1.0 | ISC |
| d3-quadtree | 3.0.1 | ISC |
| d3-scale | 4.0.2 | ISC |
| d3-scale-chromatic | 3.1.0 | ISC |
| d3-selection | 3.0.0 | ISC |
| d3-shape | 3.2.0 | ISC |
| d3-time | 3.1.0 | ISC |
| d3-time-format | 4.1.0 | ISC |
| d3-timer | 3.0.1 | ISC |
| d3-transition | 3.0.1 | ISC |
| d3-zoom | 3.0.0 | ISC |
| data-bind-mapper | 1.0.3 | MIT |
| date-fns | 4.4.0 | MIT |
| debug | 4.4.3 | MIT |
| decimal.js-light | 2.5.1 | MIT |
| decode-named-character-reference | 1.3.0 | MIT |
| dequal | 2.0.3 | MIT |
| detect-gpu | 5.0.70 | MIT |
| detect-libc | 2.1.2 | Apache-2.0 |
| detect-node-es | 1.1.0 | MIT |
| devlop | 1.1.0 | MIT |
| draco3d | 1.5.9 | Apache-2.0 |
| enhanced-resolve | 5.26.0 | MIT |
| es-toolkit | 1.53.1 | MIT |
| escape-string-regexp | 5.0.0 | MIT |
| estree-util-is-identifier-name | 3.0.0 | MIT |
| eventemitter3 | 5.0.4 | MIT |
| extend | 3.0.2 | MIT |
| fdir | 6.5.0 | MIT |
| fflate | 0.8.3 | MIT |
| fflate | 0.6.11 | MIT |
| float-tooltip | 1.7.5 | MIT |
| force-graph | 1.52.0 | MIT |
| fsevents | 2.3.3 | MIT |
| get-nonce | 1.0.1 | MIT |
| glsl-noise | 0.0.0 | MIT |
| graceful-fs | 4.2.11 | ISC |
| hast-util-sanitize | 5.0.2 | MIT |
| hast-util-to-jsx-runtime | 2.3.7 | MIT |
| hast-util-whitespace | 3.0.0 | MIT |
| hls.js | 1.7.4 | Apache-2.0 |
| html-to-image | 1.11.13 | MIT |
| html-url-attributes | 3.0.1 | MIT |
| ieee754 | 1.2.1 | BSD-3-Clause |
| immediate | 3.0.6 | MIT |
| immer | 11.2.9 | MIT |
| index-array-by | 1.4.2 | MIT |
| inline-style-parser | 0.2.9 | MIT |
| internmap | 2.0.3 | ISC |
| is-alphabetical | 2.0.1 | MIT |
| is-alphanumerical | 2.0.1 | MIT |
| is-decimal | 2.0.1 | MIT |
| is-hexadecimal | 2.0.1 | MIT |
| is-plain-obj | 4.1.0 | MIT |
| is-promise | 2.2.2 | MIT |
| isbot | 5.2.2 | Unlicense |
| isexe | 2.0.0 | ISC |
| its-fine | 2.1.1 | MIT |
| jerrypick | 1.1.2 | MIT |
| jiti | 2.7.0 | MIT |
| js-tokens | 4.0.0 | MIT |
| kapsule | 1.16.3 | MIT |
| lie | 3.3.0 | MIT |
| lightningcss | 1.32.0 | MPL-2.0 |
| lightningcss | 1.33.0 | MPL-2.0 |
| lightningcss-darwin-arm64 | 1.32.0 | MPL-2.0 |
| lightningcss-darwin-arm64 | 1.33.0 | MPL-2.0 |
| lodash-es | 4.18.1 | MIT |
| longest-streak | 3.1.0 | MIT |
| loose-envify | 1.4.0 | MIT |
| lucide-react | 1.65.0 | ISC |
| maath | 0.10.8 | MIT |
| magic-string | 0.30.21 | MIT |
| markdown-table | 3.1.0 | MIT |
| mdast-util-find-and-replace | 3.0.5 | MIT |
| mdast-util-from-markdown | 2.1.0 | MIT |
| mdast-util-gfm | 3.1.0 | MIT |
| mdast-util-gfm-autolink-literal | 2.1.2 | MIT |
| mdast-util-gfm-footnote | 2.1.0 | MIT |
| mdast-util-gfm-strikethrough | 2.0.1 | MIT |
| mdast-util-gfm-table | 2.0.1 | MIT |
| mdast-util-gfm-task-list-item | 2.0.1 | MIT |
| mdast-util-mdx-expression | 2.0.1 | MIT |
| mdast-util-mdx-jsx | 3.2.2 | MIT |
| mdast-util-mdxjs-esm | 2.0.1 | MIT |
| mdast-util-phrasing | 4.1.0 | MIT |
| mdast-util-to-hast | 13.2.2 | MIT |
| mdast-util-to-markdown | 2.2.4 | MIT |
| mdast-util-to-string | 4.0.0 | MIT |
| meshline | 3.3.1 | MIT |
| meshoptimizer | 1.1.1 | MIT |
| micromark | 4.0.3 | MIT |
| micromark-core-commonmark | 2.0.4 | MIT |
| micromark-extension-gfm | 3.0.0 | MIT |
| micromark-extension-gfm-autolink-literal | 2.1.0 | MIT |
| micromark-extension-gfm-footnote | 2.1.0 | MIT |
| micromark-extension-gfm-strikethrough | 2.1.0 | MIT |
| micromark-extension-gfm-table | 2.1.2 | MIT |
| micromark-extension-gfm-tagfilter | 2.0.0 | MIT |
| micromark-extension-gfm-task-list-item | 2.1.0 | MIT |
| micromark-factory-destination | 2.0.1 | MIT |
| micromark-factory-label | 2.0.1 | MIT |
| micromark-factory-space | 2.1.0 | MIT |
| micromark-factory-title | 2.0.1 | MIT |
| micromark-factory-whitespace | 2.0.1 | MIT |
| micromark-util-character | 2.1.1 | MIT |
| micromark-util-chunked | 2.0.1 | MIT |
| micromark-util-classify-character | 2.0.1 | MIT |
| micromark-util-combine-extensions | 2.0.1 | MIT |
| micromark-util-decode-numeric-character-reference | 2.0.2 | MIT |
| micromark-util-decode-string | 2.0.1 | MIT |
| micromark-util-edit-map | 1.0.0 | MIT |
| micromark-util-encode | 2.0.1 | MIT |
| micromark-util-html-tag-name | 2.0.1 | MIT |
| micromark-util-normalize-identifier | 2.0.1 | MIT |
| micromark-util-resolve-all | 2.0.1 | MIT |
| micromark-util-sanitize-uri | 2.0.1 | MIT |
| micromark-util-subtokenize | 2.1.0 | MIT |
| micromark-util-symbol | 2.0.1 | MIT |
| micromark-util-types | 2.0.3 | MIT |
| ms | 2.1.3 | MIT |
| nanoid | 3.3.20 | MIT |
| ngraph.events | 1.4.0 | BSD-3-Clause |
| ngraph.forcelayout | 3.3.1 | BSD-3-Clause |
| ngraph.graph | 20.1.2 | BSD-3-Clause |
| ngraph.merge | 1.0.0 | MIT |
| ngraph.random | 1.2.0 | BSD-3-Clause |
| object-assign | 4.1.1 | MIT |
| openapi-fetch | 0.17.0 | MIT |
| openapi-typescript-helpers | 0.1.0 | MIT |
| parse-entities | 4.0.2 | MIT |
| path-key | 3.1.1 | MIT |
| picocolors | 1.1.1 | ISC |
| picomatch | 4.0.7 | MIT |
| polished | 4.3.1 | MIT |
| postcss | 8.5.32 | MIT |
| potpack | 1.0.2 | ISC |
| preact | 10.29.8 | MIT |
| promise-worker-transferable | 1.0.4 | Apache-2.0 |
| prop-types | 15.8.1 | MIT |
| property-information | 7.2.0 | MIT |
| react | 19.3.1 | MIT |
| react-dom | 19.3.1 | MIT |
| react-force-graph-2d | 1.29.2 | MIT |
| react-force-graph-3d | 1.29.2 | MIT |
| react-hook-form | 7.91.0 | MIT |
| react-is | 16.13.1 | MIT |
| react-is | 19.3.1 | MIT |
| react-kapsule | 2.6.0 | MIT |
| react-markdown | 10.1.0 | MIT |
| react-redux | 9.3.1 | MIT |
| react-remove-scroll | 2.7.2 | MIT |
| react-remove-scroll-bar | 2.3.8 | MIT |
| react-style-singleton | 2.2.3 | MIT |
| react-use-measure | 2.1.7 | MIT |
| recharts | 3.10.1 | MIT |
| redux | 5.0.1 | MIT |
| redux-thunk | 3.1.0 | MIT |
| rehype-sanitize | 6.0.0 | MIT |
| remark-gfm | 4.0.1 | MIT |
| remark-parse | 11.0.0 | MIT |
| remark-rehype | 11.1.2 | MIT |
| remark-stringify | 11.0.0 | MIT |
| require-from-string | 2.0.2 | MIT |
| reselect | 5.2.0 | MIT |
| rolldown | 1.2.16 | MIT |
| scheduler | 0.28.0 | MIT |
| seroval | 1.7.5 | MIT |
| seroval-plugins | 1.7.6 | MIT |
| shebang-command | 2.0.0 | MIT |
| shebang-regex | 3.0.0 | MIT |
| sonner | 2.0.8 | MIT |
| source-map-js | 1.2.2 | BSD-3-Clause |
| space-separated-tokens | 2.0.2 | MIT |
| stats-gl | 2.4.2 | MIT |
| stats.js | 0.17.0 | MIT |
| stringify-entities | 4.0.5 | MIT |
| style-to-object | 2.0.2 | MIT |
| suspend-react | 0.1.3 | MIT |
| tailwind-merge | 3.7.0 | MIT |
| tailwindcss | 4.3.3 | MIT |
| tapable | 2.3.3 | MIT |
| three | 0.170.0 | MIT |
| three | 0.187.0 | MIT |
| three-forcegraph | 1.43.6 | MIT |
| three-mesh-bvh | 0.8.3 | MIT |
| three-render-objects | 1.43.0 | MIT |
| three-stdlib | 2.36.1 | MIT |
| tiny-invariant | 1.3.3 | MIT |
| tinycolor2 | 1.6.0 | MIT |
| tinyglobby | 0.2.17 | MIT |
| trim-lines | 3.0.1 | MIT |
| troika-three-text | 0.52.5 | MIT |
| troika-three-utils | 0.52.5 | MIT |
| troika-worker-utils | 0.52.0 | MIT |
| trough | 2.2.0 | MIT |
| tslib | 2.8.1 | 0BSD |
| tunnel-rat | 0.1.2 | MIT |
| tw-animate-css | 1.4.0 | MIT |
| undici-types | 7.24.6 | MIT |
| unified | 11.0.5 | MIT |
| unist-util-is | 6.0.1 | MIT |
| unist-util-position | 5.0.0 | MIT |
| unist-util-stringify-position | 4.0.0 | MIT |
| unist-util-visit | 5.2.0 | MIT |
| unist-util-visit-parents | 6.1.0 | MIT |
| use-callback-ref | 1.3.3 | MIT |
| use-sidecar | 1.1.3 | MIT |
| use-sync-external-store | 1.7.0 | MIT |
| utility-types | 3.11.0 | MIT |
| vfile | 6.0.3 | MIT |
| vfile-message | 4.0.4 | MIT |
| victory-vendor | 37.4.1 | MIT AND ISC AND BSD-3-Clause |
| vite | 8.3.5 | MIT |
| webgl-constants | 1.1.1 | MIT (declared in the package's README and LICENSE) |
| webgl-sdf-generator | 1.1.1 | MIT |
| which | 2.0.2 | ISC |
| zod | 4.6.7 | MIT |
| zustand | 4.5.7 | MIT |
| zustand | 5.0.16 | MIT |
| zwitch | 2.0.4 | MIT |

## 8. Backend runtime packages (Python)

| Package | Version | License |
|---|---|---|
| aiobotocore | 3.10.0 | Apache-2.0 |
| aiohappyeyeballs | 2.7.1 | PSF-2.0 |
| aiohttp | 3.14.5 | Apache-2.0 AND MIT |
| aioitertools | 0.13.0 | MIT |
| aiosignal | 1.4.0 | Apache-2.0 |
| aiosqlite | 0.22.1 | MIT |
| alembic | 1.20.1 | MIT |
| annotated-doc | 0.0.5 | MIT |
| annotated-types | 0.8.0 | MIT |
| anyio | 4.15.1 | MIT |
| argon2-cffi | 25.1.0 | MIT |
| argon2-cffi-bindings | 26.2.0 | MIT |
| attrs | 26.1.0 | MIT |
| beautifulsoup4 | 4.15.0 | MIT |
| botocore | 1.43.117 | Apache-2.0 |
| brotli | 1.2.1 | MIT |
| brotlicffi | 1.2.1.0 | MIT |
| certifi | 2026.10.23 | MPL-2.0 |
| cffi | 2.1.1 | MIT-0 |
| charset-normalizer | 3.5.2 | MIT |
| click | 8.5.0 | BSD-3-Clause |
| cobble | 0.1.4 | BSD |
| colorama | 0.4.6 | BSD |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause |
| cssselect2 | 0.10.1 | BSD |
| defusedxml | 0.7.1 | PSF-2.0 |
| ebooklib | 0.21 | AGPL-3.0-or-later |
| et-xmlfile | 2.0.0 | MIT |
| fastapi | 0.162.0 | MIT |
| filelock | 4.3.1 | MIT |
| flatbuffers | 25.12.19 | Apache-2.0 |
| fonttools | 4.68.0 | MIT |
| frozenlist | 1.8.0 | Apache-2.0 |
| fsspec | 2026.9.0 | BSD-3-Clause |
| greenlet | 3.5.6 | MIT AND PSF-2.0 |
| h11 | 0.16.0 | MIT |
| hf-xet | 1.8.0 | Apache-2.0 |
| httpcore | 1.0.9 | BSD-3-Clause |
| httpcore2 | 2.16.0 | BSD-3-Clause |
| httptools | 0.9.0 | MIT |
| httpx | 0.28.1 | BSD-3-Clause |
| httpx2 | 2.16.0 | BSD-3-Clause |
| httpx2-jsfetch | 1.0 | BSD-3-Clause |
| huggingface-hub | 2.4.0 | Apache-2.0 |
| idna | 3.20 | BSD-3-Clause |
| jinja2 | 3.1.6 | BSD |
| jiter | 0.19.0 | MIT |
| jmespath | 1.1.0 | MIT |
| jsonschema | 4.26.0 | MIT |
| jsonschema-specifications | 2025.9.1 | MIT |
| langdetect | 1.0.9 | MIT |
| lxml | 6.1.3 | BSD-3-Clause |
| magika | 1.0.3 | Apache-2.0 |
| mako | 1.4.3 | MIT |
| mammoth | 1.13.0 | BSD-2-Clause |
| markdown-it-py | 4.2.0 | MIT |
| markdownify | 1.2.4 | MIT |
| markitdown | 0.1.9 | MIT |
| markupsafe | 3.0.4 | BSD-3-Clause |
| mcp | 2.3.0 | MIT |
| mcp-types | 2.3.0 | MIT |
| mdurl | 0.1.2 | MIT |
| multidict | 7.2.1 | Apache-2.0 |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| onnxruntime | 1.32.0 | MIT |
| openai | 3.59.0 | Apache-2.0 |
| openpyxl | 3.1.5 | MIT |
| opentelemetry-api | 1.45.2 | Apache-2.0 |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pandas | 3.1.1 | BSD-3-Clause |
| pdfminer-six | 20260107 | MIT |
| pdfplumber | 0.11.11 | MIT |
| pillow | 13.0.0 | MIT-CMU |
| propcache | 0.5.4 | Apache-2.0 |
| protobuf | 7.36.2 | BSD-3-Clause |
| pycountry | 26.2.16 | LGPL-2.1-only |
| pycparser | 3.12 | BSD-3-Clause |
| pydantic | 2.14.2 | MIT |
| pydantic-core | 2.50.2 | MIT |
| pydantic-settings | 2.16.2 | MIT |
| pydyf | 0.13.0 | BSD |
| pyjwt | 2.15.1 | MIT |
| pypdf | 7.1.1 | BSD-3-Clause |
| pypdfium2 | 5.15.2 | BSD-3-Clause OR Apache-2.0 (bundles PDFium and its dependency licenses) |
| pyphen | 0.18.1 | GPL-2.0-or-later OR LGPL-2.1-or-later OR MPL-1.1 |
| pyte | 0.8.2 | LGPL-3.0 |
| python-dateutil | 2.9.0.post0 | Apache-2.0 OR BSD-3-Clause |
| python-docx | 1.2.0 | MIT |
| python-dotenv | 1.2.4 | BSD-3-Clause |
| python-multipart | 0.0.32 | Apache-2.0 |
| python-pptx | 1.0.2 | MIT |
| pywin32 | 312 | PSF-2.0 |
| pyyaml | 6.0.3 | MIT |
| referencing | 0.37.0 | MIT |
| regex | 2026.9.29 | Apache-2.0 AND CNRI-Python |
| requests | 2.34.2 | Apache-2.0 |
| rpds-py | 2026.9.1 | MIT |
| scipy | 1.18.1 | BSD |
| sentencepiece | 0.2.3 | Apache-2.0 |
| six | 1.17.0 | MIT |
| sniffio | 1.3.1 | MIT OR Apache-2.0 |
| soupsieve | 4.1.3 | MIT |
| sqlalchemy | 2.1.6 | MIT |
| sse-starlette | 3.6.0 | BSD-3-Clause |
| starlette | 1.10.0 | BSD-3-Clause |
| tantivy | 0.27.0 | MIT |
| tiktoken | 0.14.0 | MIT (declared in the project repository) |
| tinycss2 | 1.5.1 | BSD |
| tinyhtml5 | 2.1.0 | MIT |
| tokenizers | 0.23.3 | Apache-2.0 |
| tqdm | 4.70.1 | MPL-2.0 AND MIT |
| truststore | 0.10.5 | MIT |
| typing-extensions | 4.16.0 | PSF-2.0 |
| typing-inspection | 0.4.4 | MIT |
| tzdata | 2026.6 | Apache-2.0 |
| urllib3 | 2.8.0 | MIT |
| uvicorn | 0.54.0 | BSD-3-Clause |
| uvloop | 0.23.0 | MIT |
| watchfiles | 1.3.0 | MIT |
| wcwidth | 0.9.5 | MIT |
| weasyprint | 70.0 | BSD |
| webencodings | 0.6.1 | BSD |
| websockets | 17.4 | BSD-3-Clause |
| wrapt | 2.5.2 | BSD-2-Clause |
| xlsxwriter | 3.3.4 | BSD-2-Clause |
| yarl | 1.25.1 | Apache-2.0 |
| zopfli | 0.4.3 | Apache-2.0 |

## 9. Image worker runtime packages (Python)

Both optional backends are listed: `mlx` (Apple silicon) and `diffusers` (NVIDIA GPU). An installation has one of them.

| Package | Version | License |
|---|---|---|
| accelerate | 1.15.0 | Apache-2.0 |
| annotated-doc | 0.0.5 | MIT |
| annotated-types | 0.8.0 | MIT |
| anyio | 4.15.1 | MIT |
| bitsandbytes | 0.50.2 | MIT |
| certifi | 2026.10.23 | MPL-2.0 |
| charset-normalizer | 3.5.2 | MIT |
| click | 8.5.0 | BSD-3-Clause |
| colorama | 0.4.6 | BSD |
| contourpy | 1.4.0 | BSD-3-Clause |
| cuda-bindings | 13.4.4 | Apache-2.0 |
| cuda-pathfinder | 1.8.5 | Apache-2.0 |
| cuda-toolkit | 13.2.2 | LicenseRef-NVIDIA-Proprietary (NVIDIA Software License Agreement) |
| cycler | 0.12.1 | BSD |
| diffusers | 0.42.1 | Apache-2.0 |
| fastapi | 0.162.0 | MIT |
| filelock | 4.2.5 | MIT |
| fonttools | 4.68.0 | MIT |
| fsspec | 2026.9.0 | BSD-3-Clause |
| h11 | 0.16.0 | MIT |
| hf-transfer | 0.1.9 | Apache-2.0 (declared in the project repository) |
| hf-xet | 1.8.0 | Apache-2.0 |
| httpcore | 1.0.9 | BSD-3-Clause |
| httptools | 0.9.0 | MIT |
| httpx | 0.28.1 | BSD-3-Clause |
| huggingface-hub | 1.33.0 | Apache-2.0 |
| idna | 3.20 | BSD-3-Clause |
| importlib-metadata | 10.1.0 | Apache-2.0 |
| jinja2 | 3.1.6 | BSD |
| kiwisolver | 1.5.1 | BSD |
| markdown-it-py | 4.2.0 | MIT |
| markupsafe | 3.0.4 | BSD-3-Clause |
| matplotlib | 3.11.2 | PSF-2.0 |
| mdurl | 0.1.2 | MIT |
| mflux | 0.24.0 | MIT (declared in the project repository) |
| mlx | 0.32.4 | MIT |
| mlx-metal | 0.32.4 | MIT |
| mpmath | 1.3.0 | BSD |
| networkx | 3.7 | BSD-3-Clause |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| nvidia-cublas | 13.4.1.3 | LicenseRef-NVIDIA-Proprietary (NVIDIA Software License Agreement) |
| nvidia-cuda-cccl | 13.3.4.3.1 | LicenseRef-NVIDIA-Proprietary |
| nvidia-cuda-cupti | 13.2.86 | LicenseRef-NVIDIA-Proprietary (NVIDIA Software License Agreement) |
| nvidia-cuda-nvrtc | 13.2.86 | LicenseRef-NVIDIA-Proprietary (NVIDIA Software License Agreement) |
| nvidia-cuda-runtime | 13.2.86 | LicenseRef-NVIDIA-Proprietary (NVIDIA Software License Agreement) |
| nvidia-cudnn-cu13 | 9.26.0.51 | LicenseRef-NVIDIA-Proprietary (NVIDIA Software License Agreement) |
| nvidia-cufft | 12.2.0.57 | LicenseRef-NVIDIA-Proprietary (NVIDIA Software License Agreement) |
| nvidia-cufile | 1.17.1.22 | LicenseRef-NVIDIA-Proprietary (NVIDIA Software License Agreement) |
| nvidia-cusolver | 12.2.0.11 | LicenseRef-NVIDIA-Proprietary (NVIDIA Software License Agreement) |
| nvidia-cusparse | 12.7.10.12 | LicenseRef-NVIDIA-Proprietary (NVIDIA Software License Agreement) |
| nvidia-cusparselt-cu13 | 0.8.1 | LicenseRef-NVIDIA-Proprietary |
| nvidia-nccl-cu13 | 2.30.7 | LicenseRef-NVIDIA-Proprietary (NVIDIA Software License Agreement) |
| nvidia-nvjitlink | 13.4.92 | LicenseRef-NVIDIA-Proprietary |
| nvidia-nvshmem-cu13 | 3.7.2 | LicenseRef-NVIDIA-Proprietary (NVIDIA Software License Agreement) |
| nvidia-nvtx | 13.2.86 | LicenseRef-NVIDIA-Proprietary (NVIDIA Software License Agreement) |
| opencv-python | 5.0.0.93 | Apache-2.0 |
| opentelemetry-api | 1.45.2 | Apache-2.0 |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| piexif | 1.1.3 | MIT |
| pillow | 13.0.0 | MIT-CMU |
| platformdirs | 4.14.0 | MIT |
| protobuf | 7.36.2 | BSD-3-Clause |
| psutil | 7.2.2 | BSD-3-Clause |
| pydantic | 2.14.2 | MIT |
| pydantic-core | 2.50.2 | MIT |
| pydantic-settings | 2.16.2 | MIT |
| pygments | 2.21.0 | BSD-2-Clause |
| pyparsing | 3.3.3 | MIT |
| python-dateutil | 3.0.0 | Apache-2.0 OR BSD-3-Clause |
| python-dotenv | 1.2.4 | BSD-3-Clause |
| pyyaml | 6.0.3 | MIT |
| regex | 2026.9.29 | Apache-2.0 AND CNRI-Python |
| requests | 2.34.2 | Apache-2.0 |
| rich | 15.0.0 | MIT |
| safetensors | 0.8.0 | Apache-2.0 |
| sentencepiece | 0.2.2 | Apache-2.0 |
| setuptools | 84.2.1 | MIT |
| shellingham | 1.5.4 | ISC |
| six | 1.17.0 | MIT |
| sse-starlette | 3.6.0 | BSD-3-Clause |
| starlette | 1.10.0 | BSD-3-Clause |
| sympy | 1.14.0 | BSD |
| tokenizers | 0.23.3 | Apache-2.0 |
| toml | 0.10.2 | MIT |
| torch | 2.15.0 | Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND ISC AND MIT AND Zlib |
| tqdm | 4.70.1 | MPL-2.0 AND MIT |
| transformers | 5.22.1 | Apache-2.0 |
| triton | 3.9.0 | MIT |
| typer | 0.27.3 | MIT |
| typing-extensions | 4.16.0 | PSF-2.0 |
| typing-inspection | 0.4.4 | MIT |
| tzdata | 2026.6 | Apache-2.0 |
| urllib3 | 2.8.0 | MIT |
| uvicorn | 0.54.0 | BSD-3-Clause |
| uvloop | 0.23.0 | MIT |
| watchfiles | 1.3.0 | MIT |
| websockets | 17.4 | BSD-3-Clause |
| zipp | 4.1.2 | MIT |

## 10. Agent programs and their packages (npm)

| Package | Version | License |
|---|---|---|
| @agentclientprotocol/claude-agent-acp | 0.112.0 | Apache-2.0 |
| @agentclientprotocol/codex-acp | 2.12.0 | Apache-2.0 |
| @agentclientprotocol/sdk | 2.12.0 | Apache-2.0 |
| @agentclientprotocol/sdk | 2.9.1 | Apache-2.0 |
| @anthropic-ai/claude-agent-sdk | 0.3.331 | Proprietary (Anthropic, all rights reserved) |
| @anthropic-ai/claude-agent-sdk-darwin-arm64 | 0.3.331 | Proprietary (Anthropic, all rights reserved) |
| @anthropic-ai/claude-agent-sdk-darwin-x64 | 0.3.331 | Proprietary (Anthropic, all rights reserved) |
| @anthropic-ai/claude-agent-sdk-linux-arm64 | 0.3.331 | Proprietary (Anthropic, all rights reserved) |
| @anthropic-ai/claude-agent-sdk-linux-arm64-musl | 0.3.331 | Proprietary (Anthropic, all rights reserved) |
| @anthropic-ai/claude-agent-sdk-linux-x64 | 0.3.331 | Proprietary (Anthropic, all rights reserved) |
| @anthropic-ai/claude-agent-sdk-linux-x64-musl | 0.3.331 | Proprietary (Anthropic, all rights reserved) |
| @anthropic-ai/claude-agent-sdk-win32-arm64 | 0.3.331 | Proprietary (Anthropic, all rights reserved) |
| @anthropic-ai/claude-agent-sdk-win32-x64 | 0.3.331 | Proprietary (Anthropic, all rights reserved) |
| @anthropic-ai/claude-code | 2.1.332 | Proprietary (Anthropic, all rights reserved) |
| @anthropic-ai/claude-code-darwin-arm64 | 2.1.332 | Proprietary (Anthropic, all rights reserved) |
| @anthropic-ai/claude-code-darwin-x64 | 2.1.332 | Proprietary (Anthropic, all rights reserved) |
| @anthropic-ai/claude-code-linux-arm64 | 2.1.332 | Proprietary (Anthropic, all rights reserved) |
| @anthropic-ai/claude-code-linux-arm64-musl | 2.1.332 | Proprietary (Anthropic, all rights reserved) |
| @anthropic-ai/claude-code-linux-x64 | 2.1.332 | Proprietary (Anthropic, all rights reserved) |
| @anthropic-ai/claude-code-linux-x64-musl | 2.1.332 | Proprietary (Anthropic, all rights reserved) |
| @anthropic-ai/claude-code-win32-arm64 | 2.1.332 | Proprietary (Anthropic, all rights reserved) |
| @anthropic-ai/claude-code-win32-x64 | 2.1.332 | Proprietary (Anthropic, all rights reserved) |
| @anthropic-ai/sdk | 1.14.0 | Apache-2.0 |
| @babel/runtime | 7.29.15 | MIT |
| @github/copilot | 1.0.116 | Proprietary (GitHub Copilot CLI License) |
| @github/copilot-darwin-arm64 | 1.0.116 | Proprietary (GitHub Copilot CLI License) |
| @github/copilot-darwin-x64 | 1.0.116 | Proprietary (GitHub Copilot CLI License) |
| @github/copilot-linux-arm64 | 1.0.116 | Proprietary (GitHub Copilot CLI License) |
| @github/copilot-linux-x64 | 1.0.116 | Proprietary (GitHub Copilot CLI License) |
| @github/copilot-linuxmusl-arm64 | 1.0.116 | Proprietary (GitHub Copilot CLI License) |
| @github/copilot-linuxmusl-x64 | 1.0.116 | Proprietary (GitHub Copilot CLI License) |
| @github/copilot-win32-arm64 | 1.0.116 | Proprietary (GitHub Copilot CLI License) |
| @github/copilot-win32-x64 | 1.0.116 | Proprietary (GitHub Copilot CLI License) |
| @github/keytar | 7.10.6 | MIT |
| @google/gemini-cli | 0.71.1 | Apache-2.0 |
| @hono/node-server | 2.1.11 | MIT |
| @lydell/node-pty | 1.1.0 | MIT |
| @lydell/node-pty-darwin-arm64 | 1.1.0 | MIT |
| @lydell/node-pty-darwin-x64 | 1.1.0 | MIT |
| @lydell/node-pty-linux-arm64 | 1.1.0 | MIT |
| @lydell/node-pty-linux-x64 | 1.1.0 | MIT |
| @lydell/node-pty-win32-arm64 | 1.1.0 | MIT |
| @lydell/node-pty-win32-x64 | 1.1.0 | MIT |
| @modelcontextprotocol/sdk | 1.32.2 | MIT |
| @openai/codex | 0.171.0 | Apache-2.0 |
| @openai/codex | 0.171.0-darwin-arm64 | Apache-2.0 |
| @openai/codex | 0.171.0-darwin-x64 | Apache-2.0 |
| @openai/codex | 0.171.0-linux-arm64 | Apache-2.0 |
| @openai/codex | 0.171.0-linux-x64 | Apache-2.0 |
| @openai/codex | 0.171.0-win32-arm64 | Apache-2.0 |
| @openai/codex | 0.171.0-win32-x64 | Apache-2.0 |
| @openai/codex | 0.172.0 | Apache-2.0 |
| @openai/codex | 0.172.0-darwin-arm64 | Apache-2.0 |
| @openai/codex | 0.172.0-darwin-x64 | Apache-2.0 |
| @openai/codex | 0.172.0-linux-arm64 | Apache-2.0 |
| @openai/codex | 0.172.0-linux-x64 | Apache-2.0 |
| @openai/codex | 0.172.0-win32-arm64 | Apache-2.0 |
| @openai/codex | 0.172.0-win32-x64 | Apache-2.0 |
| @opentelemetry/api | 1.10.0 | Apache-2.0 |
| @stablelib/base64 | 1.0.1 | MIT |
| accepts | 2.0.0 | MIT |
| ajv | 8.20.0 | MIT |
| ajv-formats | 3.0.1 | MIT |
| body-parser | 2.4.0 | MIT |
| bundle-name | 4.1.1 | MIT |
| bytes | 3.1.2 | MIT |
| call-bind-apply-helpers | 1.0.2 | MIT |
| call-bound | 1.0.4 | MIT |
| content-disposition | 2.0.1 | MIT |
| content-type | 1.0.5 | MIT |
| content-type | 2.1.0 | MIT |
| cookie | 0.7.2 | MIT |
| cookie-signature | 1.2.2 | MIT |
| cors | 2.8.6 | MIT |
| cross-spawn | 7.0.6 | MIT |
| debug | 4.4.3 | MIT |
| default-browser | 5.5.1 | MIT |
| default-browser-id | 5.0.1 | MIT |
| define-lazy-prop | 3.0.0 | MIT |
| depd | 2.0.0 | MIT |
| detect-libc | 2.1.2 | Apache-2.0 |
| diff | 9.0.0 | BSD-3-Clause |
| dunder-proto | 1.0.1 | MIT |
| ee-first | 1.1.1 | MIT |
| encodeurl | 2.0.3 | MIT |
| es-define-property | 1.0.1 | MIT |
| es-errors | 1.3.0 | MIT |
| es-object-atoms | 1.1.2 | MIT |
| escape-html | 1.0.3 | MIT |
| etag | 1.8.1 | MIT |
| eventsource | 3.0.7 | MIT |
| eventsource-parser | 3.1.1 | MIT |
| express | 5.3.0 | MIT |
| express-rate-limit | 8.7.5 | MIT |
| fast-deep-equal | 3.1.3 | MIT |
| fast-sha256 | 1.3.0 | Unlicense |
| fast-uri | 3.1.9 | BSD-3-Clause |
| finalhandler | 2.1.1 | MIT |
| forwarded | 0.2.0 | MIT |
| fresh | 2.0.0 | MIT |
| function-bind | 1.1.2 | MIT |
| get-intrinsic | 1.3.0 | MIT |
| get-proto | 1.0.1 | MIT |
| gopd | 1.2.0 | MIT |
| has-symbols | 1.1.0 | MIT |
| hasown | 2.0.4 | MIT |
| hono | 4.13.22 | MIT |
| http-errors | 2.0.1 | MIT |
| iconv-lite | 0.7.3 | MIT |
| inherits | 2.0.4 | ISC |
| ip-address | 10.7.6 | MIT |
| ipaddr.js | 1.9.1 | MIT |
| is-docker | 3.0.0 | MIT |
| is-in-ssh | 1.0.0 | MIT |
| is-inside-container | 1.0.0 | MIT |
| is-promise | 4.0.0 | MIT |
| is-wsl | 3.1.1 | MIT |
| isexe | 2.0.0 | ISC |
| jose | 6.2.18 | MIT |
| json-schema-to-ts | 3.1.1 | MIT |
| json-schema-traverse | 1.0.0 | MIT |
| json-schema-typed | 8.0.2 | BSD-2-Clause |
| math-intrinsics | 1.1.0 | MIT |
| media-typer | 1.1.1 | MIT |
| merge-descriptors | 2.0.0 | MIT |
| mime-db | 1.54.0 | MIT |
| mime-types | 3.0.2 | MIT |
| ms | 2.1.3 | MIT |
| nan | 2.30.0 | MIT |
| negotiator | 1.1.0 | MIT |
| node-addon-api | 8.9.2 | MIT |
| node-pty | 1.0.0 | MIT |
| object-assign | 4.1.1 | MIT |
| object-inspect | 1.14.0 | MIT |
| on-finished | 2.4.2 | MIT |
| once | 1.4.0 | ISC |
| open | 11.0.4 | MIT |
| parseurl | 1.3.3 | MIT |
| path-key | 3.1.1 | MIT |
| path-to-regexp | 8.4.2 | MIT |
| pkce-challenge | 5.0.2 | MIT |
| powershell-utils | 0.2.1 | MIT |
| proxy-addr | 2.0.8 | MIT |
| qs | 6.17.1 | BSD-3-Clause |
| range-parser | 1.3.0 | MIT |
| raw-body | 3.0.2 | MIT |
| require-from-string | 2.0.2 | MIT |
| router | 2.3.0 | MIT |
| run-applescript | 7.1.0 | MIT |
| safer-buffer | 2.1.2 | MIT |
| send | 1.2.1 | MIT |
| serve-static | 2.2.1 | MIT |
| setprototypeof | 1.2.0 | ISC |
| shebang-command | 2.0.0 | MIT |
| shebang-regex | 3.0.0 | MIT |
| side-channel | 1.1.1 | MIT |
| side-channel-list | 1.0.1 | MIT |
| side-channel-map | 1.0.1 | MIT |
| side-channel-weakmap | 1.0.2 | MIT |
| standardwebhooks | 1.3.0 | MIT |
| statuses | 2.0.2 | MIT |
| toidentifier | 1.0.1 | MIT |
| ts-algebra | 2.0.0 | MIT |
| type-is | 2.1.0 | MIT |
| unpipe | 1.0.0 | MIT |
| vary | 1.1.2 | MIT |
| vscode-jsonrpc | 9.0.3 | MIT |
| which | 2.0.2 | ISC |
| wrappy | 1.0.2 | ISC |
| wsl-utils | 1.0.1 | MIT |
| zod | 4.6.7 | MIT |
| zod-to-json-schema | 3.25.2 | ISC |
