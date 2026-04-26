"use client";

type SearchSummaryBarProps = {
  displayTheme: string;
  tripFactsLine?: string;
  intentChips?: string[];
  onRemoveChip?: (chip: string) => void;
  clarificationPrompt?: string | null;
  refinePlaceholder: string;
  refineValue: string;
  onRefineChange: (value: string) => void;
  onSubmit: () => void;
  loading: boolean;
  disabled?: boolean;
};

export function SearchSummaryBar({
  displayTheme,
  tripFactsLine,
  intentChips,
  onRemoveChip,
  clarificationPrompt,
  refinePlaceholder,
  refineValue,
  onRefineChange,
  onSubmit,
  loading,
  disabled,
}: SearchSummaryBarProps) {
  return (
    <div>
      <div className="relative z-30 bg-gradient-to-b from-ss-navy via-ss-navy to-ss-navy-light pb-8 md:pb-9">
        <div className="mx-auto max-w-[1400px] px-4 pb-2 pt-0.5 md:px-6 md:pb-2.5">
          <div className="flex items-center gap-2.5">
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

          {tripFactsLine && (
            <p className="mt-1 pl-[26px] text-xs text-white/70">
              {tripFactsLine}
            </p>
          )}

          {intentChips && intentChips.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5 pl-[26px]">
              {intentChips.map((chip) => (
                <span
                  key={chip}
                  className="inline-flex items-center gap-1 rounded-full bg-white/15 px-2.5 py-0.5 text-xs font-medium text-white"
                >
                  {chip}
                  {onRemoveChip && (
                    <button
                      type="button"
                      onClick={() => onRemoveChip(chip)}
                      className="ml-0.5 rounded-full p-0.5 transition hover:bg-white/20"
                      aria-label={`Remove ${chip}`}
                    >
                      <svg className="h-3 w-3" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M3 3l6 6M9 3l-6 6" />
                      </svg>
                    </button>
                  )}
                </span>
              ))}
            </div>
          )}
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

      {clarificationPrompt && (
        <div className="mx-auto max-w-[1400px] px-4 md:px-6">
          <div className="mt-4 rounded-ss border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            {clarificationPrompt}
          </div>
        </div>
      )}

      <div className="pt-8 md:pt-9" aria-hidden />
    </div>
  );
}
