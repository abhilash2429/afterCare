"use client";

import { useEffect, useRef, useState } from "react";
import { Bilingual } from "@/components/Bilingual";
import { Button } from "@/components/Button";
import { useApp } from "@/lib/app/store";
import { bi } from "@/lib/copy";
import type { AudioClip } from "@/lib/api/types";

export function AudioPlayer({
  clip,
  onLoad,
}: {
  clip: AudioClip | null;
  onLoad: () => Promise<AudioClip | null>;
}) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [loading, setLoading] = useState(false);
  const { uiLang } = useApp();

  useEffect(() => {
    if (clip?.url && audioRef.current) {
      audioRef.current.load();
    }
  }, [clip?.url]);

  async function play() {
    if (!clip) {
      setLoading(true);
      const next = await onLoad();
      setLoading(false);
      if (next?.url) {
        window.setTimeout(() => audioRef.current?.play().catch(() => undefined), 0);
      }
      return;
    }
    if (clip.url) await audioRef.current?.play().catch(() => undefined);
  }

  return (
    <div className="app-panel rounded-3xl bg-card p-6">
      <div className="app-actions">
        <Button variant="ghost" onClick={play} disabled={loading}>
          {loading ? bi("loadingVoice", uiLang) : bi("speakSchedule", uiLang)}
        </Button>
        {clip?.spokenLanguage === "hi" ? <Bilingual k="kannadaAsHindi" lang={uiLang} className="muted" /> : null}
      </div>
      {clip?.url ? <audio ref={audioRef} className="mt-3 w-full" controls src={clip.url} /> : null}
      {clip?.text ? <p className="mt-3 text-[18px] leading-snug">{clip.text}</p> : null}
    </div>
  );
}
