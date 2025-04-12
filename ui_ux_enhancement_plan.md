# UI/UX Enhancement Plan (April 2025)

This document tracks the progress of implementing the UI/UX improvements suggested on April 12, 2025.

## Enhancement Checklist

- [X] **1. Color Palette & Theming:** Defined and implemented core CSS variables.
- [X] **2. Typography:** Selected and implemented base font styles and Google Font import.
- [ ] **3. Layout & Information Hierarchy:** Principles defined, to be applied during component HTML updates.
- [ ] **4. Components & Controls:** CSS styles defined for all planned components. HTML applied for KPI Cards and Sync Button.
    - [X] CSS Defined: Modals (4a)
    - [ ] CSS Defined: Graphs & Charts (4b - Placeholder)
    - [X] CSS Defined: Tables (4c)
    - [X] CSS Defined & HTML Applied: Buttons & Controls (4d - Sync Button)
    - [X] CSS Defined: Date Range Selector (4e)
    - [X] CSS Defined: Transcript Viewer (4f)
    - [X] CSS Defined & HTML Applied: KPI Cards (4g)
- [ ] **5. Consistency:** Ensure all chosen styles are applied uniformly across the application. (Ongoing)
- [ ] **6. (TBD - Future):** Address any specific component refinements not covered above.

## Decisions & Implementation Notes

### 1. Color Palette & Theming
- **Primary:** Deep Indigo (`#3A0CA3`)
- **Secondary/Accent:** Muted Teal (`#48BFE3`)
- **Neutrals:** Dark Gray (`#343a40`), Light Gray (`#F8F9FA`), Border Gray (`#E9ECEF`)
- **Data Visualization Palette:** To be defined later, ensuring harmony and accessibility.
- **Status:** Core variables added to `style.css`. **Updated Palette AGAIN 2025-04-12.**

### 2. Typography
- **Headings:** `Montserrat`
- **Body:** `Lato`
- **Status:** Base styles and Google Font import added to `style.css`.

### 3. Layout & Information Hierarchy
- **Approach:** Apply principles generally across all pages during component refinement (Step 4).
- **Principles:**
    - Increase whitespace (margins/padding) consistently.
    - Standardize page structure (headers, etc.) where feasible.
    - Enhance visual hierarchy using typography, color, and spacing.
- **Status:** Principles defined.

### 4. Components & Controls
- **a) Modals (e.g., Sync Status):**
    - **Header:** Styled with Primary color derivative, `Montserrat` title, icon.
    - **Body:** Adequate padding (`p-3`/`p-4`), `Lato` font, structured content.
    - **Footer:** Consistent button alignment (right), Primary/Secondary color for main action, standard style for Close/secondary.
    - **Overall:** Rounded corners, subtle fade animation.
    - **Status:** CSS rules added to `style.css`.
- **b) Graphs & Charts (Chart.js):**
    - **Data Viz Palette:** Initial set: Indigo (`#3A0CA3`), Magenta (`#C77DFF`), Lighter Purple (`#9D4EDD`), Medium Blue (`#5E60CE`). (Refine/test later).
    - **Tooltips:** Custom background/font (`Lato`), consistent formatting, color indicators.
    - **Hover States:** Clear visual feedback (brightness/border).
    - **Axes & Labels:** `Lato` font, good contrast, subtle gridlines, Y-axis titles.
    - **Legends:** Consistent positioning, `Lato` font.
    - **Empty States:** Clear "No data available" message.
    - **Chart Styles:** Apply filled lines with tension, consistent bar styles.
    - **Status:** CSS placeholder added. Styling primarily via JS options.
- **c) Tables (Transcript Viewer List):**
    - **Padding:** Increase cell padding (`py-2 px-3`).
    - **Zebra Striping:** Subtle alternating row colors (customize `table-striped`).
    - **Hover States:** Clear row hover effect (customize `table-hover`).
    - **Alignment:** Left-align text, right-align numbers/dates.
    - **Borders:** Minimal horizontal borders, distinct header border.
    - **Header:** `Montserrat` font (bold), distinct background/border, consistent alignment.
    - **Body:** `Lato` font.
    - **Status:** CSS rules added to `style.css`.
- **d) Buttons & Controls:**
    - **Primary Buttons (e.g., Search, major actions):** Secondary color (`#C77DFF`) background, white text, `Lato` font (bold).
    - **Secondary Buttons (e.g., Close, minor actions):** Standard `btn-secondary` or outline style, `Lato` font.
    - **Link Buttons:** Primary color (`#3A0CA3`) text, clear hover state.
    - **Icon Buttons:** Good contrast, clear interaction states.
    - **Padding/Rounding:** Consistent (e.g., `py-2 px-3`, standard rounding).
    - **States (:hover, :focus, :active):** Clear visual feedback, themed focus ring for inputs.
    - **Form Controls:** Standard styling, themed focus state, `Lato` font.
    - **Status:** CSS rules added. Sync button in `base.html` updated.
- **e) Date Range Selector:**
    - **Structure:** Button group (`btn-group`).
    - **Inactive Style:** Outline style (`btn-outline-secondary` or custom primary `#3A0CA3`), `Lato` font.
    - **Active Style:** Primary color (`#3A0CA3`) background, white text, `Lato` font.
    - **Hover States:** Subtle feedback for inactive, darker primary for active.
    - **Padding/Sizing:** Consistent, comfortable click targets.
    - **Status:** CSS rules added to `style.css`.
- **f) Transcript Viewer (iMessage Style):**
    - **Message Bubbles:** Light primary shade (`#A89BFF` TBC) for Agent (left), light neutral (`#E9ECEF`) for Caller (right), `