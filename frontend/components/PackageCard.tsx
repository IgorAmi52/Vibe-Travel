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
  const perPerson = flight.pricePerPerson + accommodation.pricePerPerson;

  return (
    <article className="overflow-hidden rounded-ss border border-slate-300/90 bg-white shadow-card transition-shadow duration-200 hover:shadow-card-hover">
      <div className="flex flex-col md:flex-row">
        <div className="relative h-52 w-full shrink-0 overflow-hidden md:h-auto md:w-[280px] lg:w-[320px]">
          <Image
            src={accommodation.imageUrl}
            alt=""
            fill
            className="object-cover"
            sizes="(max-width: 768px) 100vw, 320px"
          />
        </div>
        <div className="flex min-w-0 flex-1 flex-col gap-3 border-slate-200 p-4 md:border-r md:p-5">
          <div>
            <h2 className="text-lg font-bold tracking-tight text-ss-navy md:text-[1.15rem]">
              {accommodation.name}
            </h2>
            <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-slate-600">
              <span className="font-medium text-amber-500">
                {`${accommodation.starRating}★`}
              </span>
              <a
                href="#"
                className="font-semibold text-ss-accent underline decoration-ss-accent/40 underline-offset-2 hover:text-ss-accent-hover"
              >
                {accommodation.locationLabel}
              </a>
              <span className="font-bold text-ss-navy">
                {accommodation.reviewScore}/5{" "}
                <span className="font-semibold text-emerald-600">
                  {accommodation.reviewLabel}
                </span>
              </span>
            </div>
            {tags.length > 0 ? (
              <ul className="mt-2 flex flex-wrap gap-2">
                {tags.map((t) => (
                  <li
                    key={t}
                    className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-xs font-semibold text-ss-navy"
                  >
                    {t}
                  </li>
                ))}
              </ul>
            ) : null}
            <ul className="mt-3 space-y-1 text-sm text-slate-800">
              {accommodation.sellingPoints.map((p) => (
                <li key={p} className="flex items-center gap-2">
                  <span className="text-emerald-600" aria-hidden>
                    ✓
                  </span>
                  {p}
                </li>
              ))}
            </ul>
          </div>
          <div className="space-y-2 border-t border-slate-200 pt-3 text-sm">
            <FlightRow label="Outbound" leg={flight.outbound} />
            <FlightRow label="Return" leg={flight.inbound} />
          </div>
        </div>
        <div className="flex w-full flex-col justify-between bg-white p-4 md:w-56 lg:w-64">
          <div className="space-y-1 text-sm">
            {accommodation.breakfastIncluded ? (
              <p className="font-medium text-slate-800">Breakfast included</p>
            ) : null}
            <p className="text-xs text-slate-500">
              {accommodation.nights} nights · Flight + stay
            </p>
          </div>
          <div className="mt-4">
            <p className="text-[1.65rem] font-bold leading-tight text-ss-navy">
              {formatMoney(perPerson, flight.currency)}
              <span className="ml-1 text-base font-normal text-slate-600">per person</span>
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Total {formatMoney(totalPkg, flight.currency)} · indicative
            </p>
            <p className="mt-2 text-xs font-semibold text-slate-600">
              {accommodation.providerName}
            </p>
            <button
              type="button"
              className="mt-4 w-full rounded-ss bg-ss-navy py-3 text-sm font-bold text-white shadow-sm transition hover:bg-ss-navy-light"
            >
              Go to site
            </button>
          </div>
        </div>
      </div>
      {rankLabel ? (
        <div className="border-t border-slate-200 bg-slate-50 px-4 py-2 text-xs font-medium text-slate-700">
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
    <div className="flex flex-wrap items-center gap-2 text-slate-800">
      <span className="text-[11px] font-bold uppercase tracking-wide text-slate-500">
        {label}
      </span>
      <span className="rounded border border-slate-200 bg-white px-1 py-0.5 text-[10px] font-bold text-ss-navy">
        {leg.airlineCode}
      </span>
      <span className="font-medium">
        {leg.depTime} {leg.depCode} – {leg.arrTime} {leg.arrCode}
      </span>
      <span className="text-slate-500">· {leg.airline}</span>
      <span className="text-slate-500">· {leg.stopsLabel}</span>
    </div>
  );
}
