export function AppChrome() {
  return (
    <header className="bg-ss-navy text-white">
      <div className="mx-auto flex max-w-[1400px] items-center justify-between gap-4 px-4 py-2.5 md:px-6 md:py-3">
        <span className="text-lg font-bold tracking-tight text-white">Skyscanner</span>
        <div className="flex shrink-0 items-center gap-2 text-sm md:gap-3">
          <span className="hidden text-white/90 lg:inline">Help</span>
          <span className="hidden rounded-ss border border-white/35 bg-white/5 px-2.5 py-1.5 text-white/95 sm:inline">
            English (UK) · EUR
          </span>
          <button
            type="button"
            className="flex h-9 w-9 items-center justify-center rounded-full border border-white/35 bg-transparent text-white transition hover:bg-white/10"
            aria-label="Saved"
          >
            ♡
          </button>
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-ss-orange text-sm font-bold text-white shadow-md">
            R
          </div>
        </div>
      </div>
    </header>
  );
}
