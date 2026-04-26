export function AppChrome() {
  return (
    <header className="relative z-40 bg-ss-navy text-white">
      <div className="mx-auto flex max-w-[1400px] items-center justify-between gap-4 px-4 pb-2 pt-3 md:px-6 md:pb-2.5 md:pt-4">
        <span className="text-lg font-bold tracking-tight text-white">
          VibeTravel
        </span>
        <div className="flex shrink-0 items-center gap-1.5 text-sm md:gap-2">
          <button
            type="button"
            className="hidden h-9 items-center rounded-ss px-3 text-white/85 transition hover:bg-white/10 hover:text-white lg:inline-flex"
          >
            Help
          </button>
          <span className="hidden h-9 items-center rounded-ss border border-white/30 bg-white/5 px-3 text-white/95 sm:inline-flex">
            English (UK) · EUR
          </span>
          <button
            type="button"
            className="flex h-9 w-9 items-center justify-center rounded-full border border-white/30 bg-transparent text-white transition hover:border-white/60 hover:bg-white/10"
            aria-label="Saved"
          >
            <svg
              className="h-[18px] w-[18px]"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.8}
              viewBox="0 0 24 24"
              aria-hidden
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 21s-7-4.35-9.5-9.05C1 8.5 3 5 6.5 5c2 0 3.5 1 5.5 3 2-2 3.5-3 5.5-3C21 5 23 8.5 21.5 11.95 19 16.65 12 21 12 21z"
              />
            </svg>
          </button>
          <div
            className="flex h-9 w-9 items-center justify-center rounded-full bg-ss-orange text-sm font-bold text-white shadow-md ring-1 ring-white/10"
            aria-label="Account"
          >
            R
          </div>
        </div>
      </div>
    </header>
  );
}
