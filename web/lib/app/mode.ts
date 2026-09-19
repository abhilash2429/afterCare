export function isDemoMode(): boolean {
  if (process.env.NEXT_PUBLIC_USE_DEMO === "true") return true;
  return !process.env.NEXT_PUBLIC_API_BASE;
}
