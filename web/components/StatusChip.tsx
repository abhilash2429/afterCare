type Tone = "ok" | "warn" | "danger" | "neutral";

const tones: Record<Tone, string> = {
  ok: "bg-ok-soft text-ok",
  warn: "bg-warn-soft text-warn",
  danger: "bg-danger-soft text-danger",
  neutral: "bg-white text-primary border border-primary/15",
};

export function StatusChip({
  icon,
  label,
  tone = "neutral",
}: {
  icon: string;
  label: string;
  tone?: Tone;
}) {
  return (
    <span
      className={`status-chip inline-flex max-w-full items-center gap-2 rounded-full px-3 py-1.5 text-[16px] font-semibold leading-tight ${tones[tone]}`}
    >
      <span aria-hidden="true">{icon}</span>
      {label}
    </span>
  );
}
