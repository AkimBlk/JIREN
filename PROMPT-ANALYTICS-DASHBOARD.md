✅ PROMPT POUR @senior-dev - ANALYTICS DASHBOARD V2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FEATURE: analytics_dashboard_with_project_filter
APP    : blog/

GOAL
Upgrade analytics dashboard with project-level filtering and improved visual hierarchy. Display per-project sprint analytics in 3 large, compartmented chart sections with proper visibility in both light & dark modes.

MODELS
- Sprint              → Already exists, use STATUS_CLOSED, configured_capacity()
- Ticket             → Already exists, use STATUS_DONE, story_points
- Project            → Already exists, use for context

VIEWS
- AnalyticsView      → GET /analytics/ [StaffOnly] render analytics_dashboard.html
  - Accept optional query param: ?project_id=<pk>
  - Refactor get_context_data() to accept project filter
  
  Context data (global OR filtered by project):
  - all_projects                 → List of Project objects for dropdown
  - selected_project             → Project object or None (if "All Projects" selected)
  - velocity_labels              → ["Sprint 1", "Sprint 2", ...] (sprint names only, no project names if filtered)
  - velocity_values              → [8, 12, 10, ...] (story points completed per sprint)
  - consumption_values           → [75.0, 90.0, 83.0] (% capacity used per sprint)
  - burndown                     → {labels: ["01/04", "02/04"], ideal: [80, 40, 0], actual: [80, 45, 20]} | null
  - selected_sprint              → Last closed sprint object or None
  - projects_count               → Total project count
  - sprints_count                → Total closed sprint count (for current filter)

TEMPLATES
- analytics_dashboard.html → Main page with project filter + 3 large chart sections
  Layout:
  1. Header section with:
     - Title: "Analytics Dashboard"
     - Project dropdown filter (All Projects / Project A / Project B / ...)
     - Stats row: Projects / Sprints Completed / Latest Sprint
  
  2. Chart Section A (FULL WIDTH - 70% height)
     - Title: "Team Velocity"
     - Line chart showing story points per sprint
     - Chart height: 450px (larger for better visibility)
     - Hover tooltips with sprint name
  
  3. Chart Section B + C (SIDE BY SIDE - 50% each)
     - Chart B: "Capacity Consumption" (Bar chart, 50% width)
       - Color coding: Green (≤80%), Yellow (80-95%), Red (>95%)
       - Height: 400px
     - Chart C: "Sprint Burndown (Latest)" (Line chart, 50% width)
       - Dual-line chart: Ideal vs Actual
       - Height: 400px
       - Fallback: "No data available"

CARD STYLING FIX
- Light mode visibility:
  - Background: var(--helb-surface-container) NOT var(--helb-surface-container-lowest)
  - Border: 2px solid var(--helb-outline) (more prominent than outline-variant)
  - Shadow: var(--helb-shadow-lg) (increased depth)
  - Backdrop: blur(20px) for extra definition
- Both modes:
  - Padding increased to 2rem
  - Border-radius: 2rem (more rounded)
  - Divider line (1px) between card header and chart

CHART SIZING
- Velocity chart: Full width, 450px height
- Capacity chart: 50% width (grid), 400px height
- Burndown chart: 50% width (grid), 400px height
- Canvas padding: 1rem inside container for breathing room

DROPDOWN IMPLEMENTATION
- Location: Header, next to stats
- Label: "Filter by Project"
- Options:
  - "All Projects" (value="" or None)
  - "Project A"
  - "Project B"
  - ... (all projects with closed sprints)
- Styling: Material Design select input with hover/focus states
- On change: 
  - AJAX fetch OR simple form submit to /analytics/?project_id=<pk>
  - Reload charts with filtered data
  - Preserve selected option in dropdown

JAVASCRIPT ENHANCEMENTS
- Get project_id from URL query param
- Initialize dropdown with selected value
- Handle "All Projects" → calculate from all_projects
- Handle single-project filter → calculate from filtered sprints only
- Dropdown change listener updates URL (pushState) + reloads page OR fetches via JS

CHART.JS IMPLEMENTATION
- Load Chart.js from CDN: https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js
- Use `{% json_script %}` filter to embed data safely in <script> tags
- Initialize 3 separate Chart instances on DOMContentLoaded
- Colors: Velocity #6366f1, Consumption #22c55e, Burndown ideal #94a3b8, actual #6366f1
- Larger canvas height for better readability

CLEAN CODE RULES (non-negotiable)
- All names in English, intent-revealing
- Method names: _get_project_from_request(), _calculate_sprints_for_project(), _calculate_done_story_points(), _burndown_data()
- No magic numbers → PERCENTAGE_MULTIPLIER = 100, DECIMAL_PRECISION = 2
- No function > 20 lines, complexity ≤ 4
- No business logic in view context → calculations in dedicated methods
- N+1 queries FORBIDDEN → Use select_related("project") on sprints, prefetch_related("tickets")
- Template: use data attributes via {{ data|json_script:"id" }} for JS access
- CSS: Material Design tokens (var(--helb-*)) with proper contrast ratios
- Responsive: Mobile-first (1 col) → Tablet (1 wide + 2 stacked) → Desktop (1 wide + 2 side-by-side)

CSS STYLING IMPROVEMENTS
- Header container: padding 2rem, max-width 1400px
- Project dropdown: full styling with focus states, Material Design
- Chart cards:
  - Background: var(--helb-surface-container) [not lowest]
  - Border: 2px solid var(--helb-outline) [not outline-variant]
  - Shadow: var(--helb-shadow-lg)
  - Padding: 2rem
  - Border-radius: 2rem
  - Backdrop-filter: blur(20px)
- Card header divider: 1px solid var(--helb-outline-variant) below card-title
- Chart container heights: Velocity 450px, Capacity/Burndown 400px
- Responsive breakpoints: 1024px (grid 2/1), 768px (grid 1)

LAYOUT GRID
- Desktop: 
  1. Full-width velocity chart (row 1)
  2. Two side-by-side charts: Capacity (50%) + Burndown (50%) (row 2)
- Tablet (≤1024px):
  1. Full-width velocity chart
  2. Full-width capacity chart
  3. Full-width burndown chart
- Mobile (≤768px):
  1. Full-width velocity chart (350px height)
  2. Full-width capacity chart (300px height)
  3. Full-width burndown chart (300px height)

DATABASE OPTIMIZATION
- Query projects: Project.objects.all().order_by("name")
- Query sprints: Sprint.objects.filter(status=STATUS_CLOSED).select_related("project").prefetch_related("tickets")
- Filter on project_id if provided in context
- Single aggregation pass per filter

DONE WHEN
[ ] AnalyticsView accepts optional ?project_id query parameter
[ ] get_context_data() returns all_projects list for dropdown
[ ] selected_project context variable reflects filter (None = All Projects)
[ ] Dropdown in template renders all projects as options
[ ] On dropdown change, form/link updates URL to /analytics/?project_id=<pk>
[ ] Charts filter correctly: "All Projects" shows all sprints, "Project X" shows only that project's sprints
[ ] Velocity chart: 450px height, full width, line chart
[ ] Capacity chart: 400px height, 50% width on desktop, full width on mobile
[ ] Burndown chart: 400px height, 50% width on desktop, full width on mobile
[ ] Card styling: 2px border, proper background, large shadow in light mode
[ ] Light mode visibility: Cards clearly visible with proper contrast
[ ] Dark mode: Cards still look good with updated styling
[ ] Charts display with proper breathing room (canvas padding)
[ ] No N+1 queries detected
[ ] HTML structure supports responsive grid layout
[ ] python manage.py check → 0 issues
[ ] Charts are responsive on mobile/tablet/desktop viewports
[ ] Dropdown styling matches Material Design theme
[ ] Hover/focus states on dropdown

NOTES
- Dropdown label: "Filter by Project"
- Default selected: "All Projects"
- Sprint labels in filtered view should NOT include project name (already filtered)
- If selected project has no closed sprints, show empty state: "No completed sprints for this project"
- Query param behavior: /analytics/ = all, /analytics/?project_id=5 = project 5 only
- Consumption color logic (unchanged):
  - ≤ 80% → green (#22c55e)
  - 80-95% → yellow/amber (#f59e0b)
  - > 95% → red (#ef4444)
- The dropdown option to select the project is only avaible for root user 
- Update all charts when project filter changes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
