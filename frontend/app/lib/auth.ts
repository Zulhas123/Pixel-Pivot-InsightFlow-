export type JwtPayload = {
  sub?: string;
  role?: string;
  exp?: number;
};

function base64UrlDecode(input: string): string {
  const base64 = input.replace(/-/g, "+").replace(/_/g, "/");
  const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
  if (typeof window === "undefined") return "";
  return decodeURIComponent(
    Array.prototype.map
      .call(atob(padded), (c: string) => `%${c.charCodeAt(0).toString(16).padStart(2, "0")}`)
      .join("")
  );
}

export function decodeJwtPayload(token: string): JwtPayload | null {
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  try {
    const json = base64UrlDecode(parts[1]);
    return JSON.parse(json) as JwtPayload;
  } catch {
    return null;
  }
}

