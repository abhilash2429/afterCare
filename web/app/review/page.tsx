"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Bilingual } from "@/components/Bilingual";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { ErrorNote } from "@/components/ErrorNote";
import { PageHeader } from "@/components/PageHeader";
import { SourceCrop } from "@/components/SourceCrop";
import { StatusChip } from "@/components/StatusChip";
import { ILLUSTRATIONS, ScenePhoto } from "@/components/marketing/illustrations";
import { emptyUserMedicine, useApp } from "@/lib/app/store";
import { useAppView } from "@/lib/app/view";
import { bi, COPY } from "@/lib/copy";
import { brandLabel, foodKey, medicineMolecules } from "@/lib/format";
import type { Medicine, Slot } from "@/lib/api/types";

const SLOTS: Slot[] = ["morning", "noon", "night", "bedtime"];

export default function ReviewPage() {
  const router = useRouter();
  const { isApp } = useAppView();
  const { ready, plan, pages, confirmMedicine, saveMedicines, activate, error, role, uiLang } = useApp();
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState<Medicine | null>(null);
  const [busy, setBusy] = useState(false);

  if (!ready) return <p>{bi("loading", uiLang)}</p>;
  if (!plan) {
    return (
      <EmptyState
        title="noPlanReview"
        body="photographFirst"
        action="goToUpload"
        href="/upload/"
        illustration={<ScenePhoto src={ILLUSTRATIONS.review} />}
      />
    );
  }

  const unresolved = plan.medicines.filter((medicine) => medicine.needsConfirmation);
  const canActivate = unresolved.length === 0 && role !== "caregiver";

  async function onActivate() {
    if (!canActivate) return;
    setBusy(true);
    const ok = await activate();
    setBusy(false);
    if (ok) router.push("/schedule/");
  }

  async function onConfirm(lineId: string) {
    setBusy(true);
    await confirmMedicine(lineId);
    setBusy(false);
  }

  async function onSaveEdit(medicine: Medicine, userEdited: boolean) {
    if (!plan) return;
    setBusy(true);
    const medicines = plan.medicines.map((item) => (item.lineId === medicine.lineId ? medicine : item));
    await saveMedicines(medicines, userEdited);
    setDraft(null);
    setBusy(false);
  }

  async function onAdd() {
    if (!plan || !draft) return;
    if (draft.frequency && draft.slots.length === 0 && !draft.prn) return;
    setBusy(true);
    await saveMedicines([...plan.medicines, { ...draft, source: "user", sourceBlockIds: [] }], true);
    setDraft(null);
    setAdding(false);
    setBusy(false);
  }

  return (
    <section>
      <PageHeader
        eyebrow="reviewEyebrow"
        title="reviewTitle"
        description="reviewDesc"
        actions={
          <Button onClick={onActivate} disabled={!canActivate || busy}>
            <Bilingual k="activate" lang={uiLang} />
          </Button>
        }
      />
      <ErrorNote message={error} />
      {isApp ? null : (
        <div className="page-scene mb-8">
          <ScenePhoto src={ILLUSTRATIONS.review} />
        </div>
      )}

      {unresolved.length > 0 ? (
        <p className="mb-6 rounded-2xl bg-warn-soft px-4 py-3 text-warn">
          {unresolved.length} · {bi("confirmAmber", uiLang)}
        </p>
      ) : null}

      {plan.followUp?.date || plan.followUp?.with ? (
        <article className="mb-6 rounded-3xl bg-card p-6">
          <h2 className="font-semibold">
            <Bilingual k="followUp" lang={uiLang} />
          </h2>
          <p className="mt-1">
            {plan.followUp.with ?? COPY.notWritten[uiLang]}
            {plan.followUp.date ? ` · ${plan.followUp.date}` : ""}
          </p>
        </article>
      ) : null}

      <ul className={`grid gap-5 ${isApp ? "" : "md:grid-cols-2"}`}>
        {plan.medicines.map((medicine) => {
          const editing = draft?.lineId === medicine.lineId;
          return (
            <li key={medicine.lineId}>
              <article className={`app-panel h-full rounded-3xl p-6 ${medicine.needsConfirmation ? "bg-warn-soft" : "bg-card"}`}>
                <div className="flex flex-col items-start gap-2">
                  <h2 className={isApp ? "font-display text-[22px] leading-snug" : "font-display text-[28px]"}>{brandLabel(medicine.brand)}</h2>
                  {medicine.needsConfirmation ? (
                    <StatusChip icon="!" label={bi("checkThis", uiLang)} tone="warn" />
                  ) : (
                    <StatusChip icon="✓" label={bi("checked", uiLang)} tone="ok" />
                  )}
                  {medicine.prn ? <StatusChip icon="SOS" label={bi("onlyWhenNeeded", uiLang)} /> : null}
                </div>
                <SourceCrop crop={medicine.crop} pages={pages} />
                <p className="mt-2 capitalize">{medicineMolecules(medicine)}</p>
                {editing && draft ? (
                  <EditFields medicine={draft} onChange={setDraft} />
                ) : (
                  <dl className="mt-4 grid grid-cols-2 gap-3">
                    <div>
                      <dt className="muted font-semibold">
                        <Bilingual k="frequency" lang={uiLang} />
                      </dt>
                      <dd>{medicine.frequency ?? bi("notWritten", uiLang)}</dd>
                    </div>
                    <div>
                      <dt className="muted font-semibold">
                        <Bilingual k="food" lang={uiLang} />
                      </dt>
                      <dd>
                        <Bilingual k={foodKey(medicine.foodRelation)} lang={uiLang} />
                      </dd>
                    </div>
                    <div>
                      <dt className="muted font-semibold">
                        <Bilingual k="duration" lang={uiLang} />
                      </dt>
                      <dd>
                        {medicine.durationDays === null
                          ? bi("durationUnknown", uiLang)
                          : `${medicine.durationDays} ${COPY.days[uiLang]}`}
                      </dd>
                    </div>
                    <div>
                      <dt className="muted font-semibold">
                        <Bilingual k="slots" lang={uiLang} />
                      </dt>
                      <dd>
                        {medicine.prn
                          ? bi("onlyWhenNeeded", uiLang)
                          : medicine.slots.length > 0
                            ? medicine.slots.map((slot) => bi(slot, uiLang)).join(", ")
                            : bi("notWritten", uiLang)}
                      </dd>
                    </div>
                  </dl>
                )}
                <p className="mt-4 rounded-2xl bg-white px-3 py-2 text-primary/80">{medicine.rawText}</p>
                {role !== "caregiver" ? (
                  <div className={isApp ? "app-actions mt-5" : "mt-5 flex flex-wrap gap-3"}>
                    {medicine.needsConfirmation ? (
                      <Button onClick={() => onConfirm(medicine.lineId)} disabled={busy}>
                        <Bilingual k="iChecked" lang={uiLang} />
                      </Button>
                    ) : null}
                    {editing && draft ? (
                      <Button
                        onClick={() => onSaveEdit({ ...draft, needsConfirmation: false }, true)}
                        disabled={busy}
                      >
                        <Bilingual k="saveEdit" lang={uiLang} />
                      </Button>
                    ) : (
                      <Button variant="ghost" onClick={() => setDraft(medicine)}>
                        <Bilingual k="edit" lang={uiLang} />
                      </Button>
                    )}
                  </div>
                ) : null}
              </article>
            </li>
          );
        })}
      </ul>

      {role !== "caregiver" ? (
        <div className="mt-8">
          {adding && draft ? (
            <article className="rounded-3xl bg-card p-6">
              <h2 className="font-semibold">
                <Bilingual k="addLine" lang={uiLang} />
              </h2>
              <EditFields medicine={draft} onChange={setDraft} includeBrand />
              <div className={isApp ? "app-actions mt-5" : "mt-5 flex flex-wrap gap-3"}>
                <Button onClick={onAdd} disabled={busy}>
                  <Bilingual k="addThisLine" lang={uiLang} />
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => {
                    setAdding(false);
                    setDraft(null);
                  }}
                >
                  <Bilingual k="cancel" lang={uiLang} />
                </Button>
              </div>
            </article>
          ) : (
            <Button
              variant="ghost"
              onClick={() => {
                setAdding(true);
                setDraft(emptyUserMedicine());
              }}
            >
              <Bilingual k="addMedicine" lang={uiLang} />
            </Button>
          )}
        </div>
      ) : null}
    </section>
  );
}

function EditFields({
  medicine,
  onChange,
  includeBrand = false,
}: {
  medicine: Medicine;
  onChange: (medicine: Medicine) => void;
  includeBrand?: boolean;
}) {
  const { uiLang } = useApp();
  const strength = medicine.molecules[0]?.strengthMg ?? "";
  return (
    <div className="mt-4 grid gap-4">
      {includeBrand ? (
        <label>
          <span className="field-label">
            <Bilingual k="brand" lang={uiLang} />
          </span>
          <input
            className="field-input"
            value={medicine.brand ?? ""}
            onChange={(event) => onChange({ ...medicine, brand: event.target.value || null })}
          />
        </label>
      ) : null}
      <label>
        <span className="field-label">
          <Bilingual k="frequency" lang={uiLang} />
        </span>
        <input
          className="field-input"
          value={medicine.frequency ?? ""}
          onChange={(event) => onChange({ ...medicine, frequency: event.target.value || null })}
        />
      </label>
      {medicine.molecules[0] ? (
        <label>
          <span className="field-label">
            <Bilingual k="strengthMg" lang={uiLang} />
          </span>
          <input
            className="field-input"
            inputMode="decimal"
            value={strength}
            onChange={(event) => {
              const value = event.target.value;
              const next = [...medicine.molecules];
              next[0] = { ...next[0], strengthMg: value === "" ? null : Number(value) };
              onChange({ ...medicine, molecules: next });
            }}
          />
        </label>
      ) : null}
      <label>
        <span className="field-label">
          <Bilingual k="durationDays" lang={uiLang} />
        </span>
        <input
          className="field-input"
          inputMode="numeric"
          value={medicine.durationDays ?? ""}
          onChange={(event) =>
            onChange({
              ...medicine,
              durationDays: event.target.value === "" ? null : Number(event.target.value),
            })
          }
        />
      </label>
      <div>
        <p className="field-label">
          <Bilingual k="slots" lang={uiLang} />
        </p>
        <div className="slot-dots">
          {SLOTS.map((slot) => {
            const on = medicine.slots.includes(slot);
            return (
              <button
                key={slot}
                type="button"
                className={`slot-dot${on ? " is-on" : ""}`}
                onClick={() =>
                  onChange({
                    ...medicine,
                    slots: on ? medicine.slots.filter((item) => item !== slot) : [...medicine.slots, slot],
                  })
                }
              >
                <span className={`take-skip-dot ${on ? "is-take" : "is-skip"}`} />
                {bi(slot, uiLang)}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
