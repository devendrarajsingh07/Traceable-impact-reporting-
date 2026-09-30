# Traceable frontend design

## Direction

Traceable uses an editorial evidence-dossier aesthetic. Warm paper surfaces, restrained forest green, fine rules, and serif report typography make the product feel closer to a credible board report than a generic dashboard. Amber is reserved for unresolved data and assumptions.

## Tokens

All component colors use CSS custom properties from `src/styles.css`. The light and dark palettes define background, surface, ink, line, brand, warning, success, focus, and error roles. Controls use 10px radii, cards use 16px radii, and status chips use full pill radii.

Fraunces is used for page titles, report titles, and headline numbers. Inter is used for forms, tables, navigation, and supporting copy. Both include local fallback stacks.

## Components

- `AppShell` provides the Traceable brand, responsive step tracker, and theme control.
- `Button`, `Card`, `Chip`, `ConfidenceBar`, `DataGapCallout`, `EmptyState`, `LoadingState`, and `PrivacyNote` provide shared, accessible patterns.
- Workflow pages are separate route components for upload, matching, duplicate review, metrics, and report output.
- Flow prerequisites persist in local storage and are reconciled with the API when the application opens.

## Suggestion versus confirmation

Fuzzy matches and AI-generated formulas are always presented as drafts. Low-confidence column matches remain empty until a user chooses a field. Duplicate candidates require an explicit “Same person” or “Keep separate” decision. AI metric output exposes a plain-language restatement and the underlying JSON, and it is never stored until the user selects “Save and build report.” The manual metric path remains available when AI assistance fails.

## Responsive and accessible behavior

At widths below 760px, two-column comparisons and report structures become single-column layouts. Tables scroll inside their containers without widening the document. Every input has a label, focus states are visible, status is communicated with words and icons as well as color, motion respects reduced-motion settings, and pseudonymization is stated wherever source records appear.
