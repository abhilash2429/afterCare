export function PlateMark({ relation }: { relation: "before" | "after" | "unspecified" }) {
  if (relation === "unspecified") {
    return <span aria-hidden="true">–</span>;
  }
  return (
    <span className="plate-mark" aria-hidden="true">
      <svg viewBox="0 0 32 32" width="22" height="22">
        <circle cx="16" cy="16" r="12" fill="none" stroke="currentColor" strokeWidth="2" />
        <circle cx="16" cy="16" r="5" fill={relation === "after" ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" />
      </svg>
    </span>
  );
}
