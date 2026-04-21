import * as Form from "@radix-ui/react-form";
import { useQueryClient } from "@tanstack/react-query";
import { useContext, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import LangflowLogo from "@/assets/LangflowLogo.svg?react";
import { useGetKeycloakConfig } from "@/controllers/API/queries/keycloak/use-get-keycloak-config";
import { useLoginUser } from "@/controllers/API/queries/auth";
import { CustomLink } from "@/customization/components/custom-link";
import { useSanitizeRedirectUrl } from "@/hooks/use-sanitize-redirect-url";
import InputComponent from "../../components/core/parameterRenderComponent/components/inputComponent";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { CONTROL_LOGIN_STATE, IS_AUTO_LOGIN } from "../../constants/constants";
import { AuthContext } from "../../contexts/authContext";
import useAlertStore from "../../stores/alertStore";
import type { LoginType } from "../../types/api";
import type {
  inputHandlerEventType,
  loginInputStateType,
} from "../../types/components";

const SSO_ERROR_MESSAGES: Record<string, string> = {
  unauthorized: "프로젝트 접근 권한이 없습니다. 관리자에게 문의하세요.",
  no_employee_id: "사번 정보를 확인할 수 없습니다. 관리자에게 문의하세요.",
  hcp_unavailable:
    "권한 확인 서버에 연결할 수 없습니다. 잠시 후 다시 시도하세요.",
};

export default function LoginPage(): JSX.Element {
  const [inputState, setInputState] =
    useState<loginInputStateType>(CONTROL_LOGIN_STATE);

  const { password, username } = inputState;

  useSanitizeRedirectUrl();

  const [searchParams] = useSearchParams();
  const errorCode = searchParams.get("error");
  const employeeId = searchParams.get("employee");

  const { data: keycloakConfig } = useGetKeycloakConfig();
  const ssoEnabled = keycloakConfig?.enabled === true;

  const { t } = useTranslation();
  const { login, clearAuthSession } = useContext(AuthContext);
  const setErrorData = useAlertStore((state) => state.setErrorData);

  function handleInput({
    target: { name, value },
  }: inputHandlerEventType): void {
    setInputState((prev) => ({ ...prev, [name]: value }));
  }

  const { mutate } = useLoginUser();
  const queryClient = useQueryClient();

  function signIn() {
    const user: LoginType = {
      username: username.trim(),
      password: password.trim(),
    };

    mutate(user, {
      onSuccess: (data) => {
        clearAuthSession();
        login(data.access_token, "login", data.refresh_token);
        queryClient.clear();
      },
      onError: (error) => {
        setErrorData({
          title: t("errors.signin"),
          list: [error["response"]["data"]["detail"]],
        });
      },
    });
  }

  // ── SSO mode ──────────────────────────────────────────────────────────
  if (ssoEnabled) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center bg-muted">
        <div className="flex w-72 flex-col items-center justify-center gap-2">
          <LangflowLogo
            title="Langflow logo"
            className="mb-4 h-10 w-10 scale-[1.5]"
          />
          <span className="mb-6 text-2xl font-semibold text-primary">
            {t("auth.loginTitle")}
          </span>
          {errorCode && (
            <div className="mb-4 w-full rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700">
              <p>
                {SSO_ERROR_MESSAGES[errorCode] ?? `로그인 오류: ${errorCode}`}
              </p>
              {employeeId && (
                <p className="mt-1 text-xs text-red-500">
                  사번: {employeeId}
                </p>
              )}
            </div>
          )}
          <div className="w-full">
            <Button
              className="w-full"
              variant="default"
              type="button"
              ignoreTitleCase
              onClick={() => {
                window.location.href = "/api/v1/keycloak/login";
              }}
            >
              {keycloakConfig.button_text ?? "SK하이닉스 SSO 로그인"}
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // ── Standard id/pw mode ───────────────────────────────────────────────
  return (
    <Form.Root
      onSubmit={(event) => {
        if (password === "") {
          event.preventDefault();
          return;
        }
        signIn();
        const _data = Object.fromEntries(new FormData(event.currentTarget));
        event.preventDefault();
      }}
      className="h-screen w-full"
    >
      <div className="flex h-full w-full flex-col items-center justify-center bg-muted">
        <div className="flex w-72 flex-col items-center justify-center gap-2">
          <LangflowLogo
            title="Langflow logo"
            className="mb-4 h-10 w-10 scale-[1.5]"
          />
          <span className="mb-6 text-2xl font-semibold text-primary">
            {t("auth.loginTitle")}
          </span>
          <div className="mb-3 w-full">
            <Form.Field name="username">
              <Form.Label className="data-[invalid]:label-invalid">
                {t("auth.usernameLabel")}{" "}
                <span className="font-medium text-destructive">*</span>
              </Form.Label>

              <Form.Control asChild>
                <Input
                  type="username"
                  onChange={({ target: { value } }) => {
                    handleInput({ target: { name: "username", value } });
                  }}
                  value={username}
                  className="w-full"
                  required
                  placeholder={t("auth.usernamePlaceholder")}
                />
              </Form.Control>

              <Form.Message match="valueMissing" className="field-invalid">
                {t("auth.usernameRequired")}
              </Form.Message>
            </Form.Field>
          </div>
          <div className="mb-3 w-full">
            <Form.Field name="password">
              <Form.Label className="data-[invalid]:label-invalid">
                {t("auth.passwordLabel")}{" "}
                <span className="font-medium text-destructive">*</span>
              </Form.Label>

              <InputComponent
                onChange={(value) => {
                  handleInput({ target: { name: "password", value } });
                }}
                value={password}
                isForm
                password={true}
                required
                placeholder={t("auth.passwordPlaceholder")}
                className="w-full"
              />

              <Form.Message className="field-invalid" match="valueMissing">
                {t("auth.passwordRequired")}
              </Form.Message>
            </Form.Field>
          </div>
          <div className="w-full">
            <Form.Submit asChild>
              <Button className="mr-3 mt-6 w-full" type="submit">
                {t("auth.signInButton")}
              </Button>
            </Form.Submit>
          </div>
          <div className="w-full">
            <CustomLink to="/signup">
              <Button className="w-full" variant="outline" type="button">
                {t("auth.noAccount")}&nbsp;<b>{t("auth.signUpLink")}</b>
              </Button>
            </CustomLink>
          </div>
        </div>
      </div>
    </Form.Root>
  );
}
