"use client";

import { useCallback, useEffect, useRef, useState, type MutableRefObject } from "react";
import { fetchTTS } from "./api";

export type TextToSpeechState = {
  isSupported: boolean;
  isSpeaking: boolean;
  isPaused: boolean;
  isGemini: boolean;
  speak: (text: string) => void;
  pause: () => void;
  resume: () => void;
  stop: () => void;
};

function pickVoice(lang: string): SpeechSynthesisVoice | null {
  if (typeof window === "undefined") return null;
  const voices = window.speechSynthesis.getVoices();
  const exact = voices.find((v) => v.lang === lang);
  if (exact) return exact;
  const prefix = lang.split("-")[0];
  return voices.find((v) => v.lang.startsWith(prefix)) ?? null;
}

function browserSpeak(
  text: string,
  lang: string,
  rate: number,
  onStart: () => void,
  onEnd: () => void,
  onPause: () => void,
  onResume: () => void,
  ref: MutableRefObject<SpeechSynthesisUtterance | null>
) {
  const synth = window.speechSynthesis;
  if (synth.speaking || synth.paused) synth.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  utterance.rate = Math.max(0.5, Math.min(2, rate));
  utterance.pitch = 1;
  utterance.volume = 1;
  const voice = pickVoice(lang);
  if (voice) utterance.voice = voice;
  utterance.onstart = onStart;
  utterance.onpause = onPause;
  utterance.onresume = onResume;
  utterance.onend = onEnd;
  utterance.onerror = onEnd;
  ref.current = utterance;
  synth.speak(utterance);
}

export function useTextToSpeech(
  lang: string = "tr-TR",
  rate: number = 0.92,
  geminiKey?: string
): TextToSpeechState {
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isSupported, setIsSupported] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [isGemini, setIsGemini] = useState(false);

  useEffect(() => {
    const supported =
      typeof window !== "undefined" &&
      ("speechSynthesis" in window || "webkitSpeechSynthesis" in window);
    setIsSupported(supported);
  }, []);

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
      audioRef.current = null;
    }
    if (typeof window !== "undefined") window.speechSynthesis.cancel();
    setIsSpeaking(false);
    setIsPaused(false);
    setIsGemini(false);
  }, []);

  const speak = useCallback(
    (text: string) => {
      stop();

      if (geminiKey?.trim()) {
        setIsSpeaking(true);
        setIsGemini(true);
        fetchTTS(text, geminiKey)
          .then((buffer) => {
            const blob = new Blob([buffer], { type: "audio/wav" });
            const url = URL.createObjectURL(blob);
            const audio = new Audio(url);
            audioRef.current = audio;
            audio.onended = () => {
              URL.revokeObjectURL(url);
              setIsSpeaking(false);
              setIsGemini(false);
            };
            audio.onerror = () => {
              URL.revokeObjectURL(url);
              setIsSpeaking(false);
              setIsGemini(false);
            };
            void audio.play();
          })
          .catch(() => {
            setIsSpeaking(false);
            setIsGemini(false);
            if (!isSupported) return;
            browserSpeak(
              text, lang, rate,
              () => { setIsSpeaking(true); setIsPaused(false); },
              () => { setIsSpeaking(false); setIsPaused(false); },
              () => setIsPaused(true),
              () => setIsPaused(false),
              utteranceRef
            );
          });
        return;
      }

      if (!isSupported) return;
      browserSpeak(
        text, lang, rate,
        () => { setIsSpeaking(true); setIsPaused(false); },
        () => { setIsSpeaking(false); setIsPaused(false); },
        () => setIsPaused(true),
        () => setIsPaused(false),
        utteranceRef
      );
    },
    [isSupported, lang, rate, geminiKey, stop]
  );

  const pause = useCallback(() => {
    if (audioRef.current && !audioRef.current.paused) {
      audioRef.current.pause();
      setIsPaused(true);
    } else if (isSupported) {
      window.speechSynthesis.pause();
    }
  }, [isSupported]);

  const resume = useCallback(() => {
    if (audioRef.current && audioRef.current.paused) {
      void audioRef.current.play();
      setIsPaused(false);
    } else if (isSupported) {
      window.speechSynthesis.resume();
    }
  }, [isSupported]);

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      if (typeof window !== "undefined") window.speechSynthesis.cancel();
    };
  }, []);

  return { isSupported: isSupported || !!geminiKey?.trim(), isSpeaking, isPaused, isGemini, speak, pause, resume, stop };
}
