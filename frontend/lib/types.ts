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
}

export interface SessionSnapshot {
  sessionId: string;
  displayTheme: string;
  tripFactsLine: string;
  intentChips: string[];
  packages: PackageCardViewModel[];
}
