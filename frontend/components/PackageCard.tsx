import Image from "next/image";
import { formatMoney } from "@/lib/formatMoney";
import type { FlightLeg, PackageCardViewModel } from "@/lib/types";

type PackageCardProps = {
  pkg: PackageCardViewModel;
  rankLabel?: string;
};

export function PackageCard({ pkg, rankLabel }: PackageCardProps) {
  const { flight, accommodation, tags } = pkg;
  const totalPkg = flight.totalPrice + accommodation.totalPrice;
  const perPerson = flight.pricePerPerson + accommodation.pricePerPerson;

  return (
    <article className="group overflow-hidden rounded-ss border border-slate-200 bg-white shadow-sm transition-shadow duration-200 hover:shadow-md">
      <div className="flex flex-col sm:flex-row">
        {/* Image */}
        <div className="relative h-44 w-full shrink-0 overflow-hidden sm:h-auto sm:w-[200px]">
          <Image
            src={accommodation.imageUrl}
            alt={accommodation.name}
            fill
            className="object-cover transition-transform duration-300 group-hover:scale-105"
            sizes="(max-width: 640px) 100vw, 200px"
          />
          {rankLabel && (
            <span className="absolute left-2 top-2 rounded bg-ss-accent/90 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white shadow-sm">
              Best value
            </span>
          )}
        </div>

        {/* Details */}
        <div className="flex min-w-0 flex-1 flex-col p-3 sm:p-4">
          {/* Hotel header row */}
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 className="truncate text-[15px] font-bold leading-tight text-ss-navy">
                {accommodation.name}
              </h2>
              <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-slate-500">
                {accommodation.starRating > 0 && (
                  <span className="font-medium text-amber-500">
                    {accommodation.starRating}★
                  </span>
                )}
                {accommodation.locationLabel && (
                  <span className="font-semibold text-ss-accent">
                    {accommodation.locationLabel}
                  </span>
                )}
                {accommodation.reviewScore > 0 && (
                  <span className="font-bold text-ss-navy">
                    {accommodation.reviewScore}/5{" "}
                    <span className="font-semibold text-emerald-600">
                      {accommodation.reviewLabel}
                    </span>
                  </span>
                )}
              </div>
            </div>

            {/* Price block - right aligned */}
            <div className="shrink-0 text-right">
              <p className="text-xl font-bold leading-tight text-ss-navy">
                {formatMoney(perPerson, flight.currency)}
              </p>
              <p className="text-[11px] text-slate-500">per person</p>
              <p className="text-[10px] text-slate-400">
                Total {formatMoney(totalPkg, flight.currency)}
              </p>
            </div>
          </div>

          {/* Tags + selling points in one row */}
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            {tags.map((t) => (
              <span
                key={t}
                className="rounded-full border border-slate-200 bg-slate-50 px-2 py-px text-[11px] font-medium text-ss-navy"
              >
                {t}
              </span>
            ))}
            {accommodation.breakfastIncluded && (
              <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-px text-[11px] font-medium text-emerald-700">
                Breakfast included
              </span>
            )}
            {accommodation.sellingPoints.slice(0, 2).map((p) => (
              <span key={p} className="text-[11px] text-slate-500">
                <span className="text-emerald-500">✓</span> {p}
              </span>
            ))}
          </div>

          {/* Flights - compact inline */}
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 border-t border-slate-100 pt-2 text-[12px] text-slate-600">
            <CompactFlight label="Out" leg={flight.outbound} />
            <CompactFlight label="Ret" leg={flight.inbound} />
            <span className="text-slate-400">
              {accommodation.nights > 0
                ? `${accommodation.nights} nights`
                : "Dates TBC"}{" "}
              · {accommodation.providerName || "Flight + stay"}
            </span>
          </div>
        </div>

        {/* CTA strip */}
        <div className="flex items-center border-t border-slate-100 p-3 sm:w-[120px] sm:border-l sm:border-t-0">
          <button
            type="button"
            className="w-full rounded-ss bg-ss-navy py-2.5 text-xs font-bold text-white shadow-sm transition hover:bg-ss-navy-light"
          >
            View deal
          </button>
        </div>
      </div>
    </article>
  );
}

function CompactFlight({ label, leg }: { label: string; leg: FlightLeg }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span className="font-bold uppercase text-slate-400">{label}</span>
      {leg.airlineCode && (
        <span className="rounded border border-slate-200 px-1 py-px text-[10px] font-bold text-ss-navy">
          {leg.airlineCode}
        </span>
      )}
      <span className="font-medium text-slate-700">
        {leg.depCode}→{leg.arrCode}
      </span>
      {leg.stopsLabel && (
        <span className="text-slate-400">{leg.stopsLabel}</span>
      )}
    </span>
  );
}
