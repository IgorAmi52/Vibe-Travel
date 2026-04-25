import type {
  AccommodationResult,
  FlightResult,
  PackageCardViewModel,
  PackageResultV0,
} from "./types";

function slugId(flight: FlightResult, accommodation: AccommodationResult, index: number) {
  return `${accommodation.name}-${flight.destinationCode}-${index}`
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

/** Derive 0–2 fallback tags when server sends only flight + accommodation */
function heuristicTags(flight: FlightResult, accommodation: AccommodationResult): string[] {
  const tags: string[] = [];
  if (accommodation.breakfastIncluded) tags.push("Breakfast included");
  tags.push(`${flight.destinationCity}`);
  return tags.slice(0, 2);
}

export function toPackageCardViewModels(
  results: PackageResultV0[],
  options: {
    explicitTagsPerCard?: string[][];
  } = {},
): PackageCardViewModel[] {
  return results.map((row, index) => {
    const explicit = options.explicitTagsPerCard?.[index];
    const tags =
      explicit && explicit.length > 0
        ? explicit
        : heuristicTags(row.flight, row.accommodation);
    return {
      id: slugId(row.flight, row.accommodation, index),
      tags,
      flight: row.flight,
      accommodation: row.accommodation,
    };
  });
}
