# AgentOS design guide

These are the colours, type and components the app already uses (Tailwind 4 classes). New screens should reuse them so every page looks the same.

## Logo

logo.svg in this folder: a dark rounded square with a blue ring and a white play triangle (an agent running), plus an amber dot on the ring (a human approval). Use it on the login page, the sidebar and the slides. Keep clear space of at least a quarter of its width.

## Colours

| Role | Tailwind class | Hex | Used for |
|------|----------------|-----|----------|
| Sidebar, headings on dark | gray-900 | #111827 | Sidebar, code blocks, slide background |
| Page background | gray-50 | #f9fafb | Main area |
| Card | white | #ffffff | Cards and forms (with shadow-sm) |
| Body text | gray-900 / gray-700 | #111827 / #374151 | Text and labels |
| Muted text | gray-500 | #6b7280 | Hints, dates, empty states |
| Primary | blue-600 | #2563eb | Primary button, links, running state |
| Success | green-500 / green-100 | #22c55e / #dcfce7 | Done, ready |
| Warning | amber-500 / amber-100 | #f59e0b / #fef3c7 | Waiting for approval |
| Danger | red-600 / red-100 | #dc2626 / #fee2e2 | Failed, blocked, delete |

Status colours are fixed across the app: running = blue, waiting for approval = amber, done = green, failed / blocked / rejected = red. Never use colour alone; every badge also has a text label.

## Typography

- Font: the system sans stack set in globals.css (Geist when loaded).
- Page title: text-2xl font-bold. Section title: font-semibold. Body: text-sm or base. Hints and meta: text-xs text-gray-500.
- Code and JSON: text-xs on a gray-900 background with gray-100 text.

## Spacing and shape

- Page padding p-8; gap between cards space-y-3; inside cards p-4 (lists) or p-6 (forms).
- Corners: rounded (4px) for cards, buttons and inputs. Shadow: shadow-sm only.
- Focus ring: ring-2 ring-blue-500 on every input.

## Components

All in frontend/components/ui and frontend/components/runs.

| Component | Use |
|-----------|-----|
| Button (primary, secondary, danger) and buttonClass() for links | Every action. Danger only for delete, reject and stop. |
| Field, Input, Textarea, Select | Every form control, label above, hint below. |
| Badge (gray, green, amber, red, blue) | Short status or tool labels. |
| StatusBadge | Run and step status with the standard colours. |
| StepGraph, StepDetail, ApprovalCard | Run page only. |

## Rules

- One primary button per screen.
- Every list has a loading state and an empty state with one sentence telling the user what to do.
- Errors appear in red text under the form or at the top of the page, in plain words.
- Ask before delete or stop (confirm dialog).
