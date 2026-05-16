"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { transcribeAudio } from "./api";

const MAX_RECORDING_MS = 60_000;

type RecognitionAlternative = { transcript: string };
type RecognitionResult = ArrayLike<RecognitionAlternative> & { isFinal: boolean };
type RecognitionResultList = ArrayLike<RecognitionResult>;
type RecognitionErrorEvent = Event & { error: string; message?: string };
type RecognitionInstance = EventTarget & {
  lang: string; continuous: boolean; interimResults: boolean; maxAlternatives: number;
  start: () => void; stop: () => void; abort: () => void;
  onresult: ((event: { results: RecognitionResultList }) => void) | null;
  onerror: ((event: RecognitionErrorEvent) => void) | null;
  onend: (() => void) | null; onstart: (() => void) | null;
};
type RecognitionConstructor = new () => RecognitionInstance;

function getRecognitionCtor(): RecognitionConstructor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { SpeechRecognition?: RecognitionConstructor; webkitSpeechRecognition?: RecognitionConstructor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export type SpeechRecognitionState = {
  isSupported: boolean;
  isListening: boolean;
  isGemini: boolean;
  transcript: string;
  error: string;
  start: () => void;
  stop: () => void;
  reset: () => void;
};

export function useSpeechRecognition(lang: string = "tr-TR", geminiKey?: string): SpeechRecognitionState {
  const recognitionRef = useRef<RecognitionInstance | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const interimTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const recordingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [isSupported, setIsSupported] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState("");

  const useGemini = !!geminiKey?.trim();

  useEffect(() => {
    return () => {
      if (recordingTimerRef.current) clearTimeout(recordingTimerRef.current);
      try { mediaRecorderRef.current?.stop(); } catch { /* ignore */ }
    };
  }, []);

  // Set up browser recognition (used when no gemini key)
  useEffect(() => {
    if (useGemini) { setIsSupported(true); return; }
    const Ctor = getRecognitionCtor();
    if (!Ctor) { setIsSupported(false); return; }
    setIsSupported(true);
    const rec = new Ctor();
    rec.lang = lang;
    rec.continuous = false;
    rec.interimResults = true;
    rec.maxAlternatives = 1;
    rec.onstart = () => { setError(""); setIsListening(true); };
    rec.onresult = (event) => {
      let final = ""; let interim = "";
      for (let i = 0; i < event.results.length; i++) {
        const result = event.results[i];
        const alt = result[0];
        if (!alt) continue;
        if (result.isFinal) final += alt.transcript;
        else interim += alt.transcript;
      }
      if (final) {
        if (interimTimerRef.current) clearTimeout(interimTimerRef.current);
        setTranscript(final.trim());
      } else if (interim) {
        if (interimTimerRef.current) clearTimeout(interimTimerRef.current);
        interimTimerRef.current = setTimeout(() => setTranscript(interim.trim()), 120);
      }
    };
    rec.onerror = (event) => {
      const msgs: Record<string, string> = {
        "not-allowed": "Mikrofon izni reddedildi.",
        "no-speech": "Ses algılanamadı.",
        "audio-capture": "Mikrofon bulunamadı.",
        network: "Ağ hatası.",
        aborted: "",
      };
      const msg = msgs[event.error] ?? `Hata: ${event.error}`;
      if (msg) setError(msg);
      setIsListening(false);
    };
    rec.onend = () => setIsListening(false);
    recognitionRef.current = rec;
    return () => {
      if (interimTimerRef.current) clearTimeout(interimTimerRef.current);
      rec.onstart = null; rec.onresult = null; rec.onerror = null; rec.onend = null;
      try { rec.abort(); } catch { /* ignore */ }
      recognitionRef.current = null;
    };
  }, [lang, useGemini]);

  const start = useCallback(() => {
    setError(""); setTranscript("");

    if (useGemini) {
      // Gemini STT: record via MediaRecorder, send on stop
      navigator.mediaDevices.getUserMedia({ audio: true })
        .then((stream) => {
          const mr = new MediaRecorder(stream, { mimeType: "audio/webm" });
          chunksRef.current = [];
          mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
          mr.onstop = () => {
            if (recordingTimerRef.current) {
              clearTimeout(recordingTimerRef.current);
              recordingTimerRef.current = null;
            }
            stream.getTracks().forEach((t) => t.stop());
            const blob = new Blob(chunksRef.current, { type: "audio/webm" });
            setIsListening(false);
            transcribeAudio(blob, geminiKey)
              .then((text) => { if (text) setTranscript(text); })
              .catch((err: unknown) => setError(err instanceof Error ? err.message : "Transkripsiyon hatası."));
          };
          mr.start();
          recordingTimerRef.current = setTimeout(() => {
            if (mr.state === "recording") mr.stop();
          }, MAX_RECORDING_MS);
          mediaRecorderRef.current = mr;
          setIsListening(true);
        })
        .catch(() => setError("Mikrofon izni reddedildi."));
      return;
    }

    const rec = recognitionRef.current;
    if (!rec) return;
    try { rec.start(); } catch { /* already started */ }
  }, [useGemini, geminiKey]);

  const stop = useCallback(() => {
    if (useGemini) {
      if (recordingTimerRef.current) {
        clearTimeout(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
      mediaRecorderRef.current?.stop();
    } else {
      recognitionRef.current?.stop();
    }
  }, [useGemini]);

  const reset = useCallback(() => { setTranscript(""); setError(""); }, []);

  return { isSupported, isListening, isGemini: useGemini, transcript, error, start, stop, reset };
}
