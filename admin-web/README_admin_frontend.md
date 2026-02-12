# ValuScan Admin Frontend

Minimal admin interface with Asia/Singapore timezone-based theme switching.

## Features

- **Auto Theme Switching**: Day mode (07:00-18:59) / Night mode (19:00-06:59) based on Asia/Singapore timezone
- **5 Pages**: Dashboard, Controls, Params, Logs, Data Sources
- **Black & White Design**: Monospace fonts, thin borders, strong whitespace
- **Real-time Updates**: SSE log streaming, 5s health polling

## Tech Stack

- Vite + React 18 + TypeScript
- Tailwind CSS
- React Router 6
- Zero external UI libraries

## Setup

```bash
cd E:/project/valuescan/admin-web
npm install
npm run dev
```

Access at: http://localhost:3001

## Theme Engine

Located in `src/hooks/useTheme.ts`:

- Uses `Intl.DateTimeFormat` with `timeZone: 'Asia/Singapore'`
- Checks every 60 seconds for theme switch
- Manual toggle available (resets at next scheduled time)
- Day mode: Dark bg + white text (07:00-18:59)
- Night mode: Light bg + black text (19:00-06:59)

## API Integration

Backend proxy configured in `vite.config.ts`:
- `/api/*` → `http://localhost:8000`

All endpoints from SCHEMAS_V3.md implemented in `src/services/api.ts`.

## Pages

1. **Dashboard** (`/`): System health, task status, quick actions
2. **Controls** (`/controls`): Scheduler control, manual triggers
3. **Params** (`/params`): Config editor (form/JSON toggle)
4. **Logs** (`/logs`): Real-time log stream with filters
5. **Data Sources** (`/data-sources`): News + econ calendar preview

## Build

```bash
npm run build
npm run preview
```

Output: `dist/`
