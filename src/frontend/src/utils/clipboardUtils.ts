/**
 * Copy text to clipboard with fallback for non-HTTPS environments.
 *
 * navigator.clipboard.writeText() requires a secure context (HTTPS or localhost).
 * In HTTP deployments (e.g., air-gapped/internal environments), this falls back
 * to the legacy document.execCommand("copy") approach.
 */
export async function copyToClipboard(text: string): Promise<void> {
  // Try modern Clipboard API first (requires HTTPS or localhost)
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }

  // Fallback: create a temporary textarea and use execCommand
  const textArea = document.createElement("textarea");
  textArea.value = text;

  // Avoid scrolling to bottom
  textArea.style.position = "fixed";
  textArea.style.left = "-9999px";
  textArea.style.top = "-9999px";
  textArea.style.opacity = "0";

  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();

  try {
    const success = document.execCommand("copy");
    if (!success) {
      throw new Error("execCommand copy failed");
    }
  } finally {
    document.body.removeChild(textArea);
  }
}
