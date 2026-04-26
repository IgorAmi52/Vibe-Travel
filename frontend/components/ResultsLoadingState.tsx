"use client";

type ResultsLoadingStateProps = {
  statusMessage: string;
};

function SparkleIcon() {
  return (
    <div
      className="animate-sparkle-pulse text-ss-accent drop-shadow-[0_0_12px_rgb(0_98_227/0.4)] motion-reduce:animate-none motion-reduce:drop-shadow-none"
      aria-hidden
    >
      <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
        <defs>
          <linearGradient id="sp1" x1="0" y1="0" x2="1" y2="1">
            <stop stopColor="#4d9fff" />
            <stop offset="1" stopColor="#0062e3" />
          </linearGradient>
          <linearGradient id="sp2" x1="1" y1="0" x2="0" y2="1">
            <stop stopColor="#0062e3" />
            <stop offset="1" stopColor="#071d3d" />
          </linearGradient>
        </defs>
        <path
          d="M24 4l1.8 6.2L32 12l-6.2 1.8L24 20l-1.8-6.2L16 12l6.2-1.8L24 4z"
          fill="url(#sp1)"
          opacity="0.95"
        />
        <path
          d="M38 22l1.2 4.1L43 27l-4.1 1.2L38 32l-1.2-4.1L33 27l4.1-1.2L38 22z"
          fill="url(#sp2)"
          opacity="0.88"
        />
        <path
          d="M14 28l1.2 4.1L19 33l-4.1 1.2L14 38l-1.2-4.1L9 33l4.1-1.2L14 28z"
          fill="url(#sp1)"
          opacity="0.78"
        />
        <path
          d="M26 34l0.9 3.1L30 38l-3.1 0.9L26 42l-0.9-3.1L22 38l3.1-0.9L26 34z"
          fill="url(#sp2)"
          opacity="0.55"
        />
      </svg>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="flex animate-pulse flex-col overflow-hidden rounded-ss border border-slate-200 bg-white shadow-sm motion-reduce:animate-none sm:flex-row">
      <div className="h-36 w-full bg-slate-200 sm:h-auto sm:w-[200px]" />
      <div className="flex flex-1 flex-col gap-2 p-3 sm:p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 space-y-1.5">
            <div className="h-5 w-[70%] rounded bg-slate-200" />
            <div className="h-3 w-1/3 rounded bg-slate-200" />
          </div>
          <div className="space-y-1">
            <div className="h-6 w-20 rounded bg-slate-200" />
            <div className="h-3 w-14 rounded bg-slate-200" />
          </div>
        </div>
        <div className="flex gap-1.5">
          <div className="h-5 w-20 rounded-full bg-slate-200" />
          <div className="h-5 w-24 rounded-full bg-slate-200" />
        </div>
        <div className="h-3 w-full rounded bg-slate-100" />
      </div>
      <div className="hidden w-[120px] items-center border-l border-slate-200 p-3 sm:flex">
        <div className="h-9 w-full rounded-ss bg-slate-200" />
      </div>
    </div>
  );
}

export function ResultsLoadingState({ statusMessage }: ResultsLoadingStateProps) {
  return (
    <div className="relative min-h-[320px]">
      <div className="space-y-3 opacity-50">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
      <div
        className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center bg-ss-page/85 px-4 backdrop-blur-[1px]"
        role="status"
        aria-live="polite"
      >
        <SparkleIcon />
        <p className="mt-4 max-w-sm text-center text-sm font-semibold text-ss-navy">
          <span className="hidden motion-reduce:inline">Loading results…</span>
          <span className="inline motion-reduce:hidden">{statusMessage}</span>
        </p>
      </div>
    </div>
  );
}
