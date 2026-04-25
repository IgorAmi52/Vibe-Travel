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
      <div className="relative z-30 bg-ss-navy pb-12 md:pb-14">
        <div className="mx-auto flex max-w-[1400px] items-center gap-3 px-4 py-2.5 md:px-6 md:py-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-ss-accent shadow-sm">
            <svg
              className="h-4 w-4 text-white"
              fill="none"
              stroke="currentColor"
              strokeWidth={2.25}
              viewBox="0 0 24 24"
              aria-hidden
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
          <p className="min-w-0 flex-1 text-sm font-medium leading-snug text-white md:text-base">
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
      <div className="pt-12 md:pt-14" aria-hidden />
    </div>
  );
}
