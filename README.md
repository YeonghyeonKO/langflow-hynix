<!-- markdownlint-disable MD030 -->

# Langflow-Hynix

> SK Hynix 사내 커스텀 Langflow. upstream [langflow-ai/langflow](https://github.com/langflow-ai/langflow) 기반.

---

## 브랜치 전략

| 브랜치 | 역할 | 비고 |
|--------|------|------|
| `hynix/v1.9.4` | v1.9.4 + 커스텀 | **운영 (SSO RC)** |
| `hynix/v1.9.1` | v1.9.1 + 커스텀 | 아카이브 |
| `hynix/v1.9.0` | v1.9.0 + 커스텀 | 아카이브 |
| `hynix/v1.8.4` | v1.8.4 + 커스텀 | 아카이브 |
| `hynix/v1.8.3` | v1.8.3 + 커스텀 | 아카이브 |
| `hynix/v1.8.0` | v1.8.0 + 커스텀 | 아카이브 |
| `main` | upstream 미러 | GitHub Sync Fork 가능 |

## 커스텀 패치 목록

커스텀 커밋 확인: `git log upstream/release-1.9.x..hynix/v1.9.4 --oneline`

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
- 브라우저 탭/PWA 타이틀 'Langflow' → 'AI Agent Builder' (`index.html`, `manifest.json`, Playground 동적 title)
- 한글 IME 자모분리 이슈 수정
- 한국어 로케일 (ko.json) 추가 + loadLanguage fallback
- SSO 버튼 텍스트 동적 설정
- Playground 사이드바 모드 복원 (풀스크린 자동전환 제거)
- 외부 API 번들 제거 (사이드바 + 검색 필터), 로컬/자체호스팅 번들만 유지
- Discord, X(Twitter), GitHub 아이콘/링크 제거
- SSO/non-SSO 로그인 페이지 통합 (SSO → SSO 버튼, non-SSO → id/pw 폼)
- Logout: SSO 시 Keycloak logout, non-SSO 시 표준 logout
- 로그인 페이지: "Sign in to Langflow" → "AI Agent Builder"
- Welcome 페이지: "Welcome to SK hynix AI Agent Builder" + Agent Hub / Agent Builder Channel 링크
- 상단바: Agent Hub 링크 (`LANGFLOW_AGENT_HUB_URL` 환경변수)
- Settings: MCP Servers / MCP Client 메뉴 제거
- HTTP 환경에서 Copy 버튼 동작하지 않는 문제 수정 (`document.execCommand` fallback)
- 채팅 히스토리 페이지네이션: 스크롤 업 시 이전 메시지 로드 (offset 기반 무한 스크롤)
- 메시지 조회 limit 기본값 20 + Playground 열려있을 때만 조회 (캔버스 속도 저하 방지)

### Model Providers
- vLLM을 기본 Model Provider로 추가 (Settings → Model Providers)
- vLLM 서버 /v1/models API 동적 모델 조회
- vLLM Embeddings 지원 (EMBEDDING_PROVIDER_CLASS_MAPPING)
- Language Model 드롭다운에서 vLLM Embeddings 모델 제외
- "Available Models" 통합 표시 (LLM/Embedding 구분 없이)
- API Key: Global Variables / Model Provider vars / 환경변수 모두 지원
- Language Model / Agent 컴포넌트에서 vLLM provider 선택 시 `base_url` 자동 해석 (component > DB > 환경변수)
- provider 전환 시 stale API key 방지 (vLLM 전용 키 우선 사용)
- provider 변수 개별 저장 시 validation race condition 수정
- vLLM Embedding: API Base URL을 API key로 잘못 전송하던 문제 수정 ([#33](https://github.com/YeonghyeonKO/langflow-hynix/issues/33), commit `79252328ad`)
- vLLM Embedding: 최초 저장 시 인증 실패("Authentication failed") 후 재시도해야 연결되던 문제 수정 — 저장 시점 validation race, 키 미저장 시 probe skip ([#34](https://github.com/YeonghyeonKO/langflow-hynix/issues/34), commit `84bab8df3b`)
- air-gapped 환경 지원: tiktoken 비활성화, API key dummy fallback
- 친절한 에러 메시지 (연결 실패, 인증 오류, 타임아웃 구분)

### KnowledgeBase
- DRM 감지/해제 기능 (`LANGFLOW_DRM_ENABLED`, `LANGFLOW_DRM_DECRYPT_URL`)
  - 대상: PDF, DOC, DOCX, PPT, PPTX, XLS, XLSX
  - Keycloak SSO employee_id로 권한 확인 + `empNo` 쿼리 파라미터 전달
- 파일 파싱 포맷 추가: PPTX, XLSX, XLS, PPT, DOC (python-pptx, openpyxl, xlrd)
- DOCX/PPTX 테이블 콘텐츠 추출
- XLSX OOM 방지 (10,000행 제한)
- 업로드 허용 파일: md, json, txt, pdf, doc, docx, ppt, pptx, xls, xlsx, csv (최대 20MB)

### URLComponent / SSL
- URLComponent에 Verify SSL 옵션 추가 (`LANGFLOW_URL_VERIFY_SSL=false`)
- Langflow Assistant에서도 환경변수 기반 SSL 비활성화 적용
- SSL 비활성화 시 async → sync 전환 (aiohttp 우회)

### Docker / CI
- `docker/keycloak-sso.Dockerfile` — SSO 플러그인 포함 이미지
- `docker/keycloak-sso.docker-compose.yml` — Keycloak + Mock HCP 로컬 테스트
- GitHub Actions: 태그 push 시 Docker 이미지 자동 빌드 (Docker Hub + ghcr.io)
- Docker npm ci ECONNRESET 재시도 로직 (최대 3회, 네트워크 불안정 환경 대응)
- pymilvus[model] → pymilvus (ML extra 제거로 빌드 시간 단축)

### Helm Chart
- per-employee Helm 배포 (`helm/langflow/`)
- NFS PV + initContainer 자동 생성
- SSL CA 인증서 마운트
- imagePullSecrets (Harbor 등 private registry)
- nginx ingress class annotation

## upstream 업그레이드 방법

```bash
# 1. upstream fetch
git fetch upstream --tags

# 2. 새 버전 기반 hynix 브랜치 생성
git checkout -b hynix/v1.10.0 upstream/release-1.10.0

# 3. 최신 검증된 hynix 브랜치 머지
git merge hynix/v1.9.4

# 4. 충돌 해결 → 테스트 → 태그 → Docker 빌드
git tag v1.10.0-hynix-rc0
docker build -f docker/keycloak-sso.Dockerfile -t langflow-hynix:v1.10.0-hynix-rc0 .
```

## Docker Images

| 이미지 | 용도 |
|--------|------|
| `dk02315/langflow-hynix:v1.9.4-hynix-sso-rc0` | Backend (Keycloak SSO) — **최신** |

태그 push 시 GitHub Actions가 Docker 이미지를 자동 빌드합니다.

```bash
docker pull dk02315/langflow-hynix:v1.9.4-hynix-sso-rc0
```

## Docker 실행

```bash
docker run -d -p 7860:7860 \
  -e KEYCLOAK_ENABLED=true \
  -e KEYCLOAK_SERVER_URL=https://keycloak.company.com \
  -e KEYCLOAK_REALM=company \
  -e KEYCLOAK_CLIENT_ID=langflow \
  -e KEYCLOAK_CLIENT_SECRET=<secret> \
  -e KEYCLOAK_REDIRECT_URI=http://localhost:7860/api/v1/keycloak/callback \
  -e LANGFLOW_AUTO_LOGIN=false \
  -e LANGFLOW_SECRET_KEY=<random-32-chars> \
  -e LANGFLOW_AGENT_HUB_URL=https://agent-hub.company.com \
  -e LANGFLOW_AGENT_BUILDER_CHANNEL=https://channel.company.com \
  -e LANGFLOW_URL_VERIFY_SSL=false \
  -e LANGFLOW_DRM_ENABLED=true \
  -e LANGFLOW_DRM_DECRYPT_URL=http://drm-api.company.com/DRM/decrypt/file \
  -e LANGFLOW_DRM_GW_ROOT_KEY=<gw-root-key> \
  dk02315/langflow-hynix:v1.9.4-hynix-sso-rc0
```

**SSO 로컬 테스트 (Keycloak + Mock HCP)**

```bash
docker compose -f docker/keycloak-sso.docker-compose.yml up -d
```

## 환경변수 요약

| 환경변수 | 설명 | 필수 |
|----------|------|------|
| `LANGFLOW_SECRET_KEY` | 암호화 키 (고정값 권장) | O |
| `LANGFLOW_AGENT_HUB_URL` | Agent Hub 링크 (상단바 + Welcome 페이지) | X |
| `LANGFLOW_AGENT_BUILDER_CHANNEL` | Agent Builder Channel 링크 (Welcome 페이지) | X |
| `LANGFLOW_URL_VERIFY_SSL` | `false` 시 URLComponent SSL 검증 비활성화 | X |
| `LANGFLOW_DRM_ENABLED` | `true` 시 DRM 감지/해제 활성화 | X |
| `LANGFLOW_DRM_CHECK_URL` | DRM 권한 확인 API (없으면 스킵) | X |
| `LANGFLOW_DRM_DECRYPT_URL` | DRM 해제 API | DRM 사용 시 O |
| `LANGFLOW_DRM_GW_ROOT_KEY` | DRM API gateway root key 헤더 | X |

## Helm 배포

```bash
helm install langflow-<사번> helm/langflow/ \
  --set empno=<사번> \
  --set backend.image.ssoTag=v1.9.4-hynix-sso-rc0 \
  --set keycloak.serverUrl=https://keycloak.company.com \
  --set keycloak.realm=company \
  --set keycloak.clientId=langflow \
  --set keycloak.clientSecret=<secret>
```

## 플로우 백업 · 복구 (WSL + curl)

인스턴스 초기화 전에 **본인이 만든 플로우를 직접 내려받아 보관**하는 방법입니다.
사내망(VPN) 연결 상태에서 WSL 터미널을 열고 아래 순서대로 따라 하시면 됩니다.
명령어는 복사해서 붙여넣기만 하면 되고, 값을 바꿔야 하는 곳은 모두 표시해 두었습니다.

### 0. 준비물

```bash
sudo apt update && sudo apt install -y curl jq
```

`jq`는 JSON을 다루는 도구입니다. 이미 설치되어 있다면 그냥 넘어가셔도 됩니다.

**API Key 발급**: 브라우저에서 본인 인스턴스 접속 → 우측 상단 **Settings** → **Langflow API Keys** → **Add New**
→ 생성된 키는 **이때 한 번만 표시**되므로 반드시 즉시 복사해 두세요.

### 1. 환경변수 설정

`<사번>`과 `<발급받은키>` 두 곳만 본인 값으로 바꿔 주세요.

```bash
export EMPNO=<사번>
export LF_URL="http://agentbuilder-${EMPNO}.abs01.skhynix.com"
export LF_API_KEY="<발급받은키>"
export LF_BACKUP_DIR="$HOME/langflow-backup"
mkdir -p "$LF_BACKUP_DIR"
```

> 터미널을 새로 열면 위 설정이 사라집니다. 창을 닫았다면 이 단계부터 다시 실행해 주세요.

### 2. 연결 확인 (30초)

백업을 시작하기 전에 주소와 키가 올바른지 먼저 확인합니다.

```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" \
  -H "x-api-key: ${LF_API_KEY}" \
  "${LF_URL}/api/v1/users/whoami"
```

- `HTTP 200` → 정상입니다. 다음 단계로 진행하세요.
- `HTTP 401` / `HTTP 403` → API Key가 잘못되었거나 만료되었습니다. 다시 발급받아 주세요.
- 아무것도 출력되지 않거나 `Could not resolve host` → VPN/사내망 연결을 확인해 주세요.

### 3. 전체 백업 (핵심 단계)

```bash
curl -s --compressed \
  -H "x-api-key: ${LF_API_KEY}" \
  "${LF_URL}/api/v1/flows/?get_all=true&remove_example_flows=true" \
  | jq '{flows: .}' \
  > "${LF_BACKUP_DIR}/flows-${EMPNO}-$(date +%Y%m%d).json"
```

> **`--compressed` 옵션을 절대 빼지 마세요.**
> 서버가 응답을 항상 gzip으로 압축해서 보내기 때문에, 이 옵션이 없으면 읽을 수 없는
> 깨진 바이너리 파일이 저장됩니다. 이 문제로 백업에 실패하는 경우가 가장 많습니다.

`jq '{flows: .}'`로 감싸는 이유는, 이 형태 그대로 복구 API에 바로 넣을 수 있기 때문입니다.

### 4. 백업 검증 (반드시 확인)

파일이 생겼다고 끝이 아닙니다. **플로우 개수와 이름을 눈으로 확인**해 주세요.

```bash
# 백업된 플로우 개수
jq '.flows | length' "${LF_BACKUP_DIR}"/flows-${EMPNO}-*.json

# 백업된 플로우 이름 목록
jq -r '.flows[].name' "${LF_BACKUP_DIR}"/flows-${EMPNO}-*.json
```

화면에서 보이던 플로우가 모두 나오는지 확인하세요.
개수가 `0`이거나 빠진 플로우가 있다면 [문제 해결](#문제-해결) 표를 참고해 주세요.

### 5. 플로우별 파일로 나누기 (선택)

전체 파일 하나로도 충분하지만, 플로우를 하나씩 골라서 복구하고 싶다면 아래를 실행하세요.

```bash
cd "${LF_BACKUP_DIR}"
jq -c '.flows[]' flows-${EMPNO}-*.json | while read -r flow; do
  name=$(printf '%s' "$flow" | jq -r '.name' | tr -c '[:alnum:]._-' '_')
  printf '%s' "$flow" > "${name}.json"
  echo "저장 완료: ${name}.json"
done
```

이렇게 만든 개별 파일은 Langflow 화면에 **드래그 앤 드롭**으로 바로 올릴 수 있습니다.

### 6. Windows 쪽으로 파일 꺼내기

WSL 안에만 두면 나중에 찾기 어렵습니다. 탐색기로 열어서 안전한 곳에 복사해 두세요.

```bash
explorer.exe "$(wslpath -w "$LF_BACKUP_DIR")"
```

탐색기 창이 열리면 파일을 바탕화면이나 개인 드라이브로 복사하시면 됩니다.

### 7. 복구 방법

초기화 후 새 인스턴스에서 API Key를 다시 발급받고, 1단계 환경변수를 다시 설정한 뒤 실행하세요.
`<파일명>`은 실제 백업 파일 이름으로 바꿔 주세요.

```bash
curl -s -X POST \
  -H "x-api-key: ${LF_API_KEY}" \
  -F "file=@${LF_BACKUP_DIR}/<파일명>.json" \
  "${LF_URL}/api/v1/flows/upload/" \
  | jq -r '.[].name'
```

복구된 플로우 이름이 출력되면 성공입니다.
같은 ID의 플로우가 이미 있으면 덮어쓰기(upsert)되므로 중복 걱정 없이 여러 번 실행해도 됩니다.

터미널이 익숙하지 않다면, Langflow 화면에서 **Projects → 우측 상단 업로드 버튼**으로
백업 JSON 파일을 올리셔도 결과는 같습니다.

### 백업에 포함되지 않는 항목

플로우 JSON에는 **설계 내용만** 담깁니다. 아래 항목은 별도로 메모해 두셔야 합니다.

| 항목 | 이유 |
|------|------|
| Global Variables, 각종 API Key 등 자격증명 | `LANGFLOW_SECRET_KEY`로 암호화되어 저장되며 플로우 JSON에 포함되지 않음 |
| File 컴포넌트로 업로드한 파일 | 별도 스토리지에 저장됨 |
| Playground 채팅 히스토리 | 대화 기록은 백업 대상이 아님 |
| MCP 서버 설정 | 인스턴스 설정에 저장됨 |

> 복구 후 플로우를 열면 키 입력란이 비어 있을 수 있습니다. 이는 정상이며,
> 값을 다시 입력하시면 그대로 동작합니다. **초기화 전에 필요한 키 값을 미리 확보해 두세요.**

### 문제 해결

| 증상 | 원인 | 해결 방법 |
|------|------|-----------|
| 저장된 파일이 깨진 글자로 보임 | `--compressed` 누락 | 3단계 명령에 `--compressed`를 넣고 다시 실행 |
| `HTTP 401` / `HTTP 403` | API Key 오타 또는 만료 | Settings에서 키를 새로 발급받아 1단계부터 다시 |
| `jq: command not found` | jq 미설치 | `sudo apt install -y jq` |
| `Could not resolve host` | 사내망/VPN 미연결 | VPN 연결 후 재시도 |
| 플로우 개수가 `0` | 예제 플로우만 있는 상태에서 `remove_example_flows=true` 적용 | 해당 파라미터를 빼고 다시 실행 |
| `$'\r': command not found` | Windows 줄바꿈(CRLF)이 섞임 | 메모장 대신 WSL 터미널에 직접 붙여넣기, 또는 `dos2unix <파일>` |
| `Permission denied` | 백업 폴더 권한 문제 | `mkdir -p "$LF_BACKUP_DIR"`를 다시 실행 |

문제가 계속되면 위 명령의 출력 화면을 그대로 캡처해서 Agent Builder Channel로 문의해 주세요.

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

## 🛡️ Security

For security information, see our [Security Policy](./SECURITY.md).

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
