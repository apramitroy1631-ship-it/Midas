# Marketing & Growth System — Frontend

React + Vite + TypeScript app with three tabs aligned to the backend API.

## Run

1. Start the FastAPI backend (e.g. on port 8000).
2. **Use a WSL terminal** (Ubuntu app or `wsl` in PowerShell) and use the Linux path so npm never sees a UNC path:

   ```bash
   cd "/home/kartik/projects/Multi Agents Marketing and Growth System/Frontend"
   npm install
   npm run dev
   ```

3. Open http://localhost:5173. Use the navbar to switch between **Dashboard**, **Brands**, and **Campaigns**.

API requests from the app go to `/api/*` and are proxied to `http://localhost:8000` (no backend CORS changes required).

## If `npm install` fails (UNC path / esbuild error)

The error happens when the shell’s current directory is a Windows UNC path (`\\wsl.localhost\...`). npm then spawns `cmd.exe` with that path, and CMD falls back to `C:\Windows`, so postinstall scripts (e.g. esbuild) fail.

**Fix:** run install from **inside WSL** with a **Linux path**:

1. Open **WSL** (e.g. “Ubuntu 24.04” or run `wsl` in PowerShell).
2. Go to the project with the Linux path (not `\\wsl...`):
   ```bash
   cd "/home/kartik/projects/Multi Agents Marketing and Growth System/Frontend"
   ```
3. Remove a broken install and reinstall:
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   ```
4. Start the app:
   ```bash
   npm run dev
   ```

Use this same WSL terminal (and this `cd` path) for all `npm` commands.
