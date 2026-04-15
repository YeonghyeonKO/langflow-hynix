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
    tag: v1.9.0-hynix-rc0
    ssoTag: v1.9.0-hynix-sso-rc0

frontend:
  image:
    repository: dk02315/langflow-hynix-frontend
    tag: v1.9.0-hynix-rc0

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

### Backend 이미지

| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| `backend.image.repository` | Backend Docker 이미지 | `dk02315/langflow-hynix` |
| `backend.image.tag` | non-SSO 이미지 태그 | `v1.9.0-hynix-rc0` |
| `backend.image.ssoTag` | SSO 이미지 태그 (keycloak.enabled=true 시 자동 사용) | `v1.9.0-hynix-sso-rc0` |
| `backend.image.pullPolicy` | 이미지 pull 정책 | `IfNotPresent` |
| `backend.resources` | CPU/메모리 리소스 | requests: 500m/1Gi, limits: 2/4Gi |
| `backend.extraEnv` | 추가 환경변수 | `[]` |

### Frontend 이미지

| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| `frontend.image.repository` | Frontend Docker 이미지 | `dk02315/langflow-hynix-frontend` |
| `frontend.image.tag` | 이미지 태그 | `v1.9.0-hynix-rc0` |
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
| `keycloak.allowedEmployee` | 특정 사원만 접근 허용 | `""` |
| `keycloak.hcpApiUrl` | HCP API URL (프로젝트 권한 검증) | `""` |

### Langflow

| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| `langflow.secretKey` | 암호화 키 (`existingSecret` 설정 시 무시) | `""` |
| `langflow.autoLogin` | 자동 로그인 | `"false"` |
| `langflow.storage` | PVC 크기 | `5Gi` |
| `langflow.storageClass` | StorageClass 이름 | `""` |
| `langflow.databaseUrl` | 외부 DB URL (빈값 → SQLite) | `""` |
| `langflow.refreshSecure` | refresh token 쿠키 Secure 플래그 | `"false"` |
| `langflow.refreshSameSite` | refresh token 쿠키 SameSite 속성 | `"lax"` |
| `langflow.accessSecure` | access token 쿠키 Secure 플래그 | `"false"` |
| `langflow.accessSameSite` | access token 쿠키 SameSite 속성 | `"lax"` |

> HTTP 환경: `*Secure: "false"`, `*SameSite: "lax"`
> HTTPS 환경: `*Secure: "true"`, `*SameSite: "none"`

### NFS 스토리지

| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| `nfs.enabled` | NFS PV 자동 생성 | `false` |
| `nfs.server` | NFS 서버 IP | `""` |
| `nfs.basePath` | NFS 기본 경로 | `""` |
| `nfs.mountOptions` | NFS 마운트 옵션 | `[]` |
| `nfs.initImage` | 디렉토리 생성용 initContainer 이미지 | `busybox:1.36` |

`nfs.enabled=true`이면:
- PV가 `basePath`를 마운트
- initContainer가 `langflow-<instanceName>` 하위 디렉토리를 자동 생성
- 메인 컨테이너는 `subPath: langflow-<instanceName>`로 해당 디렉토리만 사용

> `basePath`는 NFS 서버에 이미 존재해야 합니다. 하위 디렉토리는 자동 생성됩니다.

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
