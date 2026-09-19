"use client";

import { useRef } from "react";
import { useRouter } from "next/navigation";
import { Bilingual } from "@/components/Bilingual";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { ErrorNote } from "@/components/ErrorNote";
import { PageHeader } from "@/components/PageHeader";
import { ILLUSTRATIONS, ScenePhoto } from "@/components/marketing/illustrations";
import { bi } from "@/lib/copy";
import { useApp } from "@/lib/app/store";
import { useAppView } from "@/lib/app/view";

export default function UploadPage() {
  const router = useRouter();
  const cameraRef = useRef<HTMLInputElement>(null);
  const galleryRef = useRef<HTMLInputElement>(null);
  const { isApp } = useAppView();
  const {
    ready,
    circleId,
    pages,
    addPages,
    removePage,
    extracting,
    extractStep,
    startExtract,
    error,
    setError,
    role,
    uiLang,
  } = useApp();

  if (!ready) return <p>{bi("loading", uiLang)}</p>;
  if (!circleId) {
    return (
      <EmptyState
        title="noCircleTitle"
        body="noCircleUploadBody"
        action="setUp"
        href="/setup/"
        illustration={<ScenePhoto src={ILLUSTRATIONS.upload} />}
      />
    );
  }
  if (role === "caregiver") {
    return (
      <EmptyState
        title="ownersUpload"
        body="ownersUploadBody"
        action="openSchedule"
        href="/schedule/"
        illustration={<ScenePhoto src={ILLUSTRATIONS.upload} />}
      />
    );
  }

  async function extract() {
    const ok = await startExtract();
    if (ok) router.push("/review/");
  }

  if (extracting) {
    return (
      <section className="flex min-h-[60vh] flex-col items-center justify-center text-center">
        <div className="page-scene page-scene-center">
          <ScenePhoto src={ILLUSTRATIONS.review} />
        </div>
        <h1 className={`font-display text-primary ${isApp ? "text-[26px] leading-snug" : "text-[40px]"}`}>{bi("readingPrescription", uiLang)}</h1>
        <p className="mt-3 text-primary/80">{extractStep}</p>
        <p className="muted mt-8">{bi("canTake2min", uiLang)}</p>
      </section>
    );
  }

  return (
    <section>
      <PageHeader eyebrow="dischargeSummary" title="photographPaper" description="uploadDesc" />
      <ErrorNote message={error} />

      <div className={isApp ? "flex flex-col gap-4" : "grid gap-8 lg:grid-cols-[1.1fr_0.9fr]"}>
        <button
          type="button"
          onClick={() => galleryRef.current?.click()}
          className={
            isApp
              ? "app-dropzone"
              : "flex min-h-[320px] flex-col items-center justify-center rounded-[32px] border-2 border-dashed border-secondary/35 bg-transparent px-8 py-12 text-center"
          }
        >
          <div className="page-scene">
            <ScenePhoto src={ILLUSTRATIONS.upload} />
          </div>
          <span className={`mt-3 font-semibold ${isApp ? "text-[18px] leading-snug" : "mt-4 text-[24px]"}`}>
            <Bilingual k="dropPages" lang={uiLang} />
          </span>
          <span className="muted mt-2 text-[15px] leading-snug">
            <Bilingual k="addOnePage" lang={uiLang} />
          </span>
        </button>

        <div className={`flex flex-col ${isApp ? "gap-3" : "items-start justify-center gap-4"}`}>
          <p className="muted text-[15px] leading-snug">
            <Bilingual k="showPaper" lang={uiLang} />
          </p>
          <div className={isApp ? "app-actions" : "flex flex-wrap gap-3"}>
            <Button onClick={() => cameraRef.current?.click()}>
              <Bilingual k="photographPage" lang={uiLang} />
            </Button>
            <Button variant="ghost" onClick={() => galleryRef.current?.click()}>
              <Bilingual k="addPage" lang={uiLang} />
            </Button>
            <Button onClick={extract} disabled={pages.length === 0}>
              <Bilingual k="readPages" lang={uiLang} />
            </Button>
          </div>
        </div>
      </div>

      <input
        ref={cameraRef}
        type="file"
        accept="image/jpeg,image/png"
        capture="environment"
        className="sr-only"
        aria-label="Photograph discharge summary"
        onChange={(event) => {
          if (event.target.files) setError(addPages(event.target.files));
          event.target.value = "";
        }}
      />
      <input
        ref={galleryRef}
        type="file"
        accept="image/jpeg,image/png"
        multiple
        className="sr-only"
        aria-label="Choose discharge summary photos"
        onChange={(event) => {
          if (event.target.files) setError(addPages(event.target.files));
          event.target.value = "";
        }}
      />

      {pages.length > 0 ? (
        <ul className={`mt-8 grid grid-cols-2 gap-4 ${isApp ? "" : "md:grid-cols-4"}`}>
          {pages.map((page, index) => (
            <li key={page.id} className="relative">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={page.previewUrl} alt={`Page ${index + 1}`} className="h-40 w-full rounded-2xl object-cover" />
              <button
                type="button"
                onClick={() => removePage(page.id)}
                className="absolute right-2 top-2 rounded-full bg-primary px-3 py-1 text-[16px] text-white"
              >
                {bi("remove", uiLang)}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
