"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type RecognitionAlternative = {
  transcript: string;
};

type RecognitionResult = ArrayLike<RecognitionAlternative> & {
  isFinal: boolean;
};

type RecognitionResultList = ArrayLike<RecognitionResult>;

type RecognitionErrorEvent = Event & { error: string; message?: string };

type RecognitionInstance = EventTarget & {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: { results: RecognitionResultList }) => void) | null;
  onerror: ((event: RecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  onstart: (() => void) | null;
};

type RecognitionConstructor = new () => RecognitionInstance;

function getRecognitionCtor(): RecognitionConstructor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    SpeechRecognition?: RecognitionConstructor;
    webkitSpeechRecognition?: RecognitionConstructor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export type SpeechRecognitionState = {
  isSupported: boolean;
  isListening: boolean;
  transcript: string;
  error: string;
  start: () => void;
  stop: () => void;
  reset: () => void;
};

export function useSpeechRecognition(lang: string = "tr-TR"): SpeechRecognitionState {
  const recognitionRef = useRef<RecognitionInstance | null>(null);
  const [isSupported, setIsSupported] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const Ctor = getRecognitionCtor();
    if (!Ctor) {
      setIsSupported(false);
      return;
    }
    setIsSupported(true);
    const rec = new Ctor();
    rec.lang = lang;
    rec.continuous = false;
    rec.interimResults = true;
    rec.maxAlternatives = 1;

    rec.onstart = () => {
      setError("");
      setIsListening(true);
    };

    rec.onresult = (event) => {
      let final = "";
      let interim = "";
      for (let i = 0; i < event.results.length; i++) {
        const result = event.results[i];
        const alt = result[0];
        if (!alt) continue;
        if (result.isFinal) {
          final += alt.transcript;
        } else {
          interim += alt.transcript;
        }
      }
      setTranscript((final || interim).trim());
    };

    rec.onerror = (event) => {
      const code = event.error;
      const messages: Record<string, string> = {
        "not-allowed": "Mikrofon izni reddedildi. Tarayıcı ayarlarından izin ver.",
        "service-not-allowed": "Mikrofon servisi engellendi.",
        "no-speech": "Ses algılanamadı, tekrar dene.",
        "audio-capture": "Mikrofon bulunamadı.",
        network: "Ağ hatası: konuşma tanıma çalışmadı.",
        aborted: "",
      };
      const msg = messages[code] ?? `Konuşma tanıma hatası: ${code}`;
      if (msg) setError(msg);
      setIsListening(false);
    };

    rec.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = rec;
    return () => {
      rec.onstart = null;
      rec.onresult = null;
      rec.onerror = null;
      rec.onend = null;
      try {
        rec.abort();
      } catch {
        // ignore
      }
      recognitionRef.current = null;
    };
  }, [lang]);

  const start = useCallback(() => {
    const rec = recognitionRef.current;
    if (!rec) return;
    setError("");
    setTranscript("");
    try {
      rec.start();
    } catch {
      // already started
    }
  }, []);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  const reset = useCallback(() => {
    setTranscript("");
    setError("");
  }, []);

  return { isSupported, isListening, transcript, error, start, stop, reset };
}
