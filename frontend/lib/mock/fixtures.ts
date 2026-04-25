import type { PackageResultV0 } from "../types";

/** Mock-only: paired with each row for demo UI */
export interface MockRowExtra {
  cardTags: string[];
}

export interface MockFixtureSet {
  displayTheme: string;
  tripFactsLine: string;
  intentChips: string[];
  rows: PackageResultV0[];
  extras: MockRowExtra[];
}

const imgHotel =
  "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800&q=80";

export const fixturePrimary: MockFixtureSet = {
  displayTheme: "Cultural city break · great food & direct-ish routes",
  tripFactsLine: "Barcelona (BCN) – Beijing • Thu, 30 Apr – Thu, 07 May • 2 travellers",
  intentChips: ["Culture", "Foodie", "Flexible stops"],
  extras: [
    {
      cardTags: ["Matches: Culture", "Hub airport access", "Flexible payments"],
    },
    {
      cardTags: ["Matches: Foodie", "Central district", "Book with deposit"],
    },
    {
      cardTags: ["Matches: Culture", "Great reviews", "Breakfast included"],
    },
  ],
  rows: [
    {
      flight: {
        originCity: "Barcelona",
        originCode: "BCN",
        destinationCity: "Beijing",
        destinationCode: "PEK",
        outbound: {
          depTime: "10:40",
          arrTime: "06:15+1",
          depCode: "BCN",
          arrCode: "PEK",
          airline: "Singapore Airlines",
          airlineCode: "SQ",
          stopsLabel: "1 stop · SIN",
        },
        inbound: {
          depTime: "00:30",
          arrTime: "07:05",
          depCode: "PEK",
          arrCode: "BCN",
          airline: "Singapore Airlines",
          airlineCode: "SQ",
          stopsLabel: "1 stop · SIN",
        },
        pricePerPerson: 4055,
        totalPrice: 8110,
        currency: "EUR",
      },
      accommodation: {
        name: "Wyndham Beijing North",
        starRating: 5,
        reviewScore: 4.7,
        reviewLabel: "Excellent",
        locationLabel: "Haidian · 8 km to centre",
        nights: 7,
        breakfastIncluded: true,
        pricePerPerson: 1820,
        totalPrice: 3640,
        currency: "EUR",
        providerName: "lastminute.com",
        imageUrl: imgHotel,
        sellingPoints: ["Flexible payments", "Book with deposit"],
      },
    },
    {
      flight: {
        originCity: "Barcelona",
        originCode: "BCN",
        destinationCity: "Beijing",
        destinationCode: "PKX",
        outbound: {
          depTime: "14:20",
          arrTime: "11:50+1",
          depCode: "BCN",
          arrCode: "PKX",
          airline: "Lufthansa",
          airlineCode: "LH",
          stopsLabel: "1 stop · FRA",
        },
        inbound: {
          depTime: "13:10",
          arrTime: "20:35",
          depCode: "PKX",
          arrCode: "BCN",
          airline: "Lufthansa",
          airlineCode: "LH",
          stopsLabel: "1 stop · MUC",
        },
        pricePerPerson: 3890,
        totalPrice: 7780,
        currency: "EUR",
      },
      accommodation: {
        name: "The Peninsula Beijing",
        starRating: 5,
        reviewScore: 4.8,
        reviewLabel: "Excellent",
        locationLabel: "Chaoyang · near CBD",
        nights: 7,
        breakfastIncluded: false,
        pricePerPerson: 2100,
        totalPrice: 4200,
        currency: "EUR",
        providerName: "Expedia",
        imageUrl:
          "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=800&q=80",
        sellingPoints: ["City views", "Spa access"],
      },
    },
    {
      flight: {
        originCity: "Barcelona",
        originCode: "BCN",
        destinationCity: "Beijing",
        destinationCode: "PEK",
        outbound: {
          depTime: "08:05",
          arrTime: "05:40+1",
          depCode: "BCN",
          arrCode: "PEK",
          airline: "Air China",
          airlineCode: "CA",
          stopsLabel: "Nonstop",
        },
        inbound: {
          depTime: "04:25",
          arrTime: "10:10",
          depCode: "PEK",
          arrCode: "BCN",
          airline: "Air China",
          airlineCode: "CA",
          stopsLabel: "Nonstop",
        },
        pricePerPerson: 3688,
        totalPrice: 7376,
        currency: "EUR",
      },
      accommodation: {
        name: "Grand Hyatt Beijing",
        starRating: 5,
        reviewScore: 4.6,
        reviewLabel: "Excellent",
        locationLabel: "Dongcheng · near Forbidden City",
        nights: 7,
        breakfastIncluded: true,
        pricePerPerson: 1950,
        totalPrice: 3900,
        currency: "EUR",
        providerName: "Booking.com",
        imageUrl:
          "https://images.unsplash.com/photo-1582719508461-905c673771fd?w=800&q=80",
        sellingPoints: ["Pool", "Family friendly"],
      },
    },
  ],
};

/** After “refine” — fewer results, shifted theme */
export const fixtureRefined: MockFixtureSet = {
  displayTheme: "Narrowed: historic core · walkable neighbourhoods",
  tripFactsLine: "Barcelona (BCN) – Beijing • Thu, 30 Apr – Thu, 07 May • 2 travellers",
  intentChips: ["Culture", "Foodie"],
  extras: [
    { cardTags: ["Walkable", "Heritage area", "Top rated"] },
    { cardTags: ["Matches: Foodie", "Night markets nearby"] },
  ],
  rows: [fixturePrimary.rows[2], fixturePrimary.rows[1]],
};

/** After chip removal — exploratory copy */
export const fixtureExploratory: MockFixtureSet = {
  displayTheme: "Exploring options from Barcelona · flexible rhythm",
  tripFactsLine: "From Barcelona (BCN) · flexible return • 2 travellers · EUR",
  intentChips: ["Foodie"],
  extras: fixturePrimary.extras.slice(0, 2),
  rows: fixturePrimary.rows.slice(0, 2),
};
