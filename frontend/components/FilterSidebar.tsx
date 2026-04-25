"use client";

import { formatMoney } from "@/lib/formatMoney";

function Chevron(props: { className?: string }) {
  return (
    <svg
      className={props.className}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden
    >
      <path d="M7 10l5 5 5-5z" />
    </svg>
  );
}

function StarIcon({ filled }: { filled: boolean }) {
  return (
    <span
      className={
        filled ? "text-orange-500" : "text-slate-300"
      }
      aria-hidden
    >
      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z" />
      </svg>
    </span>
  );
}

function StarRow({
  label,
  filledStars,
  count,
  disabled,
}: {
  label: string;
  filledStars: number;
  count: number;
  disabled?: boolean;
}) {
  return (
    <label
      className={`flex cursor-pointer items-center gap-3 py-2 text-sm ${
        disabled ? "cursor-not-allowed opacity-45" : "text-slate-900"
      }`}
    >
      <input
        type="checkbox"
        disabled={disabled}
        className="h-4 w-4 shrink-0 rounded border-slate-400 text-ss-accent focus:ring-ss-accent/30 disabled:cursor-not-allowed"
      />
      <span className={`min-w-0 flex-1 ${disabled ? "" : "font-medium"}`}>{label}</span>
      <span className="flex gap-0.5">
        {[0, 1, 2, 3, 4].map((i) => (
          <StarIcon key={i} filled={i < filledStars} />
        ))}
      </span>
      <span className="w-8 shrink-0 text-right text-xs text-slate-500">{count}</span>
    </label>
  );
}

/** Static dual-handle style range (visual parity with Skyscanner) */
function PriceRangeVisual() {
  return (
    <div className="relative mt-1 h-9 w-full">
      <div className="absolute left-0 right-0 top-1/2 h-2 -translate-y-1/2 rounded-full bg-slate-200">
        <div className="absolute inset-y-0 left-0 right-0 rounded-full bg-ss-accent" />
      </div>
      <div
        className="absolute left-0 top-1/2 z-10 h-5 w-5 -translate-y-1/2 rounded-full border-[3px] border-white bg-ss-accent shadow-md"
        aria-hidden
      />
      <div
        className="absolute right-0 top-1/2 z-10 h-5 w-5 -translate-y-1/2 rounded-full border-[3px] border-white bg-ss-accent shadow-md"
        aria-hidden
      />
    </div>
  );
}

const PRICE_MIN = 7800;
const PRICE_MAX = 19700;
const PRICE_CURRENCY = "EUR";

const reviewOptions: { label: string; count: number }[] = [
  { label: "5.0 Outstanding", count: 1 },
  { label: "4.5+ Excellent", count: 79 },
  { label: "4.0+ Very good", count: 86 },
  { label: "3.5+ Good", count: 12 },
  { label: "3.0+ Satisfactory", count: 4 },
];

export function FilterSidebar() {
  return (
    <aside
      className="h-fit w-full shrink-0 overflow-hidden rounded-lg border border-slate-200/90 bg-[#f2f4f7] lg:w-72 xl:w-80"
      aria-label="Filters"
    >
      <details open className="group border-b border-slate-200 bg-[#f2f4f7]">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-4 py-3.5 pr-3 font-bold text-slate-900 outline-none marker:content-none [&::-webkit-details-marker]:hidden">
          Price
          <Chevron className="h-5 w-5 shrink-0 text-slate-600 transition group-open:-rotate-180" />
        </summary>
        <div className="space-y-3 px-4 pb-4">
          <div className="flex justify-between text-sm font-semibold tabular-nums text-slate-900">
            <span>{formatMoney(PRICE_MIN, PRICE_CURRENCY)}</span>
            <span>{formatMoney(PRICE_MAX, PRICE_CURRENCY)}</span>
          </div>
          <PriceRangeVisual />
        </div>
      </details>

      <details open className="group border-b border-slate-200 bg-[#f2f4f7]">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-4 py-3.5 pr-3 font-bold text-slate-900 outline-none marker:content-none [&::-webkit-details-marker]:hidden">
          Hotel review score
          <Chevron className="h-5 w-5 shrink-0 text-slate-600 transition group-open:-rotate-180" />
        </summary>
        <ul className="space-y-0.5 px-4 pb-4">
          {reviewOptions.map(({ label, count }) => (
            <li key={label}>
              <label className="flex cursor-pointer items-center gap-3 py-2 text-sm text-slate-900">
                <input
                  type="checkbox"
                  className="h-4 w-4 shrink-0 rounded border-slate-400 text-ss-accent focus:ring-ss-accent/30"
                />
                <span className="min-w-0 flex-1 font-medium">{label}</span>
                <span className="w-8 shrink-0 text-right text-xs text-slate-500 tabular-nums">
                  {count}
                </span>
              </label>
            </li>
          ))}
        </ul>
      </details>

      <details open className="group bg-[#f2f4f7]">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-4 py-3.5 pr-3 font-bold text-slate-900 outline-none marker:content-none [&::-webkit-details-marker]:hidden">
          Star rating
          <Chevron className="h-5 w-5 shrink-0 text-slate-600 transition group-open:-rotate-180" />
        </summary>
        <div className="space-y-0.5 px-4 pb-4">
          <StarRow label="5 stars" filledStars={5} count={32} />
          <StarRow label="4 stars" filledStars={4} count={24} />
          <StarRow label="3 stars" filledStars={3} count={28} />
          <StarRow label="2 stars" filledStars={2} count={0} disabled />
          <StarRow label="1 star" filledStars={1} count={0} disabled />
        </div>
      </details>
    </aside>
  );
}
