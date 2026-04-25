export function AppChrome() {
  return (
    <header className="bg-ss-navy text-white">
      <div className="mx-auto flex max-w-[1400px] items-center justify-between gap-4 px-4 py-3 md:px-6">
        <div className="flex items-center gap-6">
          <span className="text-lg font-semibold tracking-tight">Skyscanner</span>
          <nav className="hidden items-center gap-1 text-sm md:flex" aria-label="Primary">
            <a
              href="#"
              className="rounded px-3 py-2 text-white/90 hover:bg-white/10"
            >
              Flights
            </a>
            <a
              href="#"
              className="rounded px-3 py-2 text-white/90 hover:bg-white/10"
            >
              Hotels
            </a>
            <a
              href="#"
              className="rounded px-3 py-2 text-white/90 hover:bg-white/10"
            >
              Cars
            </a>
            <a
              href="#"
              className="relative rounded bg-ss-accent px-3 py-2 font-medium text-white"
            >
              Packages
              <span className="absolute -right-1 -top-1 rounded bg-pink-500 px-1.5 text-[10px] font-bold leading-none text-white">
                New
              </span>
            </a>
          </nav>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="hidden lg:inline text-white/80">Help</span>
          <span className="hidden rounded border border-white/20 px-2 py-1 text-white/90 sm:inline">
            English (UK) · EUR
          </span>
          <button
            type="button"
            className="flex h-9 w-9 items-center justify-center rounded-full border border-white/30"
            aria-label="Saved"
          >
            ♡
          </button>
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-ss-accent text-sm font-semibold">
            R
          </div>
        </div>
      </div>
    </header>
  );
}
