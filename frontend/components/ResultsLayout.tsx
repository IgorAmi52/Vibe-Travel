import type { PackageCardViewModel } from "@/lib/types";
import { PackageCard } from "./PackageCard";
import { ResultsLoadingState } from "./ResultsLoadingState";

type ResultsLayoutProps = {
  packages: PackageCardViewModel[];
  loading: boolean;
  statusMessage: string;
};

export function ResultsLayout({
  packages,
  loading,
  statusMessage,
}: ResultsLayoutProps) {
  return (
    <div className="mx-auto max-w-[1100px] px-4 pb-6 pt-2 md:px-6 md:pb-8 md:pt-3">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-bold text-ss-navy">
          {loading ? "…" : `${packages.length} results`}
        </p>
        <p className="text-xs text-slate-500">Additional baggage fees may apply</p>
      </div>
      {loading ? (
        <ResultsLoadingState statusMessage={statusMessage} />
      ) : packages.length === 0 ? (
        <div className="rounded-ss border border-dashed border-slate-300 bg-white px-6 py-14 text-center shadow-sm">
          <p className="text-lg font-bold text-ss-navy">No packages yet</p>
          <p className="mt-2 text-sm text-slate-600">
            Use Search above to describe your trip and see flight + stay bundles.
          </p>
        </div>
      ) : (
        <ul className="space-y-3">
          {packages.map((pkg, i) => (
            <li key={pkg.id}>
              <PackageCard
                pkg={pkg}
                rankLabel={
                  i === 0 ? "Cheapest comparable bundle in this list" : undefined
                }
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
