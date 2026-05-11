"""DRM detection and decryption utilities for KnowledgeBase ingestion.

Supports detection and decryption of DRM-protected files:
- PDF, DOC, DOCX, PPT, PPTX, XLS, XLSX

Configuration via environment variables:
- LANGFLOW_DRM_ENABLED: "true" to enable DRM handling
- LANGFLOW_DRM_CHECK_URL: (optional) endpoint to verify user permission
- LANGFLOW_DRM_DECRYPT_URL: endpoint to decrypt DRM-protected files
- LANGFLOW_DRM_GW_ROOT_KEY: gateway root key header value
"""

from __future__ import annotations

import os
from io import BytesIO
from typing import TYPE_CHECKING

import requests

from lfx.log.logger import logger

if TYPE_CHECKING:
    pass

# File extensions that may have DRM protection
DRM_TARGET_EXTENSIONS = frozenset({
    ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
})

# OLE Compound File magic bytes (encrypted Office files)
OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def is_drm_enabled() -> bool:
    """Check if DRM handling is enabled via environment variable."""
    return os.environ.get("LANGFLOW_DRM_ENABLED", "false").lower() == "true"


def is_drm_target_file(file_name: str) -> bool:
    """Check if the file extension is a DRM target."""
    lower_name = file_name.lower()
    return any(lower_name.endswith(ext) for ext in DRM_TARGET_EXTENSIONS)


def detect_drm(file_name: str, file_content: bytes) -> bool:
    """Detect if a file has DRM/encryption applied.

    Detection methods:
    - PDF: pypdf PdfReader.is_encrypted
    - Office (DOC/XLS/PPT): OLE compound file magic bytes indicate encrypted format
    - Office XML (DOCX/XLSX/PPTX): Try to open as ZIP, if it fails → likely encrypted

    Returns:
        True if DRM/encryption is detected, False otherwise.
    """
    lower_name = file_name.lower()

    if lower_name.endswith(".pdf"):
        return _detect_pdf_drm(file_content)
    if lower_name.endswith((".doc", ".xls", ".ppt")):
        return _detect_ole_drm(file_content)
    if lower_name.endswith((".docx", ".xlsx", ".pptx")):
        return _detect_ooxml_drm(file_content)
    return False


def _detect_pdf_drm(file_content: bytes) -> bool:
    """Detect PDF encryption using pypdf."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(file_content))
        return reader.is_encrypted
    except Exception:  # noqa: BLE001
        # If we can't even parse it, might be encrypted or corrupted
        return True


def _detect_ole_drm(file_content: bytes) -> bool:
    """Detect OLE compound file encryption (legacy .doc/.xls/.ppt).

    Encrypted Office files use OLE compound format with EncryptedPackage stream.
    """
    # OLE files start with magic bytes
    if file_content[:8] == OLE_MAGIC:
        # This is an OLE file. Legacy Office formats are always OLE,
        # but encrypted OOXML files are also wrapped in OLE.
        # Check for EncryptedPackage stream indicator
        return b"EncryptedPackage" in file_content[:4096]
    return False


def _detect_ooxml_drm(file_content: bytes) -> bool:
    """Detect OOXML encryption (.docx/.xlsx/.pptx).

    OOXML files are ZIP archives. If we can't open as ZIP, it's likely
    encrypted (wrapped in OLE compound format).
    """
    import zipfile

    # If it starts with OLE magic, it's an encrypted OOXML file
    if file_content[:8] == OLE_MAGIC:
        return True

    # If it's not a valid ZIP, it might be encrypted
    try:
        with zipfile.ZipFile(BytesIO(file_content)) as zf:
            # Valid ZIP = not encrypted
            zf.namelist()
            return False
    except (zipfile.BadZipFile, Exception):  # noqa: BLE001
        return True


def check_drm_permission(employee_id: str) -> bool:
    """Check if the user has permission to decrypt DRM files.

    Calls the DRM check API with the employee ID.
    If LANGFLOW_DRM_CHECK_URL is not configured, returns True (skip check).

    Returns:
        True if permitted, False otherwise.
    """
    check_url = os.environ.get("LANGFLOW_DRM_CHECK_URL")
    if not check_url:
        # No check URL configured — skip permission check
        return True

    gw_root_key = os.environ.get("LANGFLOW_DRM_GW_ROOT_KEY", "")

    try:
        headers = {}
        if gw_root_key:
            headers["gw-root-key"] = gw_root_key

        response = requests.post(
            check_url,
            json={"employee_id": employee_id},
            headers=headers,
            timeout=10,
            verify=False,  # noqa: S501 — air-gapped environment
        )

        if response.status_code == 200:
            data = response.json()
            # Accept various response formats
            return data.get("permitted", data.get("has_permission", data.get("result", False)))

        logger.warning("DRM check API returned status %s for employee %s", response.status_code, employee_id)
        return False

    except Exception as e:  # noqa: BLE001
        logger.error("DRM check API call failed: %s", e)
        return False


def decrypt_drm_file(file_name: str, file_content: bytes, employee_id: str | None = None) -> bytes:
    """Decrypt a DRM-protected file via the DRM decrypt API.

    Sends the file as multipart/form-data to the decrypt endpoint.
    Employee number is included as a query parameter (empNo) for audit/logging.

    Returns:
        Decrypted file bytes.

    Raises:
        ValueError: If decryption fails or API is not configured.
    """
    decrypt_url = os.environ.get("LANGFLOW_DRM_DECRYPT_URL")
    if not decrypt_url:
        msg = "DRM decrypt URL is not configured (LANGFLOW_DRM_DECRYPT_URL). Cannot decrypt DRM-protected files."
        raise ValueError(msg)

    gw_root_key = os.environ.get("LANGFLOW_DRM_GW_ROOT_KEY", "")

    headers = {}
    if gw_root_key:
        headers["gw-root-key"] = gw_root_key

    # Add employee number as query parameter for audit
    params = {}
    if employee_id:
        params["empNo"] = employee_id

    try:
        response = requests.post(
            decrypt_url,
            files={"file": (file_name, BytesIO(file_content))},
            headers=headers,
            params=params,
            timeout=60,
            verify=False,  # noqa: S501 — air-gapped environment
        )

        if response.status_code == 200:
            decrypted = response.content
            if not decrypted:
                msg = f"DRM decrypt API returned empty response for '{file_name}'"
                raise ValueError(msg)
            logger.info("DRM decryption successful: %s (%d → %d bytes)", file_name, len(file_content), len(decrypted))
            return decrypted

        msg = (
            f"DRM decrypt API failed for '{file_name}' "
            f"(status={response.status_code}): {response.text[:200]}"
        )
        raise ValueError(msg)

    except requests.RequestException as e:
        msg = f"DRM decrypt API request failed for '{file_name}': {e}"
        raise ValueError(msg) from e


def process_drm_file(file_name: str, file_content: bytes, employee_id: str | None = None) -> bytes:
    """Full DRM processing pipeline: detect → check permission → decrypt.

    Args:
        file_name: Name of the file
        file_content: Raw file bytes
        employee_id: Employee ID from Keycloak SSO (for permission check)

    Returns:
        Decrypted file bytes if DRM was detected and decrypted,
        or original file_content if no DRM detected.

    Raises:
        PermissionError: If user doesn't have DRM decrypt permission.
        ValueError: If decryption fails.
    """
    if not is_drm_enabled():
        return file_content

    if not is_drm_target_file(file_name):
        return file_content

    if not detect_drm(file_name, file_content):
        logger.debug("No DRM detected for '%s', proceeding normally", file_name)
        return file_content

    logger.info("DRM detected for '%s', attempting decryption", file_name)

    # Permission check (if configured)
    if employee_id:
        if not check_drm_permission(employee_id):
            msg = f"DRM decryption not permitted for employee '{employee_id}'. Contact your administrator."
            raise PermissionError(msg)
    else:
        logger.warning("No employee_id provided for DRM check on '%s', skipping permission check", file_name)

    # Decrypt
    return decrypt_drm_file(file_name, file_content, employee_id=employee_id)
