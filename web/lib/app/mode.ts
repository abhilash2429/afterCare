export function isDemoMode(): boolean {
  return process.env.NEXT_PUBLIC_USE_DEMO === "true";
}
