import type { PackageCardViewModel } from "@/lib/types";
import { FilterSidebar } from "./FilterSidebar";
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
    <div className="mx-auto max-w-[1400px] px-4 py-6 md:px-6">
      <div className="flex flex-col gap-6 lg:flex-row lg:gap-8">
        <FilterSidebar />
        <div className="min-w-0 flex-1">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2 text-sm">
            <p className="font-medium text-ss-navy">
              {loading ? "…" : `${packages.length} results`}
            </p>
            <p className="text-neutral-500">Additional baggage fees may apply</p>
          </div>
          {loading ? (
            <ResultsLoadingState statusMessage={statusMessage} />
          ) : packages.length === 0 ? (
            <div className="rounded-lg border border-dashed border-neutral-300 bg-neutral-50 px-6 py-16 text-center text-neutral-600">
              <p className="text-lg font-medium text-ss-navy">No packages yet</p>
              <p className="mt-2 text-sm">
                Describe your trip above to see flight + stay ideas tailored to your
                vibe.
              </p>
            </div>
          ) : (
            <ul className="space-y-4">
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
      </div>
    </div>
  );
}
