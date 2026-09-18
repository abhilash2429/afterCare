import type { ReactNode } from "react";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-10 flex flex-wrap items-end justify-between gap-6">
      <div className="max-w-2xl">
        <p className="landing-eyebrow" style={{ marginBottom: 12 }}>
          {eyebrow}
        </p>
        <h1 className="font-display text-[44px] leading-[1.1] tracking-[-0.03em] text-primary">{title}</h1>
        {description ? <p className="mt-3 text-primary/75">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
    </div>
  );
}
