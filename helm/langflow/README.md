# Langflow Helm Chart

사원별 Langflow 인스턴스를 Kubernetes에 배포하기 위한 Helm chart입니다.

## 사전 요구사항

- Kubernetes 1.24+
- Helm 3.x
- Keycloak 서버 (SSO 사용 시)
- NFS 서버 또는 동적 프로비저닝 StorageClass
- Wildcard DNS: `*.<domain>` → Ingress controller

## 배포 모드

| 모드 | `separateFrontend` | `keycloak.enabled` | 설명 |
|------|-------------------|--------------------|------|
| SSO + BE/FE 분리 | `true` | `true` | Backend API + Frontend nginx 별도 Pod |
| SSO + 올인원 | `false` | `true` | Backend가 FE도 서빙 (단일 Pod) |
| id/pw + BE/FE 분리 | `true` | `false` | SSO 없이 BE/FE 분리 |
| id/pw + 올인원 | `false` | `false` | 가장 단순한 배포 |

## 빠른 시작

### 1. 시크릿 생성 (운영 권장)

```bash
kubectl create namespace langflow-2074795

kubectl create secret generic langflow-keycloak \
  --namespace langflow-2074795 \
  --from-literal=client-secret=YOUR_KEYCLOAK_SECRET \
  --from-literal=langflow-secret-key=YOUR_LANGFLOW_KEY
```

### 2. Harbor 레지스트리 인증 (private registry 사용 시)

```bash
kubectl create secret docker-registry harbor-cred \
  --namespace langflow-2074795 \
  --docker-server=harbor-aipp01.skhynix.com \
  --docker-username=YOUR_USERNAME \
  --docker-password=YOUR_PASSWORD
```

또는 `imageRegistry`로 자동 생성:

```yaml
imageRegistry:
  enabled: true
  server: harbor-aipp01.skhynix.com
  username: YOUR_USERNAME
  password: YOUR_PASSWORD
```

### 3. values 파일 작성

```yaml
# my-values.yaml
instanceName: "2074795"
separateFrontend: true

backend:
  image:
    repository: dk02315/langflow-hynix
    tag: v1.9.0-hynix-rc28
    ssoTag: v1.9.0-hynix-sso-rc28

frontend:
  image:
    repository: dk02315/langflow-hynix-frontend
    tag: v1.9.0-hynix-rc28

keycloak:
  enabled: true
  serverUrl: https://keycloak.skhynix.com
  realm: company
  clientId: langflow
  existingSecret: langflow-keycloak

ssl:
  enabled: true
  caCert: |
    -----BEGIN CERTIFICATE-----
    ...
    -----END CERTIFICATE-----

nfs:
  enabled: true
  server: 10.0.0.1
  basePath: /nfs/data
  mountOptions:
    - nfsvers=3
  initImage: harbor-aipp01.skhynix.com/busybox/busybox:latest

langflow:
  storageClass: sc-nfs-app-retain

imagePullSecrets:
  - name: harbor-cred
```

### 4. 배포

```bash
helm install langflow ./helm/langflow \
  --namespace langflow-2074795 \
  --create-namespace \
  -f my-values.yaml
```

접속: `http://langflow-2074795.aipp02.skhynix.com`

### 5. 업그레이드

```bash
helm upgrade langflow ./helm/langflow \
  --namespace langflow-2074795 \
  -f my-values.yaml
```

### 6. 삭제

```bash
helm uninstall langflow -n langflow-2074795
kubectl delete namespace langflow-2074795
```

## 전체 설정 (values.yaml)

### 기본

| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| `instanceName` | 인스턴스 이름 (필수, 리소스 이름/호스트명에 사용) | `""` |
| `separateFrontend` | BE/FE 분리 배포 여부 | `true` |

### Backend

| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| `backend.image.repository` | Backend Docker 이미지 | `dk02315/langflow-hynix` |
| `backend.image.tag` | non-SSO 이미지 태그 | `v1.9.0-hynix-rc2` |
| `backend.image.ssoTag` | SSO 이미지 태그 (keycloak.enabled=true 시 자동 사용) | `v1.9.0-hynix-sso-rc2` |
| `backend.image.pullPolicy` | 이미지 pull 정책 | `IfNotPresent` |
| `backend.resources` | CPU/메모리 리소스 | requests: 500m/1Gi, limits: 2/4Gi |
| `backend.extraEnv` | 추가 환경변수 | `[]` |
| `backend.readinessProbe.initialDelaySeconds` | Readiness 초기 지연 | `30` |
| `backend.readinessProbe.periodSeconds` | Readiness 체크 주기 | `15` |
| `backend.readinessProbe.timeoutSeconds` | Readiness 타임아웃 | `5` |
| `backend.livenessProbe.initialDelaySeconds` | Liveness 초기 지연 | `60` |
| `backend.livenessProbe.periodSeconds` | Liveness 체크 주기 | `30` |
| `backend.livenessProbe.timeoutSeconds` | Liveness 타임아웃 | `10` |

### Frontend

| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| `frontend.image.repository` | Frontend Docker 이미지 | `dk02315/langflow-hynix-frontend` |
| `frontend.image.tag` | 이미지 태그 | `v1.9.0-hynix-rc2` |
| `frontend.image.pullPolicy` | 이미지 pull 정책 | `IfNotPresent` |
| `frontend.port` | Frontend 포트 | `8080` |
| `frontend.resources` | CPU/메모리 리소스 | requests: 100m/128Mi, limits: 500m/256Mi |

### Ingress

| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| `ingress.enabled` | Ingress 생성 여부 | `true` |
| `ingress.domain` | 기본 도메인 | `aipp02.skhynix.com` |
| `ingress.annotations` | 추가 어노테이션 | `kubernetes.io/ingress.class: nginx` |

호스트명: `langflow-<instanceName>.<domain>`

### Keycloak SSO

| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| `keycloak.enabled` | SSO 활성화 여부 | `false` |
| `keycloak.serverUrl` | Keycloak 서버 URL | `""` |
| `keycloak.realm` | Realm | `""` |
| `keycloak.clientId` | Client ID | `""` |
| `keycloak.clientSecret` | Client secret (`existingSecret` 설정 시 무시) | `""` |
| `keycloak.existingSecret` | 기존 K8s Secret 이름 | `""` |
| `keycloak.existingSecretKeys.clientSecret` | Secret 내 client-secret 키 | `client-secret` |
| `keycloak.existingSecretKeys.langflowSecretKey` | Secret 내 langflow-secret-key 키 | `langflow-secret-key` |
| `keycloak.employeeClaim` | 사원번호 추출 토큰 클레임 | `preferred_username` |
| `keycloak.buttonText` | 로그인 버튼 텍스트 | `SK하이닉스 SSO 로그인` |
| `keycloak.sharedUsername` | 공유 프로젝트 계정 | `""` |
| `keycloak.allowedEmployee` | 특정 사원만 접근 허용 (쉼표 구분) | `""` |
| `keycloak.hcpApiUrl` | HCP API URL (프로젝트 권한 검증) | `""` |

### Langflow

| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| `langflow.secretKey` | 암호화 키 (`existingSecret` 설정 시 무시) | `""` |
| `langflow.autoLogin` | 자동 로그인 | `"false"` |
| `langflow.storage` | PVC 크기 | `5Gi` |
| `langflow.storageClass` | StorageClass 이름 | `""` |
| `langflow.databaseUrl` | 외부 DB URL (빈값 → SQLite) | `""` |
| `langflow.store` | Langflow Store API 활성화 | `"false"` |
| `langflow.terminationGracePeriodSeconds` | Pod 종료 대기 시간 | `60` |
| `langflow.refreshSecure` | refresh token 쿠키 Secure 플래그 | `"false"` |
| `langflow.refreshSameSite` | refresh token 쿠키 SameSite 속성 | `"lax"` |
| `langflow.accessSecure` | access token 쿠키 Secure 플래그 | `"false"` |
| `langflow.accessSameSite` | access token 쿠키 SameSite 속성 | `"lax"` |

> HTTP 환경: `*Secure: "false"`, `*SameSite: "lax"`
> HTTPS 환경: `*Secure: "true"`, `*SameSite: "none"`

> Air-gapped 환경에서는 `langflow.store: "false"` (기본값)로 외부 API 호출을 차단합니다.

### NFS 직접 마운트 (flow 데이터 & 커스텀 컴포넌트)

| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| `nfsVolumes.flow.enabled` | Flow 데이터 NFS 마운트 | `false` |
| `nfsVolumes.flow.server` | NFS 서버 주소 | `""` |
| `nfsVolumes.flow.path` | NFS 경로 | `"/langflow/prd/flow"` |
| `nfsVolumes.flow.mountPath` | 컨테이너 내 마운트 경로 | `/app/flow` |
| `nfsVolumes.flow.storage` | PV/PVC 용량 | `5Gi` |
| `nfsVolumes.flow.mountOptions` | NFS 마운트 옵션 | `[]` |
| `nfsVolumes.component.enabled` | 커스텀 컴포넌트 NFS 마운트 | `false` |
| `nfsVolumes.component.server` | NFS 서버 주소 | `""` |
| `nfsVolumes.component.path` | NFS 경로 | `"/langflow/prd/component"` |
| `nfsVolumes.component.mountPath` | 컨테이너 내 마운트 경로 | `/app/custom_components` |
| `nfsVolumes.component.storage` | PV/PVC 용량 | `5Gi` |
| `nfsVolumes.component.mountOptions` | NFS 마운트 옵션 | `[]` |

> **NFS v3 환경**: `mountOptions`에 `nolock`을 반드시 추가하세요. NFS v3의 NLM(Network Lock Manager)이 SQLite 파일 잠금과 충돌하여 I/O 지연 및 DB 손상을 유발할 수 있습니다.

사용 예시 (NFS v3 + nolock):

```yaml
nfsVolumes:
  flow:
    enabled: true
    server: "nas.company.com"
    path: "/langflow/prd/flow"
    mountPath: /app/flow
    storage: 5Gi
    mountOptions:
      - nfsvers=3
      - nolock
  component:
    enabled: true
    server: "nas.company.com"
    path: "/langflow/prd/component"
    mountPath: /app/custom_components
    storage: 5Gi
    mountOptions:
      - nfsvers=3
      - nolock

backend:
  extraEnv:
    - name: LANGFLOW_COMPONENTS_PATH
      value: /app/custom_components
```

### NFS PersistentVolume (SQLite 데이터)

| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| `nfs.enabled` | NFS PV 자동 생성 | `false` |
| `nfs.server` | NFS 서버 IP | `""` |
| `nfs.basePath` | NFS 기본 경로 | `""` |
| `nfs.mountOptions` | NFS 마운트 옵션 (v3: `[nfsvers=3, nolock]`) | `[]` |
| `nfs.initImage` | 디렉토리 생성용 initContainer 이미지 | `busybox:1.36` |

`nfs.enabled=true`이면:
- PV가 `basePath`를 마운트
- initContainer가 `langflow-<instanceName>` 하위 디렉토리를 자동 생성
- 메인 컨테이너는 `subPath: langflow-<instanceName>`로 해당 디렉토리만 사용

> `basePath`는 NFS 서버에 이미 존재해야 합니다. 하위 디렉토리는 자동 생성됩니다.

> SQLite 손상 방지: Deployment strategy가 `Recreate`로 설정되어 있어 업그레이드 시 기존 Pod가 완전히 종료된 후 새 Pod가 시작됩니다. `terminationGracePeriodSeconds`(기본 60초)로 graceful shutdown 시간을 확보합니다.

### SSL 인증서

| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| `ssl.enabled` | CA 인증서 마운트 | `false` |
| `ssl.caCert` | PEM 내용 직접 입력 | `""` |
| `ssl.existingConfigMap` | 기존 ConfigMap 사용 | `""` |
| `ssl.existingSecret` | 기존 Secret 사용 | `""` |
| `ssl.key` | ConfigMap/Secret 내 키 이름 | `ca.crt` |

### Private Registry

| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| `imageRegistry.enabled` | imagePullSecret 자동 생성 | `false` |
| `imageRegistry.server` | 레지스트리 서버 | `""` |
| `imageRegistry.username` | 사용자명 | `""` |
| `imageRegistry.password` | 비밀번호 | `""` |
| `imagePullSecrets` | 기존 imagePullSecret 목록 (imageRegistry와 택 1) | `[]` |

## 여러 사원 일괄 배포

공통 values 파일 하나로 여러 사원을 배포할 수 있습니다:

```bash
for EMPNO in 2074795 2073215 2071234; do
  helm install langflow-${EMPNO} ./helm/langflow \
    --namespace langflow-${EMPNO} \
    --create-namespace \
    -f values-common.yaml \
    --set instanceName=${EMPNO}
done
```

## Air-gapped 환경 배포 참고

Air-gapped(네트워크 차단) 환경에서 배포 시:

1. **Langflow Store 비활성화**: `langflow.store: "false"` (기본값) — 외부 API 호출 차단
2. **SSL 인증서**: `ssl.enabled: true` + `ssl.caCert` — 사내 PKI CA 인증서 마운트
3. **tiktoken 캐시**: Docker 이미지에 `cl100k_base.tiktoken`이 번들되어 있어 오프라인에서도 Knowledge Base 임베딩이 동작합니다
4. **Private Registry**: `imageRegistry` 또는 `imagePullSecrets`로 사내 레지스트리 인증
