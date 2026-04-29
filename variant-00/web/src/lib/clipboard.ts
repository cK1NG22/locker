import { COPY_FEEDBACK_MS } from "./constants";

export async function copyToClipboard(
  text: string,
  setCopied: (v: boolean) => void,
  duration = COPY_FEEDBACK_MS,
): Promise<void> {
  await navigator.clipboard.writeText(text);
  setCopied(true);
  setTimeout(() => setCopied(false), duration);
}
