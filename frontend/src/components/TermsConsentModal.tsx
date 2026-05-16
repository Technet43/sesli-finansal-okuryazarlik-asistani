"use client";

import { AlertTriangle, CheckCircle2, FileText, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import { useMemo, useState } from "react";

const TERMS_VERSION = "v1.0.0";

const REQUIRED_CHECKS = [
  {
    id: "not_investment_advice",
    label:
      "Bu uygulamanın yatırım tavsiyesi, yatırım danışmanlığı, portföy yönetimi veya alım-satım önerisi sunmadığını kabul ediyorum.",
  },
  {
    id: "ai_may_be_wrong",
    label:
      "Yapay zeka çıktılarının hatalı, eksik, güncel olmayan veya yanlış yorumlanmış bilgiler içerebileceğini kabul ediyorum.",
  },
  {
    id: "official_sources_required",
    label:
      "Yatırım veya finansal karar almadan önce resmi KAP bildirimlerini, şirket raporlarını ve ilgili resmi belgeleri kontrol etmem gerektiğini kabul ediyorum.",
  },
  {
    id: "user_responsible",
    label:
      "Uygulamayı kullanmam sonucunda oluşabilecek kar, zarar, fırsat kaybı veya diğer finansal sonuçlardan yalnızca benim sorumlu olduğumu kabul ediyorum.",
  },
];

type TermsConsentModalProps = {
  onAccept: () => void;
};

export function TermsConsentModal({ onAccept }: TermsConsentModalProps) {
  const [accepted, setAccepted] = useState<Record<string, boolean>>({});
  const allAccepted = useMemo(
    () => REQUIRED_CHECKS.every((item) => accepted[item.id]),
    [accepted]
  );

  function toggle(id: string) {
    setAccepted((current) => ({ ...current, [id]: !current[id] }));
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-3 py-4 backdrop-blur-md sm:px-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="terms-title"
    >
      <section className="glass-surface max-h-[92vh] w-full max-w-3xl overflow-hidden rounded-[28px] text-ink shadow-2xl">
        <div className="border-b border-white/70 px-5 py-4 sm:px-7 sm:py-5">
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-iris-indigo/10 text-iris-indigo">
              <ShieldCheck className="h-5 w-5" aria-hidden />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-ink-muted">
                Kullanıcı kabulü · {TERMS_VERSION}
              </p>
              <h2 id="terms-title" className="mt-1 text-xl font-bold tracking-tight text-ink sm:text-2xl">
                Önemli bilgilendirme ve sorumluluk reddi
              </h2>
            </div>
          </div>
        </div>

        <div className="max-h-[58vh] overflow-y-auto px-5 py-5 sm:px-7">
          <div className="grid gap-3 sm:grid-cols-3">
            <InfoBlock
              icon={<AlertTriangle className="h-4 w-4" aria-hidden />}
              title="Yatırım tavsiyesi değildir"
              text="KAP Okuryazar yalnızca finansal okuryazarlık, eğitim ve KAP bildirimlerini sadeleştirme amacıyla sunulur."
            />
            <InfoBlock
              icon={<FileText className="h-4 w-4" aria-hidden />}
              title="Resmi kaynak yerine geçmez"
              text="Asıl ve bağlayıcı kaynak resmi KAP bildirimleri, şirket açıklamaları, finansal raporlar ve ilgili mevzuattır."
            />
            <InfoBlock
              icon={<CheckCircle2 className="h-4 w-4" aria-hidden />}
              title="AI hata yapabilir"
              text="Özetler, sesli anlatımlar, karşılaştırmalar ve sohbet cevapları eksik veya hatalı olabilir."
            />
          </div>

          <div className="mt-5 space-y-3 rounded-2xl border border-white/70 bg-white/55 p-4 text-sm leading-6 text-ink-soft">
            <p>
              Bu uygulama yatırım danışmanlığı, portföy yönetimi, hedef fiyat analizi,
              alım-satım önerisi veya kişiye özel finansal yönlendirme hizmeti sunmaz.
              Uygulamadaki hiçbir ifade al, sat, tut veya benzeri bir yatırım kararı
              olarak yorumlanmamalıdır.
            </p>
            <p>
              Kullanıcı, uygulamadaki bilgilere dayanarak yaptığı veya yapmadığı tüm
              finansal işlemlerden, oluşabilecek kar veya zarardan ve diğer sonuçlardan
              kendisinin sorumlu olduğunu kabul eder.
            </p>
            <p>
              Sesli giriş, PDF/görsel yükleme, yapay zeka sohbeti ve metin okuma gibi
              özelliklerde kullanıcının sağladığı içerikler ilgili servisler tarafından
              işlenebilir. Gizli, kişisel veya paylaşılmasını istemediğiniz belgeleri
              uygulamaya yüklemeyiniz.
            </p>
            <p>
              Kullanıcı kendi API anahtarını girerse, bu anahtarın güvenliği ve kullanım
              maliyeti kullanıcının sorumluluğundadır. API anahtarı uygulama tarafından
              kalıcı olarak sunucuda saklanmaz.
            </p>
          </div>

          <div className="mt-5 space-y-3">
            {REQUIRED_CHECKS.map((item) => (
              <label
                key={item.id}
                className="flex cursor-pointer items-start gap-3 rounded-2xl border border-white/70 bg-white/60 p-4 text-sm font-medium leading-6 text-ink-soft transition hover:bg-white/75"
              >
                <input
                  type="checkbox"
                  checked={!!accepted[item.id]}
                  onChange={() => toggle(item.id)}
                  className="mt-1 h-4 w-4 shrink-0 accent-iris-indigo"
                />
                <span>{item.label}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="border-t border-white/70 bg-white/55 px-5 py-4 sm:px-7">
          <button
            type="button"
            disabled={!allAccepted}
            onClick={onAccept}
            className="h-12 w-full rounded-2xl bg-gradient-to-r from-iris-indigo via-iris-sky to-iris-rose px-5 text-sm font-bold text-white shadow-glass-soft transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-45 disabled:hover:translate-y-0"
          >
            Tüm şartları okudum, anladım ve kabul ediyorum
          </button>
          <p className="mt-3 text-center text-[11px] leading-5 text-ink-muted">
            Devam ederek bu uygulamanın yalnızca eğitim, bilgilendirme ve finansal
            okuryazarlık amacıyla sunulduğunu kabul etmiş olursunuz.
          </p>
        </div>
      </section>
    </div>
  );
}

function InfoBlock({
  icon,
  title,
  text,
}: {
  icon: ReactNode;
  title: string;
  text: string;
}) {
  return (
    <div className="rounded-2xl border border-white/70 bg-white/55 p-4">
      <div className="mb-2 flex items-center gap-2 text-iris-indigo">
        {icon}
        <h3 className="text-sm font-bold text-ink">{title}</h3>
      </div>
      <p className="text-xs leading-5 text-ink-muted">{text}</p>
    </div>
  );
}
