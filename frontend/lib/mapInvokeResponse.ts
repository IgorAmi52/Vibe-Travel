import type {
  AccommodationResult,
  FlightLeg,
  FlightResult,
  InvokeFlightLeg,
  InvokeFlightResult,
  InvokeGroupedResult,
  InvokeResponse,
  InvokeState,
  InvokeTripIntent,
  PackageCardViewModel,
  SessionSnapshot,
} from "./types";

const FALLBACK_IMAGE =
  "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&q=80";

function buildSkyscannerUrl(
  originIata: string,
  destIata: string,
  outDate: string | null | undefined,
  inDate: string | null | undefined,
  adults: number = 1,
): string {
  const o = originIata.toLowerCase();
  const d = destIata.toLowerCase();
  const dep = outDate ? toYYMMDD(outDate) : "";
  const ret = inDate ? toYYMMDD(inDate) : "";
  const params = new URLSearchParams();
  // Skyscanner's web search reads `adultsv2` (the newer param). `adults`
  // alone gets ignored on /transport/flights/, which is why deep-linked
  // results were always shown for one traveller.
  const safeAdults = Math.max(1, Math.floor(adults));
  params.set("adultsv2", String(safeAdults));
  params.set("adults", String(safeAdults));
  params.set("children", "0");
  params.set("childrenv2", "");
  params.set("infants", "0");
  params.set("cabinclass", "economy");
  params.set("rtn", dep && ret ? "1" : "0");
  const qs = params.toString();
  const suffix = qs ? `?${qs}` : "";
  if (dep && ret) {
    return `https://www.skyscanner.net/transport/flights/${o}/${d}/${dep}/${ret}/${suffix}`;
  }
  if (dep) {
    return `https://www.skyscanner.net/transport/flights/${o}/${d}/${dep}/${suffix}`;
  }
  return `https://www.skyscanner.net/transport/flights/${o}/${d}/${suffix}`;
}

function buildBookingUrl(
  hotelName: string,
  hotelId: string | null | undefined,
  checkin: string | null | undefined,
  checkout: string | null | undefined,
  adults: number = 1,
): string {
  const params = new URLSearchParams();
  params.set("ss", hotelName);
  // Disambiguate to the exact property: Booking.com routes
  // dest_type=hotel + dest_id=<id> straight to that hotel's page, so we
  // never land on a wrong-name match or a generic results listing.
  if (hotelId) {
    params.set("dest_type", "hotel");
    params.set("dest_id", hotelId);
  }
  if (checkin) params.set("checkin", toYYYYMMDD(checkin));
  if (checkout) params.set("checkout", toYYYYMMDD(checkout));
  if (adults > 1) params.set("group_adults", String(adults));
  params.set("no_rooms", "1");
  return `https://www.booking.com/searchresults.html?${params.toString()}`;
}

function toYYMMDD(dateStr: string): string {
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr.replace(/-/g, "").slice(2);
  const y = String(d.getFullYear()).slice(2);
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}${m}${day}`;
}

function toYYYYMMDD(dateStr: string): string {
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toISOString().slice(0, 10);
}

function normalizeCurrency(raw: string | null | undefined): string {
  if (!raw) return "EUR";
  if (raw.startsWith("PRICE_UNIT")) return "EUR";
  return raw;
}

function reviewLabel(score: number): string {
  if (score >= 9) return "Wonderful";
  if (score >= 8) return "Excellent";
  if (score >= 7) return "Very Good";
  if (score >= 6) return "Good";
  return "Pleasant";
}

function nightsBetween(start: string | null, end: string | null): number {
  if (!start || !end) return 1;
  const ms = new Date(end).getTime() - new Date(start).getTime();
  const n = Math.round(ms / 86_400_000);
  return n > 0 ? n : 1;
}

function formatTime(datetime: string | null | undefined): string {
  if (!datetime) return "--:--";
  const d = new Date(datetime);
  if (isNaN(d.getTime())) return "--:--";
  return d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

function formatDateLabel(datetime: string | null | undefined): string {
  if (!datetime) return "";
  const d = new Date(datetime);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
}

function mapLeg(
  leg: InvokeFlightLeg | undefined,
  fallbackOrigin: { iata: string; name: string },
  fallbackDest: { iata: string; name: string },
  fallbackDatetime: string | null | undefined,
  isDirect: boolean,
): FlightLeg {
  if (leg) {
    const orig = leg.airports?.origin ?? fallbackOrigin;
    const dest = leg.airports?.destination ?? fallbackDest;
    const carrier = leg.carrier;
    const airlineName = typeof carrier === "object" && carrier !== null
      ? (carrier as Record<string, string>).name ?? ""
      : String(carrier ?? "");
    const airlineCode = typeof carrier === "object" && carrier !== null
      ? (carrier as Record<string, string>).display_code ?? (carrier as Record<string, string>).iata ?? ""
      : String(carrier ?? "");
    const dt = leg.datetime ?? fallbackDatetime;
    return {
      depTime: formatTime(dt),
      arrTime: formatTime(dt),
      depCode: orig.iata,
      arrCode: dest.iata,
      airline: airlineName,
      airlineCode,
      stopsLabel: leg.is_direct ?? isDirect ? "Direct" : "1+ stops",
      dateLabel: formatDateLabel(dt),
    };
  }
  return {
    depTime: formatTime(fallbackDatetime),
    arrTime: formatTime(fallbackDatetime),
    depCode: fallbackOrigin.iata,
    arrCode: fallbackDest.iata,
    airline: "",
    airlineCode: "",
    stopsLabel: isDirect ? "Direct" : "1+ stops",
    dateLabel: formatDateLabel(fallbackDatetime),
  };
}

function mapFlight(
  item: InvokeGroupedResult,
  personCount: number,
): FlightResult {
  const f = item.flight;
  const origin = f.airports?.origin ?? { iata: "???", name: "Origin" };
  const dest = f.airports?.destination ?? { iata: "???", name: "Destination" };
  const totalPrice = item.price_summary.flight_amount ?? 0;
  const currency = normalizeCurrency(item.price_summary.currency);

  return {
    originCity: origin.name,
    originCode: origin.iata,
    destinationCity: dest.name,
    destinationCode: dest.iata,
    outbound: mapLeg(
      f.outbound,
      origin,
      dest,
      f.outbound_datetime,
      f.is_direct ?? true,
    ),
    inbound: mapLeg(
      f.inbound,
      dest,
      origin,
      f.inbound_datetime,
      f.is_direct ?? true,
    ),
    pricePerPerson: personCount > 0 ? totalPrice / personCount : totalPrice,
    totalPrice,
    currency,
    dealUrl: buildSkyscannerUrl(origin.iata, dest.iata, f.outbound_datetime, f.inbound_datetime, personCount),
  };
}

function mapAccommodation(
  item: InvokeGroupedResult,
  tripIntent: InvokeTripIntent | undefined,
  personCount: number,
): AccommodationResult {
  const h = item.hotel;
  const totalPrice = item.price_summary.hotel_amount ?? 0;
  const currency = normalizeCurrency(item.price_summary.currency);
  const amenities = h.amenities ?? [];

  const rawRating = h.guest_rating ?? 0;
  const scaledRating = rawRating > 5 ? Math.round((rawRating / 2) * 10) / 10 : rawRating;

  const checkin =
    tripIntent?.start_date ?? item.flight.outbound_datetime ?? null;
  const checkout =
    tripIntent?.end_date ?? item.flight.inbound_datetime ?? null;

  return {
    name: h.name,
    starRating: h.star_rating ?? 0,
    reviewScore: scaledRating,
    reviewLabel: reviewLabel(rawRating),
    locationLabel: item.destination.place ?? "",
    nights: nightsBetween(checkin, checkout),
    breakfastIncluded: amenities.some((a) =>
      a.toLowerCase().includes("breakfast"),
    ),
    pricePerPerson: personCount > 0 ? totalPrice / personCount : totalPrice,
    totalPrice,
    currency,
    providerName: "Booking.com",
    imageUrl: h.images?.[0] ?? FALLBACK_IMAGE,
    sellingPoints: amenities.slice(0, 3),
    dealUrl: buildBookingUrl(h.name, h.hotel_id, checkin, checkout, personCount),
  };
}

function mapGroupedResult(
  item: InvokeGroupedResult,
  tripIntent: InvokeTripIntent | undefined,
  personCount: number,
): PackageCardViewModel {
  const flight = mapFlight(item, personCount);
  const accommodation = mapAccommodation(item, tripIntent, personCount);

  const tags: string[] = [];
  if (item.destination.place) tags.push(item.destination.place);
  if (item.hotel.accommodation_type) tags.push(item.hotel.accommodation_type);

  return {
    id: item.option_id,
    tags,
    flight,
    accommodation,
  };
}

function mapFlightOnlyCard(
  fr: InvokeFlightResult,
  index: number,
  personCount: number,
): PackageCardViewModel {
  const origin = fr.airports.origin;
  const dest = fr.airports.destination;
  const totalPrice = fr.price.amount ?? 0;
  const currency = fr.price.unit ?? "EUR";

  const emptyLeg: FlightLeg = {
    depTime: formatTime(fr.outbound_datetime),
    arrTime: formatTime(fr.outbound_datetime),
    depCode: origin.iata,
    arrCode: dest.iata,
    airline: "",
    airlineCode: "",
    stopsLabel: fr.is_direct ? "Direct" : "1+ stops",
    dateLabel: formatDateLabel(fr.outbound_datetime),
  };

  const flight: FlightResult = {
    originCity: origin.name,
    originCode: origin.iata,
    destinationCity: dest.name,
    destinationCode: dest.iata,
    outbound: emptyLeg,
    inbound: { ...emptyLeg, depCode: dest.iata, arrCode: origin.iata },
    pricePerPerson: personCount > 0 ? totalPrice / personCount : totalPrice,
    totalPrice,
    currency,
    dealUrl: buildSkyscannerUrl(origin.iata, dest.iata, fr.outbound_datetime, null, personCount),
  };

  const accommodation: AccommodationResult = {
    name: `Flights to ${dest.name}`,
    starRating: 0,
    reviewScore: 0,
    reviewLabel: "",
    locationLabel: dest.name,
    nights: 0,
    breakfastIncluded: false,
    pricePerPerson: 0,
    totalPrice: 0,
    currency,
    providerName: "",
    imageUrl: FALLBACK_IMAGE,
    sellingPoints: ["Indicative flight price", "Add dates to see hotels"],
    dealUrl: "",
  };

  return {
    id: `flight-only-${index}`,
    tags: [dest.name, "Flights only"],
    flight,
    accommodation,
  };
}

function vibeText(vibe: string | string[] | null | undefined): string {
  if (!vibe) return "";
  if (Array.isArray(vibe)) return vibe.join(", ");
  return vibe;
}

function buildDisplayTheme(intent?: InvokeTripIntent): string {
  const parts: string[] = [];
  const v = vibeText(intent?.vibe);
  if (v) parts.push(v);
  if (intent?.places?.length) {
    parts.push(`in ${intent.places.join(", ")}`);
  }
  if (parts.length === 0) {
    return "Your next trip, matched to how you like to travel";
  }
  const raw = parts.join(" ");
  return raw.charAt(0).toUpperCase() + raw.slice(1);
}

function buildTripFactsLine(state: InvokeState): string {
  const parts: string[] = [];
  const intent = state.trip_intent;
  if (intent?.start_date && intent?.end_date) {
    parts.push(`${intent.start_date} → ${intent.end_date}`);
  }
  if (state.person_count > 1) {
    parts.push(`${state.person_count} travellers`);
  }
  if (intent?.budget) {
    parts.push(`Budget €${intent.budget}`);
  }
  return parts.length > 0
    ? parts.join(" · ")
    : "Select dates and party size when you continue to Skyscanner";
}

function buildIntentChips(intent?: InvokeTripIntent): string[] {
  if (!intent) return [];
  const chips: string[] = [];
  for (const place of intent.places ?? []) chips.push(place);
  for (const country of intent.countries ?? []) {
    if (!chips.includes(country)) chips.push(country);
  }
  const v = vibeText(intent.vibe);
  if (v) chips.push(v);
  if (intent.start_date && intent.end_date) {
    chips.push(`${intent.start_date} → ${intent.end_date}`);
  } else if (intent.start_date) {
    chips.push(`From ${intent.start_date}`);
  }
  if (intent.budget) chips.push(`€${intent.budget} budget`);
  if (intent.person_count && intent.person_count > 1) {
    chips.push(`${intent.person_count} travellers`);
  }
  return chips;
}

export function mapInvokeToSnapshot(response: InvokeResponse): SessionSnapshot {
  const state = response.state;
  const intent = state.trip_intent;
  const personCount = state.person_count || 1;

  let packages: PackageCardViewModel[];
  const grouped = state.grouped_results ?? [];

  if (grouped.length > 0) {
    const all = grouped.map((item) =>
      mapGroupedResult(item, intent, personCount),
    );
    const byHotel = new Map<string, PackageCardViewModel>();
    for (const pkg of all) {
      const key = pkg.accommodation.name;
      const existing = byHotel.get(key);
      if (!existing) {
        byHotel.set(key, pkg);
      } else {
        const existingTotal = existing.flight.totalPrice + existing.accommodation.totalPrice;
        const newTotal = pkg.flight.totalPrice + pkg.accommodation.totalPrice;
        if (!existing.alternativeFlights) existing.alternativeFlights = [];
        if (newTotal < existingTotal) {
          existing.alternativeFlights.push(existing.flight);
          existing.flight = pkg.flight;
        } else {
          existing.alternativeFlights.push(pkg.flight);
        }
      }
    }
    packages = [...byHotel.values()];
  } else if (state.flight_results?.length > 0) {
    packages = state.flight_results.map((fr, i) =>
      mapFlightOnlyCard(fr, i, personCount),
    );
  } else {
    packages = [];
  }

  let clarificationPrompt =
    response.clarification_prompt ?? state.clarification_prompt ?? null;

  if (
    !clarificationPrompt &&
    grouped.length === 0 &&
    state.flight_results?.length > 0
  ) {
    clarificationPrompt =
      "We found indicative flight prices! Add travel dates to your search (e.g. \"in August\" or \"10–14 Aug\") to see full flight + hotel packages.";
  }

  return {
    sessionId: "live",
    displayTheme: buildDisplayTheme(intent),
    tripFactsLine: buildTripFactsLine(state),
    intentChips: buildIntentChips(intent),
    packages,
    needsClarification: response.needs_clarification ?? state.needs_clarification,
    clarificationPrompt,
  };
}
