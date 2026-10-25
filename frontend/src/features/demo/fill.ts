interface SeedCustomer {
  name: string;
  city: string;
  transit: string;
  transitTotal: number;
  delivered: string;
  deliveredTotal: number;
}

const SEEDS: Record<"ana" | "bruno" | "carla", SeedCustomer> = {
  ana: {
    name: "Ana Rojas",
    city: "Caracas",
    transit: "A-1001",
    transitTotal: 45,
    delivered: "A-1002",
    deliveredTotal: 18,
  },
  bruno: {
    name: "Bruno Díaz",
    city: "Valencia",
    transit: "B-2001",
    transitTotal: 60,
    delivered: "B-2002",
    deliveredTotal: 12,
  },
  carla: {
    name: "Carla Méndez",
    city: "Maracaibo",
    transit: "C-3001",
    transitTotal: 150,
    delivered: "C-3002",
    deliveredTotal: 8,
  },
};

const DEMO_TRANSIT_TOTAL = 45;
const DEMO_DELIVERED_TOTAL = 18;

function seedOwning(orders: readonly string[]): SeedCustomer | undefined {
  return Object.values(SEEDS).find(
    (seed) => orders.includes(seed.transit) || orders.includes(seed.delivered),
  );
}

export function placeholders(orders: readonly string[]): Record<string, string> {
  const own = seedOwning(orders);
  const first = own === SEEDS.carla ? SEEDS.ana : SEEDS.carla;
  const second = own === SEEDS.bruno ? SEEDS.ana : SEEDS.bruno;
  return {
    own: orders[0] ?? "",
    own_total: String(own?.transitTotal ?? DEMO_TRANSIT_TOTAL),
    own_delivered: orders[1] ?? orders[0] ?? "",
    own_delivered_total: String(own?.deliveredTotal ?? DEMO_DELIVERED_TOTAL),
    f: first.transit,
    f_name: first.name,
    f_city: first.city,
    f_total: String(first.transitTotal),
    g: second.transit,
    g_delivered: second.delivered,
    g_delivered_total: String(second.deliveredTotal),
  };
}

export function fill(text: string, values: Record<string, string>): string {
  return text.replace(/\{(\w+)\}/g, (match, key: string) => values[key] ?? match);
}
