# Should I Add React to This Project?

## Pros

- **State management** — As you add more layers (POIs, user preferences, filters), React's state model would make toggling, combining filters, and syncing UI cleaner than manual DOM updates.

- **Component reuse** — Legend, popups, route cards, and filter controls could become reusable components. If you add multiple map views or pages, you avoid duplicating logic.

- **react-leaflet** — A mature library that wraps Leaflet with React components, making layer management declarative:
  ```jsx
  {showCycleways && <GeoJSON data={cyclewaysData} />}
  ```

- **Easier testing** — Component-based architecture makes unit testing UI logic simpler.

## Cons

- **Overhead for current scope** — The map is self-contained with ~200 lines of JS. React adds build tooling (Vite/Webpack), JSX transpilation, and a larger bundle for what currently loads instantly.

- **GitHub Pages friction** — You'd need a build step and deploy the `dist/` folder instead of serving HTML directly. Adds CI/CD complexity.

- **Leaflet integration quirks** — react-leaflet works well but has edge cases. Direct DOM manipulation (like `polylineDecorator`) sometimes requires escaping React's model.

- **Learning curve** — If you're not already fluent in React, the ramp-up time may not pay off for a personal project.

## Recommendation

Wait until you feel the pain. Signs that would justify React:

- Multiple maps sharing state or components
- Complex filtering UI (e.g., multi-select, search, saved preferences)
- More than ~500 lines of JS or significant UI beyond the map
- Wanting to add routing between pages (e.g., `/skating`, `/routes/:id`)

For now, incrementally improve by extracting JS into a separate file and using ES modules. That keeps things simple while preparing for a framework later if needed.