"use client";

type SearchSummaryBarProps = {
  displayTheme: string;
  refinePlaceholder: string;
  refineValue: string;
  onRefineChange: (value: string) => void;
  onSubmit: () => void;
  loading: boolean;
  disabled?: boolean;
};

export function SearchSummaryBar({
  displayTheme,
  refinePlaceholder,
  refineValue,
  onRefineChange,
  onSubmit,
  loading,
  disabled,
}: SearchSummaryBarProps) {
  return (
    <div>
      {/* Navy header block — search bar overlaps bottom edge into the grey canvas */}
      <div className="relative z-30 bg-gradient-to-b from-ss-navy via-ss-navy to-ss-navy-light pb-8 md:pb-9">
        <div className="mx-auto flex max-w-[1400px] items-center gap-2.5 px-4 pb-2 pt-0.5 md:px-6 md:pb-2.5">
          <svg
            className="h-[18px] w-[18px] shrink-0 text-ss-orange"
            fill="currentColor"
            viewBox="0 0 24 24"
            aria-hidden
          >
            <path d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z" />
            <path d="M18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456Z" />
          </svg>
          <p className="min-w-0 flex-1 text-sm font-semibold leading-snug text-white md:text-[15px]">
            {displayTheme}
          </p>
        </div>

        <div className="pointer-events-none absolute inset-x-0 bottom-0 z-20 flex justify-center px-4 md:px-6">
          <form
            className="pointer-events-auto flex w-full max-w-[1400px] translate-y-1/2 flex-col gap-2 rounded-ss border border-slate-200/90 bg-white p-1.5 shadow-lg sm:flex-row sm:items-stretch sm:gap-2 sm:p-1.5"
            onSubmit={(e) => {
              e.preventDefault();
              onSubmit();
            }}
          >
            <div className="flex min-h-[46px] flex-1 items-center px-3 sm:min-h-[48px]">
              <label htmlFor="refine-search" className="sr-only">
                Search or refine
              </label>
              <input
                id="refine-search"
                type="text"
                value={refineValue}
                onChange={(e) => onRefineChange(e.target.value)}
                placeholder={refinePlaceholder}
                disabled={loading || disabled}
                className="min-w-0 flex-1 border-0 bg-transparent py-2 text-sm font-medium text-ss-navy outline-none placeholder:font-normal placeholder:text-slate-400 disabled:opacity-50"
              />
            </div>
            <button
              type="submit"
              className="rounded-ss bg-ss-accent px-8 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-ss-accent-hover disabled:opacity-50 sm:shrink-0 sm:px-10"
              disabled={loading || disabled}
            >
              Search
            </button>
          </form>
        </div>
      </div>

      {/* Reserve vertical space for the half of the search bar that sits over the results canvas */}
      <div className="pt-8 md:pt-9" aria-hidden />
    </div>
  );
}
