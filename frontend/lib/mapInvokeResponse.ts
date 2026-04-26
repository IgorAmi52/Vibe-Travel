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
    return {
      depTime: formatTime(leg.datetime ?? fallbackDatetime),
      arrTime: formatTime(leg.datetime ?? fallbackDatetime),
      depCode: orig.iata,
      arrCode: dest.iata,
      airline: airlineName,
      airlineCode,
      stopsLabel: leg.is_direct ?? isDirect ? "Direct" : "1+ stops",
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

  return {
    name: h.name,
    starRating: h.star_rating ?? 0,
    reviewScore: scaledRating,
    reviewLabel: reviewLabel(rawRating),
    locationLabel: item.destination.place ?? "",
    nights: nightsBetween(
      tripIntent?.start_date ?? null,
      tripIntent?.end_date ?? null,
    ),
    breakfastIncluded: amenities.some((a) =>
      a.toLowerCase().includes("breakfast"),
    ),
    pricePerPerson: personCount > 0 ? totalPrice / personCount : totalPrice,
    totalPrice,
    currency,
    providerName: "Booking.com",
    imageUrl: h.images?.[0] ?? FALLBACK_IMAGE,
    sellingPoints: amenities.slice(0, 3),
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
  return chips;
}

export function mapInvokeToSnapshot(response: InvokeResponse): SessionSnapshot {
  const state = response.state;
  const intent = state.trip_intent;
  const personCount = state.person_count || 1;

  let packages: PackageCardViewModel[];
  const grouped = state.grouped_results ?? [];

  if (grouped.length > 0) {
    packages = grouped.map((item) =>
      mapGroupedResult(item, intent, personCount),
    );
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
