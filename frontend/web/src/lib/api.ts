export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public requestId: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
export function errorDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((item) => {
        const value = item as { loc?: unknown[]; msg?: string };
        return `${value.loc?.slice(1).join(".") || "Input"}: ${value.msg || "Invalid value"}`;
      })
      .join("; ");
  return "The request could not be completed. Please try again.";
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, options);
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError")
      throw error;
    throw new ApiError(
      "Cannot reach the backend. Check that the API is running.",
      0,
    );
  }
  const payload = await response.json().catch(() => null);
  if (!response.ok)
    throw new ApiError(
      errorDetail(payload?.detail),
      response.status,
      response.headers.get("X-Request-ID"),
    );
  if (payload === null)
    throw new ApiError(
      "The backend returned an unreadable response.",
      response.status,
    );
  return payload as T;
}
export const jsonBody = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});
export function multipart(
  values: Record<string, string | boolean | File | null | undefined>,
): FormData {
  const form = new FormData();
  for (const [key, value] of Object.entries(values)) {
    if (value !== null && value !== undefined && value !== "")
      form.append(key, value instanceof File ? value : String(value));
  }
  return form;
}
export function validateFile(
  file: File,
  maxBytes: number,
  kind: "resume" | "audio",
) {
  if (file.size > maxBytes)
    throw new Error(
      `Choose a ${kind} smaller than ${maxBytes / 1024 / 1024} MiB.`,
    );
  if (kind === "resume" && !file.name.toLowerCase().endsWith(".pdf"))
    throw new Error("Choose a PDF resume.");
}
export function parseQuestions(text: string) {
  return text
    .split(/\r?\n/)
    .map((line) => line.replace(/^\s*(?:\d+[.)]|[-*])\s*/, "").trim())
    .filter(Boolean);
}
