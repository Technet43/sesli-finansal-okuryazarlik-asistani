"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type TextToSpeechState = {
  isSupported: boolean;
  isSpeaking: boolean;
  isPaused: boolean;
  speak: (text: string) => void;
  pause: () => void;
  resume: () => void;
  stop: () => void;
};

export function useTextToSpeech(lang: string = "tr-TR"): TextToSpeechState {
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const [isSupported, setIsSupported] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isPaused, setIsPaused] = useState(false);

  useEffect(() => {
    const supported =
      typeof window !== "undefined" &&
      ("speechSynthesis" in window || "webkitSpeechSynthesis" in window);
    setIsSupported(supported);
  }, []);

  const speak = useCallback(
    (text: string) => {
      if (!isSupported) return;

      const synthesis = window.speechSynthesis;
      if (synthesis.speaking || synthesis.paused) {
        synthesis.cancel();
      }

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang;
      utterance.rate = 1;
      utterance.pitch = 1;
      utterance.volume = 1;

      utterance.onstart = () => {
        setIsSpeaking(true);
        setIsPaused(false);
      };

      utterance.onpause = () => {
        setIsPaused(true);
      };

      utterance.onresume = () => {
        setIsPaused(false);
      };

      utterance.onend = () => {
        setIsSpeaking(false);
        setIsPaused(false);
      };

      utterance.onerror = () => {
        setIsSpeaking(false);
        setIsPaused(false);
      };

      utteranceRef.current = utterance;
      synthesis.speak(utterance);
    },
    [isSupported, lang]
  );

  const pause = useCallback(() => {
    if (!isSupported) return;
    window.speechSynthesis.pause();
  }, [isSupported]);

  const resume = useCallback(() => {
    if (!isSupported) return;
    window.speechSynthesis.resume();
  }, [isSupported]);

  const stop = useCallback(() => {
    if (!isSupported) return;
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
    setIsPaused(false);
  }, [isSupported]);

  useEffect(() => {
    return () => {
      if (typeof window !== "undefined") {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  return { isSupported, isSpeaking, isPaused, speak, pause, resume, stop };
}
