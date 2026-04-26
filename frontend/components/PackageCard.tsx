import Image from "next/image";
import { formatMoney } from "@/lib/formatMoney";
import type { FlightLeg, FlightResult, PackageCardViewModel } from "@/lib/types";

type PackageCardProps = {
  pkg: PackageCardViewModel;
  rankLabel?: string;
};

export function PackageCard({ pkg, rankLabel }: PackageCardProps) {
  const { flight, accommodation, tags, alternativeFlights } = pkg;
  const bestPP = flight.pricePerPerson + accommodation.pricePerPerson;
  const bestTotal = flight.totalPrice + accommodation.totalPrice;

  const stayLabel = [
    accommodation.nights > 0 ? `${accommodation.nights} nights` : null,
    accommodation.providerName || null,
  ]
    .filter(Boolean)
    .join(" · ");

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

        {/* Right content */}
        <div className="flex min-w-0 flex-1 flex-col">
          {/* Hotel info + price */}
          <div className="flex items-start justify-between gap-3 p-3 pb-2 sm:p-4 sm:pb-2">
            <div className="min-w-0">
              <h2 className="truncate text-[15px] font-bold leading-tight text-ss-navy">
                {accommodation.dealUrl ? (
                  <a href={accommodation.dealUrl} target="_blank" rel="noopener noreferrer" className="hover:underline">
                    {accommodation.name}
                  </a>
                ) : (
                  accommodation.name
                )}
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
                {stayLabel && (
                  <span className="text-slate-400">{stayLabel}</span>
                )}
              </div>
            </div>

            <div className="shrink-0 text-right">
              <p className="text-lg font-bold leading-tight text-ss-navy">
                from {formatMoney(bestPP, flight.currency)}
              </p>
              <p className="text-[10px] text-slate-400">
                pp · Total {formatMoney(bestTotal, flight.currency)}
              </p>
            </div>
          </div>

          {/* Tags + selling points */}
          <div className="flex flex-wrap items-center gap-1.5 px-3 pb-2 sm:px-4">
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

          {/* Flight options — uniform rows */}
          <div className="border-t border-slate-100">
            <FlightRow flight={flight} highlight />
            {alternativeFlights?.map((alt, i) => (
              <FlightRow key={`alt-${i}`} flight={alt} />
            ))}
          </div>
        </div>
      </div>
    </article>
  );
}

function FlightRow({
  flight,
  highlight,
}: {
  flight: FlightResult;
  highlight?: boolean;
}) {
  return (
    <div
      className={`flex items-center gap-x-3 px-3 py-1.5 text-[12px] sm:px-4 ${
        highlight
          ? "bg-slate-50/60 text-slate-700"
          : "border-t border-dashed border-slate-100 text-slate-500"
      }`}
    >
      <CompactFlight leg={flight.outbound} />
      <CompactFlight leg={flight.inbound} />
      <span className="ml-auto whitespace-nowrap font-bold text-ss-navy">
        {formatMoney(flight.pricePerPerson, flight.currency)}
        <span className="ml-0.5 font-normal text-slate-400">pp</span>
      </span>
      <span className="hidden whitespace-nowrap text-[10px] text-slate-400 sm:inline">
        Total {formatMoney(flight.totalPrice, flight.currency)}
      </span>
      <a
        href={flight.dealUrl}
        target="_blank"
        rel="noopener noreferrer"
        className={`shrink-0 rounded-ss px-3 py-1 text-center text-[11px] font-bold no-underline transition ${
          highlight
            ? "bg-ss-navy text-white shadow-sm hover:bg-ss-navy-light"
            : "border border-ss-navy text-ss-navy hover:bg-ss-navy hover:text-white"
        }`}
      >
        View deal
      </a>
    </div>
  );
}

function CompactFlight({ leg }: { leg: FlightLeg }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span className="w-[70px] text-[11px] font-semibold text-slate-500">
        {leg.dateLabel || "TBC"}
      </span>
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
