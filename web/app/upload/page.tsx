"use client";

import { useRef } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/Button";
import { PageHeader } from "@/components/PageHeader";
import { ILLUSTRATIONS, ScenePhoto } from "@/components/marketing/illustrations";
import { useDemo } from "@/lib/demo/store";

export default function UploadPage() {
  const router = useRouter();
  const cameraRef = useRef<HTMLInputElement>(null);
  const galleryRef = useRef<HTMLInputElement>(null);
  const { pages, addPages, removePage, extracting, extractStep, startExtract } = useDemo();

  async function extract() {
    await startExtract();
    router.push("/review/");
  }

  if (extracting) {
    return (
      <section className="flex min-h-[60vh] flex-col items-center justify-center text-center">
        <div className="page-scene page-scene-center">
          <ScenePhoto src={ILLUSTRATIONS.review} />
        </div>
        <h1 className="font-display text-[40px] text-primary">Reading the paper</h1>
        <p className="mt-3 text-primary/80">{extractStep}</p>
        <p className="muted mt-8">This can take up to two minutes on a live document.</p>
      </section>
    );
  }

  return (
    <section>
      <PageHeader
        eyebrow="Discharge summary"
        title="Photograph the paper."
        description="Then we check that the pill box matches what your doctor wrote."
      />

      <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <button
          type="button"
          onClick={() => galleryRef.current?.click()}
          className="flex min-h-[320px] flex-col items-center justify-center rounded-[32px] border-2 border-dashed border-secondary/35 bg-white px-8 py-12 text-center"
        >
          <div className="page-scene">
            <ScenePhoto src={ILLUSTRATIONS.upload} />
          </div>
          <span className="mt-4 text-[24px] font-semibold">Drop pages here, or browse</span>
          <span className="muted mt-2">JPEG or PNG. Add one page at a time if you prefer.</span>
        </button>

        <div className="flex flex-col items-start justify-center gap-4">
          <p className="font-kannada muted">ಡಾಕ್ಟರ್ ಬರೆದದ್ದನ್ನೇ ತೋರಿಸುತ್ತೇವೆ.</p>
          <div className="flex flex-wrap gap-3">
            <Button onClick={() => cameraRef.current?.click()}>Photograph page</Button>
            <Button variant="ghost" onClick={() => galleryRef.current?.click()}>
              Add another page
            </Button>
          </div>
          <Button variant="secondary" onClick={extract}>
            {pages.length > 0 ? "Read these pages" : "Use demo summary"}
          </Button>
          <p className="muted">
            Demo mode loads the cardiac fixture so you can review, activate, and run Box Check without
            a live backend.
          </p>
        </div>
      </div>

      <input
        ref={cameraRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="sr-only"
        aria-label="Photograph discharge summary"
        onChange={(event) => {
          if (event.target.files) addPages(event.target.files);
          event.target.value = "";
        }}
      />
      <input
        ref={galleryRef}
        type="file"
        accept="image/*"
        multiple
        className="sr-only"
        aria-label="Choose discharge summary photos"
        onChange={(event) => {
          if (event.target.files) addPages(event.target.files);
          event.target.value = "";
        }}
      />

      {pages.length > 0 ? (
        <ul className="mt-8 grid grid-cols-2 gap-4 md:grid-cols-4">
          {pages.map((page, index) => (
            <li key={page.id} className="relative">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={page.previewUrl}
                alt={`Page ${index + 1}`}
                className="h-40 w-full rounded-2xl object-cover"
              />
              <button
                type="button"
                onClick={() => removePage(page.id)}
                className="absolute right-2 top-2 rounded-full bg-primary px-3 py-1 text-[16px] text-white"
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

