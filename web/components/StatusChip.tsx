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
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-[18px] font-semibold ${tones[tone]}`}
    >
      <span aria-hidden="true">{icon}</span>
      {label}
    </span>
  );
}
