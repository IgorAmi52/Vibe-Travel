/**
 * v0 API: each result is only `flight` + `accommodation`.
 * Theme, tags, and chips come from mapper heuristics or mock enrichment.
 */

export interface FlightLeg {
  depTime: string;
  arrTime: string;
  depCode: string;
  arrCode: string;
  airline: string;
  airlineCode: string;
  stopsLabel: string;
  dateLabel: string;
}

export interface FlightResult {
  originCity: string;
  originCode: string;
  destinationCity: string;
  destinationCode: string;
  outbound: FlightLeg;
  inbound: FlightLeg;
  pricePerPerson: number;
  totalPrice: number;
  currency: string;
  dealUrl: string;
}

export interface AccommodationResult {
  name: string;
  starRating: number;
  reviewScore: number;
  reviewLabel: string;
  locationLabel: string;
  nights: number;
  breakfastIncluded: boolean;
  pricePerPerson: number;
  totalPrice: number;
  currency: string;
  providerName: string;
  imageUrl: string;
  sellingPoints: string[];
  dealUrl: string;
}

export interface PackageResultV0 {
  flight: FlightResult;
  accommodation: AccommodationResult;
}

/** UI model for a single package card */
export interface PackageCardViewModel {
  id: string;
  tags: string[];
  flight: FlightResult;
  accommodation: AccommodationResult;
  alternativeFlights?: FlightResult[];
}

export interface SessionSnapshot {
  sessionId: string;
  displayTheme: string;
  tripFactsLine: string;
  intentChips: string[];
  packages: PackageCardViewModel[];
  needsClarification?: boolean;
  clarificationPrompt?: string | null;
}

/* ------------------------------------------------------------------ */
/*  Backend /invoke response types                                     */
/* ------------------------------------------------------------------ */

export interface InvokeTripIntent {
  places: string[];
  countries: string[];
  start_date: string | null;
  end_date: string | null;
  budget: number | null;
  vibe: string | string[] | null;
  person_count: number | null;
}

export interface InvokeAirport {
  iata: string;
  name: string;
}

export interface InvokeCarrier {
  id?: string;
  name?: string;
  iata?: string;
  display_code?: string;
}

export interface InvokeFlightLeg {
  price?: { amount: number | null; unit?: string };
  airports?: { origin: InvokeAirport; destination: InvokeAirport };
  carrier?: string | InvokeCarrier | null;
  datetime?: string | null;
  is_direct?: boolean;
}

export interface InvokeFlight {
  price?: { amount: number | null; unit?: string };
  airports?: {
    origin: InvokeAirport;
    destination: InvokeAirport;
  };
  outbound_datetime?: string | null;
  inbound_datetime?: string | null;
  is_direct?: boolean;
  outbound?: InvokeFlightLeg;
  inbound?: InvokeFlightLeg;
}

export interface InvokeHotel {
  hotel_id?: string;
  name: string;
  price?: { amount: number | null; currency?: string };
  description?: string;
  amenities?: string[];
  star_rating?: number;
  guest_rating?: number;
  accommodation_type?: string;
  images?: string[];
  scores?: Record<string, number>;
}

export interface InvokePriceSummary {
  flight_amount: number | null;
  hotel_amount: number | null;
  total_amount: number | null;
  currency: string | null;
  budget: number | null;
}

export interface InvokeGroupedResult {
  option_id: string;
  destination: { place: string | null; iata: string | null };
  flight: InvokeFlight;
  hotel: InvokeHotel;
  within_budget: boolean;
  price_summary: InvokePriceSummary;
}

export interface InvokeFlightResult {
  airports: { origin: InvokeAirport; destination: InvokeAirport };
  outbound_datetime?: string | null;
  inbound_datetime?: string | null;
  price: { amount: number | null; unit?: string };
  is_direct?: boolean;
}

export interface InvokeState {
  user_query: string;
  source: string;
  status: string;
  trip_intent?: InvokeTripIntent;
  budget?: number | null;
  origin_iata?: string | null;
  destination_place?: string | null;
  destination_iata?: string | null;
  flight_results: InvokeFlightResult[];
  hotel_results: unknown[];
  grouped_results: InvokeGroupedResult[];
  person_count: number;
  next_step?: string | null;
  errors: string[];
  needs_clarification: boolean;
  clarification_prompt?: string | null;
  iteration: number;
}

export interface InvokeResponse {
  state: InvokeState;
  needs_clarification?: boolean;
  clarification_prompt?: string | null;
}
