"use client";

type SearchSummaryBarProps = {
  displayTheme: string;
  tripFactsLine: string;
  intentChips: string[];
  onRemoveChip: (chip: string) => void;
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
  refinePlaceholder,
  refineValue,
  onRefineChange,
  onSubmit,
  loading,
  disabled,
}: SearchSummaryBarProps) {
  return (
    <div className="bg-ss-navy-light text-white">
      <div className="mx-auto max-w-[1400px] px-4 py-4 md:px-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:gap-4">
          <button
            type="button"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-ss-accent text-white"
            aria-label="Search"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </button>
          <div className="min-w-0 flex-1 space-y-2">
            <p className="text-base font-medium leading-snug md:text-lg">
              {displayTheme}
            </p>
            {tripFactsLine ? (
              <p className="text-sm text-white/80">{tripFactsLine}</p>
            ) : null}
            {intentChips.length > 0 ? (
              <div className="flex flex-wrap gap-2 pt-1">
                {intentChips.map((chip) => (
                  <button
                    key={chip}
                    type="button"
                    onClick={() => onRemoveChip(chip)}
                    disabled={loading || disabled}
                    className="inline-flex items-center gap-1 rounded-full border border-white/35 bg-white/10 px-3 py-1 text-xs font-medium text-white hover:bg-white/15 disabled:opacity-50"
                  >
                    {chip}
                    <span className="text-white/70" aria-hidden>
                      ×
                    </span>
                    <span className="sr-only">Remove {chip}</span>
                  </button>
                ))}
              </div>
            ) : null}
            <form
              className="pt-2"
              onSubmit={(e) => {
                e.preventDefault();
                onSubmit();
              }}
            >
              <label htmlFor="refine-search" className="sr-only">
                Refine your search
              </label>
              <input
                id="refine-search"
                type="text"
                value={refineValue}
                onChange={(e) => onRefineChange(e.target.value)}
                placeholder={refinePlaceholder}
                disabled={loading || disabled}
                className="w-full rounded border border-white/25 bg-white/10 px-4 py-2.5 text-sm text-white placeholder:text-white/50 outline-none ring-ss-accent focus:ring-2 disabled:opacity-50"
              />
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
