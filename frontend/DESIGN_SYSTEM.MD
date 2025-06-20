# SelfDB Website Design System

This document outlines the core design tokens and guidelines used in the SelfDB website project. The system is primarily implemented using Tailwind CSS configuration.

## 1. Color Palette

Colors are defined in `tailwind.config.js` under `theme.extend.colors`.

### Primary Color (Blue)

Used for main calls to action, links, and important highlights.

- **Classes:** `bg-primary-*`, `text-primary-*`, `border-primary-*`
- **Main Shade:** `primary-600` (`#2563eb`)

```js
// tailwind.config.js
primary: {
  50: '#eff6ff',
  100: '#dbeafe',
  200: '#bfdbfe',
  300: '#93c5fd',
  400: '#60a5fa',
  500: '#3b82f6',
  600: '#2563eb', // Main primary color
  700: '#1d4ed8',
  800: '#1e40af',
  900: '#1e3a8a',
  950: '#172554',
},
```

### Secondary Color (Gray)

Used for body text, borders, and background shades.

- **Classes:** `bg-secondary-*`, `text-secondary-*`, `border-secondary-*`
- **Foreground Text:** `secondary-800` (`#1f2937`)
- **Muted Text:** `secondary-500` (`#6b7280`)
- **Subtle Background:** `secondary-50` (`#f9fafb`)
- **Default Background:** `white` (`#ffffff`)

```js
// tailwind.config.js
secondary: {
  50: '#f9fafb', // background-subtle
  100: '#f3f4f6',
  200: '#e5e7eb',
  300: '#d1d5db',
  400: '#9ca3af',
  500: '#6b7280', // text-muted
  600: '#4b5563',
  700: '#374151',
  800: '#1f2937', // text-foreground
  900: '#111827',
  950: '#030712',
},
```

### Accent Color (Teal)

Used sparingly for highlighting secondary actions or visual flourishes.

- **Classes:** `bg-accent-*`, `text-accent-*`, `border-accent-*`
- **Main Shade:** `accent-500` (`#14b8a6`)

```js
// tailwind.config.js
accent: {
  50: '#f0fdfa',
  100: '#ccfbf1',
  200: '#99f6e4',
  300: '#5eead4',
  400: '#2dd4bf',
  500: '#14b8a6', // Main accent color
  600: '#0d9488',
  700: '#0f766e',
  800: '#115e59',
  900: '#134e4a',
  950: '#042f2e',
},
```

### Semantic Colors

Standard colors for feedback messages (success, warning, error) are also defined.

- **Classes:** `bg-success-*`, `text-warning-500`, `border-error-600`, etc.
- See `tailwind.config.js` for the full scale.

## 2. Typography

Fonts are configured in `tailwind.config.js` and loaded via Google Fonts in `index.html`. Base styles are applied in `src/index.css`.

### Font Families

- **Body:** `Inter` (Applied via `font-sans` utility)
- **Headings:** `Poppins` (Applied via `font-heading` utility)

```js
// tailwind.config.js
fontFamily: {
  sans: ['Inter', /* fallback fonts */],
  heading: ['Poppins', /* fallback fonts */],
},
```

### Base Styles (`src/index.css`)

- `body` uses `font-sans` and `text-secondary-800` by default.
- `h1` - `h6` use `font-heading`, `font-bold`, and `tracking-tight` by default.

### Font Loading (`index.html`)

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@600;700;800&display=swap" rel="stylesheet">
```

## 3. Spacing

The project primarily uses Tailwind's default spacing scale (multiples of 4px). Consult the [Tailwind Spacing Documentation](https://tailwindcss.com/docs/customizing-spacing) for available values (e.g., `p-4`, `m-8`, `gap-6`).

One custom spacing value has been added:
- `spacing: { '128': '32rem' }`

## 4. Tables

Tables should follow a consistent style across the application for data display. The following guidelines ensure consistency with SelfDB's design language.

### Container

- Wrap tables in a parent container with these classes:
  ```
  bg-white dark:bg-secondary-800 p-6 rounded-lg shadow border border-secondary-200 dark:border-secondary-700
  ```
- Add `overflow-x-auto` to handle horizontal scrolling for narrow viewports

### Table Structure

- Use `min-w-full` to ensure the table fills the container
- Use `divide-y divide-secondary-200 dark:divide-secondary-700` for row dividers

### Table Headers

```html
<thead>
  <tr>
    <th className="px-4 py-2 text-left text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider">
      Column Name
    </th>
  </tr>
</thead>
```

- Use uppercase text for column headers
- Apply `text-secondary-500 dark:text-secondary-400` for header text color
- Use `tracking-wider` for slight letter spacing in headers
- Apply consistent `px-4 py-2` padding

### Table Body

```html
<tbody className="divide-y divide-secondary-200 dark:divide-secondary-700">
  <tr>
    <td className="px-4 py-2 text-secondary-800 dark:text-white text-sm">
      Cell content
    </td>
  </tr>
</tbody>
```

- Use `divide-y` for row separators
- Apply `text-secondary-800 dark:text-white` for cell text
- Keep consistent `px-4 py-2` padding for cells
- Use `text-sm` for cell content

### Status Indicators

For status badges within tables:

```html
<span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-success-100 dark:bg-success-900 text-success-800 dark:text-success-100">
  Active
</span>
```

- Use `rounded-full` for pill-shaped badges
- Apply semantic colors based on status (success, warning, error)
- Use `text-xs` and `font-medium` for badge text

### Table Loading & Empty States

- Loading state:
  ```html
  <div className="text-center text-secondary-500 dark:text-secondary-400 py-8 text-base">
    Loading data...
  </div>
  ```

- Empty state:
  ```html
  <div className="text-secondary-500 dark:text-secondary-400 py-8 text-center text-base">
    No data found.
  </div>
  ```

### Error Messages

```html
<div className="text-error-600 dark:text-error-400 bg-error-50 dark:bg-error-900/30 p-4 rounded mb-4 text-sm">
  Error message
</div>
```

### Actions Column

For tables with action buttons:

```html
<td className="px-4 py-2 text-center">
  <Button
    variant="outline"
    className="text-error-600 dark:text-error-400 border-error-300 dark:border-error-500 hover:bg-error-50 dark:hover:bg-error-900/30"
  >
    Delete
  </Button>
</td>
```

- Center action buttons with `text-center`
- Use appropriate semantic colors for buttons (e.g., error colors for delete)
- Keep consistent padding with other cells

### Sortable Headers

For sortable column headers, add:

```html
<th 
  className="px-4 py-2 text-left text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider cursor-pointer hover:bg-secondary-50 dark:hover:bg-secondary-700"
  onClick={handleSort}
>
  <div className="flex items-center">
    <span>Column Name</span>
    {sortIndicator}
  </div>
</th>
```

- Add `cursor-pointer` for interactive indication
- Add hover state with `hover:bg-secondary-50 dark:hover:bg-secondary-700`
- Use consistent sort indicators (up/down arrows)

## 5. Usage

Apply design tokens using Tailwind utility classes directly in your components.

- **Colors:** `text-primary-600`, `bg-secondary-50`, `border-accent-300`
- **Typography:** The base fonts are applied automatically. Use utilities like `text-lg`, `font-medium`, `leading-relaxed` as needed. Headings automatically use the `Poppins` font.
- **Spacing:** `p-6`, `my-4`, `space-x-2`, `gap-4`

Strive for consistency by reusing defined colors and respecting the typography hierarchy. 