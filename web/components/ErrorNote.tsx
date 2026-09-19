"use client";

import { Button } from "@/components/Button";

export function ErrorNote({
  message,
  action,
  onRetry,
}: {
  message: string | null;
  action?: string;
  onRetry?: () => void;
}) {
  if (!message) return null;
  return (
    <div className="mb-6 rounded-3xl bg-danger-soft p-6 text-danger" role="alert">
      <p>{message}</p>
      {onRetry && action ? (
        <div className="mt-4">
          <Button variant="ghost" onClick={onRetry}>
            {action}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
