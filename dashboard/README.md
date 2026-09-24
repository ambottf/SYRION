# SYRION Dashboard — Phase 0

> Next.js 14 App Router — nur Start-Server, keine Anwendungslogik.

## Start
```powershell
cd dashboard
npm install
npm run dev      # http://localhost:3000
npm run build    # Production-Build prüfen
```

## Struktur
```
dashboard/
  app/
    layout.tsx
    page.tsx     # Stub: "SYRION — Phase 0"
    globals.css
  public/        # statische Assets (leer in Phase 0)
  next.config.mjs
  tsconfig.json
```

## Hinweise
- Architektur: `../SYRION_ARCHITEKTUR.md` Kap. 9
- Gateway läuft separat unter `:8080` (Docker oder `core`)
- Keine Tailwind/shadcn in Phase 0 — wird erst in Phase 1 benötigt
