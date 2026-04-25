"use client";

type ResultsLoadingStateProps = {
  statusMessage: string;
};

function SparkleIcon() {
  return (
    <div
      className="animate-sparkle-pulse text-ss-accent motion-reduce:animate-none motion-reduce:opacity-100"
      aria-hidden
    >
      <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
        <path
          d="M24 4l1.8 6.2L32 12l-6.2 1.8L24 20l-1.8-6.2L16 12l6.2-1.8L24 4z"
          fill="currentColor"
          opacity="0.9"
        />
        <path
          d="M38 22l1.2 4.1L43 27l-4.1 1.2L38 32l-1.2-4.1L33 27l4.1-1.2L38 22z"
          fill="currentColor"
          opacity="0.65"
        />
        <path
          d="M14 28l1.2 4.1L19 33l-4.1 1.2L14 38l-1.2-4.1L9 33l4.1-1.2L14 28z"
          fill="currentColor"
          opacity="0.65"
        />
        <path
          d="M26 34l0.9 3.1L30 38l-3.1 0.9L26 42l-0.9-3.1L22 38l3.1-0.9L26 34z"
          fill="currentColor"
          opacity="0.45"
        />
      </svg>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="flex animate-pulse flex-col overflow-hidden rounded-lg border border-neutral-200 bg-white motion-reduce:animate-none md:flex-row">
      <div className="h-48 w-full bg-neutral-200 md:h-auto md:w-[280px]" />
      <div className="flex flex-1 flex-col gap-3 p-4 md:p-5">
        <div className="h-6 w-[75%] rounded bg-neutral-200" />
        <div className="h-4 w-1/2 rounded bg-neutral-200" />
        <div className="flex gap-2">
          <div className="h-6 w-20 rounded-full bg-neutral-200" />
          <div className="h-6 w-24 rounded-full bg-neutral-200" />
        </div>
        <div className="h-4 w-full rounded bg-neutral-200" />
        <div className="h-4 w-5/6 rounded bg-neutral-200" />
      </div>
      <div className="hidden w-56 flex-col gap-3 border-l border-neutral-100 p-4 md:flex">
        <div className="h-8 w-full rounded bg-neutral-200" />
        <div className="h-10 w-full rounded bg-neutral-200" />
      </div>
    </div>
  );
}

export function ResultsLoadingState({ statusMessage }: ResultsLoadingStateProps) {
  return (
    <div className="relative min-h-[420px]">
      <div className="space-y-4 opacity-60">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
      <div
        className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center bg-white/70 px-4"
        role="status"
        aria-live="polite"
      >
        <SparkleIcon />
        <p className="mt-4 max-w-sm text-center text-sm font-medium text-ss-navy">
          <span className="hidden motion-reduce:inline">Loading results…</span>
          <span className="inline motion-reduce:hidden">{statusMessage}</span>
        </p>
      </div>
    </div>
  );
}
