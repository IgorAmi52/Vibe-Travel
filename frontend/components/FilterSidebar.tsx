export function FilterSidebar() {
  return (
    <aside className="w-full shrink-0 space-y-6 lg:w-56 xl:w-64" aria-label="Filters">
      <div>
        <p className="mb-2 text-sm font-semibold text-ss-navy">Sort by</p>
        <select className="w-full rounded border border-neutral-200 bg-white px-2 py-2 text-sm">
          <option>Best</option>
          <option>Cheapest</option>
          <option>Quickest</option>
        </select>
      </div>
      <div>
        <p className="mb-2 text-sm font-semibold text-ss-navy">Map</p>
        <div className="flex h-28 items-center justify-center rounded border border-dashed border-neutral-300 bg-neutral-50 text-xs text-neutral-500">
          Map preview
        </div>
      </div>
      <div>
        <p className="mb-2 text-sm font-semibold text-ss-navy">Price</p>
        <div className="h-2 rounded-full bg-neutral-200">
          <div className="h-2 w-2/3 rounded-full bg-ss-accent" />
        </div>
        <p className="mt-1 text-xs text-neutral-500">€500 – €8,000</p>
      </div>
      <div>
        <p className="mb-2 text-sm font-semibold text-ss-navy">Hotel review score</p>
        <ul className="space-y-1 text-sm text-neutral-700">
          <li>
            <label className="flex cursor-pointer items-center gap-2">
              <input type="checkbox" className="rounded border-neutral-300" />9+
            </label>
          </li>
          <li>
            <label className="flex cursor-pointer items-center gap-2">
              <input type="checkbox" className="rounded border-neutral-300" />8+
            </label>
          </li>
          <li>
            <label className="flex cursor-pointer items-center gap-2">
              <input type="checkbox" className="rounded border-neutral-300" />7+
            </label>
          </li>
        </ul>
      </div>
    </aside>
  );
}
