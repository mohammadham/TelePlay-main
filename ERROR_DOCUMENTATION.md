# Pre-existing TypeScript Errors Documentation

## 1. ErrorBoundary.tsx (60,26): process not found

**Issue**: In Vite environment, the global `process` variable is not available by default, causing a ReferenceError when accessing `process.env.NODE_ENV`.

**Root Cause**: The original code used:
```tsx
(import.meta.env.DEV || process.env.NODE_ENV === 'development') && this.state.error && (
```

**Solution**: Changed to use `import.meta.env.DEV` which is Vite's native way to check for development mode, eliminating the need for the non-existent global `process` variable.

## 2. NotFound.tsx (8,21): unused useState

**Issue**: The file imported `useState` but never used it, only used `useEffect`.

**Root Cause**: During development, `useState` was added but later refactored, leaving the unused import.

**Solution**: Removed the unused import statement:
```tsx
import { useEffect } from 'react';
```

## 3. SetupPage.tsx: unused variables

**Issue**: Four variables are declared but never used:
- `autoConfig`: declared but never assigned or used
- `setAutoConfig`: setter for unused variable
- `setExtraTokens`: setter for unused array
- `goToStep`: callback function never called

**Root Cause**: These were likely added during development for features that were later removed or modified without cleaning up the code.

**Solution**: Removed all unused variables and their corresponding state setters.

## 4. Sidebar.tsx: mobile sidebar behavior

**Issue**: The sidebar opens by default on mobile devices, and the close button doesn't work properly.

**Root Cause**: The `Sidebar` component uses `isOpen` state that's not properly initialized, and the mobile overlay doesn't correctly handle closing.

**Solutions**:
1. Added `useState` for `mobileOpen` state in Sidebar
2. Implemented event-based sidebar opening via `open-sidebar` event
3. Ensured proper conditional rendering based on `alwaysOpen` prop

## 5. Sidebar hamburger button

**Issue**: The hamburger button opens the sidebar but the close button (X) doesn't work.

**Root Cause**: The sidebar component needs to properly handle the `isOpen` state and ensure the close button triggers the `onClose` callback.

**Solution**: The Sidebar component now properly handles the `isOpen` state through the `alwaysOpen` prop and event-based state changes.

## 6. Mobile navigation

**Issue**: Mobile navigation should use a bottom bar instead of a side drawer for better UX.

**Root Cause**: The original implementation used a fixed-position sidebar overlay which is not ideal for mobile-first design.

**Solution**: Created `MobileBottomNav` component with Android-style bottom navigation that:
- Is visible only on mobile screens (<768px)
- Uses standard Android navigation patterns
- Maintains visibility of key sections (Music, Search, Playlists, Downloads, History)
- Integrates with existing routing system

## 7. Missing admin-controlled SEO/Geo settings

**Issue**: SEO meta tags and geo-targeting settings are hardcoded, not configurable from admin panel.

**Root Cause**: The admin SettingsPanel only shows environment template values but no structured SEO/Geo configuration.

**Solution**: Added `SEOSettings` model to backend with fields for title, description, keywords, geo_region, geo_locale, social_image. Created API endpoints to fetch/update SEO settings. Admin panel component `SeoSettingsPanel` allows editing these values. The `useSEO` hook now fetches dynamic values from API instead of using hardcoded defaults.