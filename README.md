<!-- markdownlint-disable MD030 -->

# Langflow-Hynix

> SK Hynix 사내 커스텀 Langflow. upstream [langflow-ai/langflow](https://github.com/langflow-ai/langflow) 기반.

---

## 브랜치 전략

| 브랜치 | 역할 | 비고 |
|--------|------|------|
| `main` | 최신 hynix 릴리즈 | hynix/v1.8.4 기반 |
| `hynix/v1.8.4` | v1.8.4 + 커스텀 | **현행** |
| `hynix/v1.8.4` | v1.8.4 + 커스텀 | v1.8.4-hynix-rc0 |
| `hynix/v1.8.0` | v1.8.0 + 커스텀 | 아카이브 |
| `legacy/v1.8.0-hynix` | 이전 main 백업 | 아카이브 |

## 커스텀 패치 목록

커스텀 커밋 확인: `git log v1.8.4..hynix/v1.8.4 --oneline`

### Keycloak SSO
- Keycloak SSO 플러그인 (`src/backend/langflow-keycloak-sso/`)
- PKCE + nonce 검증, end_session 로그아웃 보안 강화
- EXTERNAL_SERVER_URL (Docker/K8s 내부 → 브라우저 리다이렉트 분리)
- HCP API 기반 프로젝트 권한 검증
- per-employee 인스턴스 접근 제한 (ALLOWED_EMPLOYEE)
- JWT leeway 30초 (서버 간 시계 차이 허용)
- Keycloak 26.x aud 클레임 호환
- refresh/access token 쿠키 설정 (HTTP 환경 401 해결)

### Frontend
- 한글 IME 자모분리 이슈 수정
- SSO 버튼 텍스트 동적 설정
- Get Started 템플릿 커스터마이징 (반도체 공정 도우미, 사내 문서 검색, 데이터 분석 에이전트)
- Playground 사이드바 모드 복원 (풀스크린 자동전환 제거)
- 외부 API 번들 제거 (사이드바 + 검색 필터), 로컬/자체호스팅 번들만 유지
- Discord, X(Twitter) 아이콘/링크 제거
- SSO/non-SSO 로그인 페이지 통합 (SSO → SSO 버튼, non-SSO → id/pw 폼)
- Logout: SSO 시 Keycloak logout, non-SSO 시 표준 logout

### Docker / CI
- `docker/keycloak-sso.Dockerfile` — SSO 플러그인 포함 이미지
- `docker/keycloak-sso.docker-compose.yml` — Keycloak + Mock HCP 로컬 테스트
- GitHub Actions: 태그 push 시 Docker 이미지 자동 빌드 (Docker Hub + ghcr.io)

### Helm Chart
- per-employee Helm 배포 (`helm/langflow/`)
- NFS PV + initContainer 자동 생성
- SSL CA 인증서 마운트
- imagePullSecrets (Harbor 등 private registry)
- nginx ingress class annotation

## upstream 업그레이드 방법

```bash
# 1. main 동기화
git checkout main && git pull upstream main

# 2. 새 버전 기반 hynix 브랜치 생성
git checkout -b hynix/v1.9.0 v1.9.0

# 3. 최신 검증된 hynix 브랜치 머지
git merge hynix/v1.8.4

# 4. 충돌 해결 → 테스트 → 태그 → Docker 빌드
git tag v1.9.0-hynix-rc0
docker build -f docker/keycloak-sso.Dockerfile -t langflow-hynix:v1.9.0-hynix-rc0 .
```

## Docker Images

| 이미지 | 용도 | SSO |
|--------|------|-----|
| `dk02315/langflow-hynix:v1.8.4-hynix-rc0` | Backend (id/pw 로그인) | X |
| `dk02315/langflow-hynix:v1.8.4-hynix-sso-rc0` | Backend (Keycloak SSO) | O |
| `dk02315/langflow-hynix-frontend:v1.8.4-hynix-rc0` | Frontend (nginx, 공용) | 동적 |

태그 push 시 GitHub Actions가 3종 이미지를 자동 빌드합니다. 수동 빌드:

```bash
# SSO 포함
docker build -f docker/keycloak-sso.Dockerfile --build-arg INSTALL_SSO=true -t langflow-hynix:v1.8.4-hynix-sso-rc0 .

# SSO 없이
docker build -f docker/keycloak-sso.Dockerfile --build-arg INSTALL_SSO=false -t langflow-hynix:v1.8.4-hynix-rc0 .

# Frontend
docker build -f docker/frontend/build_and_push_frontend.Dockerfile -t langflow-hynix-frontend:v1.8.4-hynix-rc0 .
```

## Docker 실행

**A서비스 — Keycloak SSO (BE + FE 분리)**

```bash
# Backend (API only)
docker run -d -p 7860:7860 \
  -e KEYCLOAK_ENABLED=true \
  -e KEYCLOAK_SERVER_URL=https://keycloak.company.com \
  -e KEYCLOAK_REALM=company \
  -e KEYCLOAK_CLIENT_ID=langflow \
  -e KEYCLOAK_CLIENT_SECRET=<secret> \
  -e KEYCLOAK_REDIRECT_URI=http://localhost:3000/api/v1/keycloak/callback \
  -e LANGFLOW_AUTO_LOGIN=false \
  -e LANGFLOW_SECRET_KEY=<random-32-chars> \
  dk02315/langflow-hynix:v1.8.4-hynix-sso-rc0 langflow run --backend-only

# Frontend (nginx → Backend proxy)
docker run -d -p 3000:3000 \
  -e BACKEND_URL=http://<backend-host>:7860 \
  -e FRONTEND_PORT=3000 \
  dk02315/langflow-hynix-frontend:v1.8.4-hynix-rc0
```

**B서비스 — id/pw 로그인 (올인원)**

```bash
docker run -p 7860:7860 \
  -e LANGFLOW_AUTO_LOGIN=false \
  -e LANGFLOW_SECRET_KEY=<random-32-chars> \
  dk02315/langflow-hynix:v1.8.4-hynix-rc0
```

**SSO 로컬 테스트 (Keycloak + Mock HCP)**

```bash
docker compose -f docker/keycloak-sso.docker-compose.yml up -d
```

## Helm 배포

```bash
helm install langflow-<사번> helm/langflow/ \
  --set empno=<사번> \
  --set backend.image.ssoTag=v1.8.4-hynix-sso-rc0 \
  --set keycloak.serverUrl=https://keycloak.company.com \
  --set keycloak.realm=company \
  --set keycloak.clientId=langflow \
  --set keycloak.clientSecret=<secret>
```

---

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./docs/static/img/langflow-logo-color-blue-bg.svg">
  <img src="./docs/static/img/langflow-logo-color-black-solid.svg" alt="Langflow logo">
</picture>

[![Release Notes](https://img.shields.io/github/release/langflow-ai/langflow?style=flat-square)](https://github.com/langflow-ai/langflow/releases)
[![PyPI - License](https://img.shields.io/badge/license-MIT-orange)](https://opensource.org/licenses/MIT)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/langflow?style=flat-square)](https://pypistats.org/packages/langflow)
[![Twitter](https://img.shields.io/twitter/url/https/twitter.com/langflow-ai.svg?style=social&label=Follow%20%40Langflow)](https://twitter.com/langflow_ai)
[![YouTube Channel](https://img.shields.io/youtube/channel/subscribers/UCn2bInQrjdDYKEEmbpwblLQ?label=Subscribe)](https://www.youtube.com/@Langflow)
[![Discord Server](https://img.shields.io/discord/1116803230643527710?logo=discord&style=social&label=Join)](https://discord.gg/EqksyE2EX9)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/langflow-ai/langflow)

[Langflow](https://langflow.org) is a powerful platform for building and deploying AI-powered agents and workflows. It provides developers with both a visual authoring experience and built-in API and MCP servers that turn every workflow into a tool that can be integrated into applications built on any framework or stack. Langflow comes with batteries included and supports all major LLMs, vector databases and a growing library of AI tools.

## ✨ Highlight features

- **Visual builder interface** to quickly get started and iterate.
- **Source code access** lets you customize any component using Python.
- **Interactive playground** to immediately test and refine your flows with step-by-step control.
- **Multi-agent orchestration** with conversation management and retrieval.
- **Deploy as an API** or export as JSON for Python apps.
- **Deploy as an MCP server** and turn your flows into tools for MCP clients.
- **Observability** with LangSmith, LangFuse and other integrations.
- **Enterprise-ready** security and scalability.

## 🖥️  Langflow Desktop

Langflow Desktop is the easiest way to get started with Langflow. All dependencies are included, so you don't need to manage Python environments or install packages manually.
Available for Windows and macOS.

[📥 Download Langflow Desktop](https://www.langflow.org/desktop)

## ⚡️ Quickstart

### Install locally (recommended)

Requires Python 3.10–3.13 and [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended package manager).

#### Install

From a fresh directory, run:
```shell
uv pip install langflow -U
```

The latest Langflow package is installed.
For more information, see [Install and run the Langflow OSS Python package](https://docs.langflow.org/get-started-installation#install-and-run-the-langflow-oss-python-package).

#### Run

To start Langflow, run:
```shell
uv run langflow run
```

Langflow starts at http://127.0.0.1:7860.

That's it! You're ready to build with Langflow! 🎉

## 📦 Other install options

### Run from source
If you've cloned this repository and want to contribute, run this command from the repository root:
```shell
make run_cli
```
For more information, see [DEVELOPMENT.md](./DEVELOPMENT.md).

### Docker
Start a Langflow container with default settings:
```shell
docker run -p 7860:7860 langflowai/langflow:latest
```
Langflow is available at http://localhost:7860/.
For configuration options, see the [Docker deployment guide](https://docs.langflow.org/deployment-docker).

> [!CAUTION]
> - Users must update to Langflow >= 1.7.1 to protect against [CVE-2025-68477](https://github.com/langflow-ai/langflow/security/advisories/GHSA-5993-7p27-66g5) and [CVE-2025-68478](https://github.com/langflow-ai/langflow/security/advisories/GHSA-f43r-cc68-gpx4).
> - Langflow version 1.7.0 has a critical bug where persisted state (flows, projects, and global variables) cannot be found when upgrading. Version 1.7.0 was yanked and replaced with version 1.7.1, which includes a fix for this bug. **DO NOT** upgrade to version 1.7.0. Instead, upgrade directly to version 1.7.1.
> - Langflow versions 1.6.0 through 1.6.3 have a critical bug where `.env` files are not read, potentially causing security vulnerabilities. **DO NOT** upgrade to these versions if you use `.env` files for configuration. Instead, upgrade to 1.6.4, which includes a fix for this bug.
> - Windows users of Langflow Desktop should **not** use the in-app update feature to upgrade to Langflow version 1.6.0. For upgrade instructions, see [Windows Desktop update issue](https://docs.langflow.org/release-notes#windows-desktop-update-issue).
> - Users must update to Langflow >= 1.3 to protect against [CVE-2025-3248](https://nvd.nist.gov/vuln/detail/CVE-2025-3248)
> - Users must update to Langflow >= 1.5.1 to protect against [CVE-2025-57760](https://github.com/langflow-ai/langflow/security/advisories/GHSA-4gv9-mp8m-592r)
>
> For security information, see our [Security Policy](./SECURITY.md) and [Security Advisories](https://github.com/langflow-ai/langflow/security/advisories).

## 🚀 Deployment

Langflow is completely open source and you can deploy it to all major deployment clouds. To learn how to deploy Langflow, see our [Langflow deployment guides](https://docs.langflow.org/deployment-overview).

## ⭐ Stay up-to-date

Star Langflow on GitHub to be instantly notified of new releases.

![Star Langflow](https://github.com/user-attachments/assets/03168b17-a11d-4b2a-b0f7-c1cce69e5a2c)

## 👋 Contribute

We welcome contributions from developers of all levels. If you'd like to contribute, please check our [contributing guidelines](./CONTRIBUTING.md) and help make Langflow more accessible.

---

[![Star History Chart](https://api.star-history.com/svg?repos=langflow-ai/langflow&type=Timeline)](https://star-history.com/#langflow-ai/langflow&Date)

## ❤️ Contributors

[![langflow contributors](https://contrib.rocks/image?repo=langflow-ai/langflow)](https://github.com/langflow-ai/langflow/graphs/contributors)
