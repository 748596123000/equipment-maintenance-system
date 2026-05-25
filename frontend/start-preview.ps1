#!/usr/bin/env pwsh
# Start the frontend preview server

Write-Host "Starting Vite preview server..." -ForegroundColor Cyan

# Start the Vite preview server on port 3001
npm run preview -- --port 3001 --host