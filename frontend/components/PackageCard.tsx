import Image from "next/image";
import type { PackageCardViewModel } from "@/lib/types";

type PackageCardProps = {
  pkg: PackageCardViewModel;
  rankLabel?: string;
};

function formatMoney(n: number, currency: string) {
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(n);
  } catch {
    return `${n} ${currency}`;
  }
}

export function PackageCard({ pkg, rankLabel }: PackageCardProps) {
  const { flight, accommodation, tags } = pkg;
  const totalPkg = flight.totalPrice + accommodation.totalPrice;

  return (
    <article className="overflow-hidden rounded-lg border border-neutral-200 bg-white shadow-sm">
      <div className="flex flex-col md:flex-row">
        <div className="relative h-48 w-full shrink-0 md:h-auto md:w-[280px] lg:w-[320px]">
          <Image
            src={accommodation.imageUrl}
            alt=""
            fill
            className="object-cover"
            sizes="(max-width: 768px) 100vw, 320px"
          />
        </div>
        <div className="flex min-w-0 flex-1 flex-col gap-3 p-4 md:p-5">
          <div>
            <h2 className="text-lg font-semibold text-neutral-900">
              {accommodation.name}
            </h2>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-neutral-600">
              <span>{`${accommodation.starRating}★`}</span>
              <a href="#" className="text-ss-accent hover:underline">
                {accommodation.locationLabel}
              </a>
              <span className="font-medium text-neutral-800">
                {accommodation.reviewScore}/5 {accommodation.reviewLabel}
              </span>
            </div>
            {tags.length > 0 ? (
              <ul className="mt-2 flex flex-wrap gap-2">
                {tags.map((t) => (
                  <li
                    key={t}
                    className="rounded-full border border-ss-accent/30 bg-ss-accent/5 px-2.5 py-0.5 text-xs font-medium text-ss-navy"
                  >
                    {t}
                  </li>
                ))}
              </ul>
            ) : null}
            <ul className="mt-2 space-y-1 text-sm text-neutral-700">
              {accommodation.sellingPoints.map((p) => (
                <li key={p} className="flex items-center gap-2">
                  <span className="text-green-600" aria-hidden>
                    ✓
                  </span>
                  {p}
                </li>
              ))}
            </ul>
          </div>
          <div className="space-y-2 border-t border-neutral-100 pt-3 text-sm">
            <FlightRow label="Outbound" leg={flight.outbound} />
            <FlightRow label="Return" leg={flight.inbound} />
          </div>
        </div>
        <div className="flex flex-col justify-between border-t border-neutral-100 p-4 md:w-56 md:border-l md:border-t-0 lg:w-64">
          <div className="space-y-1 text-sm">
            {accommodation.breakfastIncluded ? (
              <p className="text-neutral-700">Breakfast included</p>
            ) : null}
            <p className="text-xs text-neutral-500">
              {accommodation.nights} nights · Flight + stay
            </p>
          </div>
          <div className="mt-4">
            <p className="text-2xl font-bold text-ss-navy">
              {formatMoney(flight.pricePerPerson + accommodation.pricePerPerson, flight.currency)}{" "}
              <span className="text-sm font-normal text-neutral-600">per person</span>
            </p>
            <p className="text-xs text-neutral-500">
              Total {formatMoney(totalPkg, flight.currency)} · indicative
            </p>
            <p className="mt-2 text-xs font-medium text-neutral-600">
              via {accommodation.providerName}
            </p>
            <button
              type="button"
              className="mt-4 w-full rounded bg-ss-navy py-3 text-sm font-semibold text-white hover:bg-ss-navy/90"
            >
              Go to site
            </button>
          </div>
        </div>
      </div>
      {rankLabel ? (
        <div className="border-t border-neutral-100 bg-neutral-50 px-4 py-2 text-xs text-neutral-600">
          {rankLabel}
        </div>
      ) : null}
    </article>
  );
}

function FlightRow({
  label,
  leg,
}: {
  label: string;
  leg: PackageCardViewModel["flight"]["outbound"];
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-neutral-800">
      <span className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
        {label}
      </span>
      <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-[10px] font-bold">
        {leg.airlineCode}
      </span>
      <span>
        {leg.depTime} {leg.depCode} – {leg.arrTime} {leg.arrCode}
      </span>
      <span className="text-neutral-500">· {leg.airline}</span>
      <span className="text-neutral-500">· {leg.stopsLabel}</span>
    </div>
  );
}
