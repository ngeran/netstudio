# Network Automation Management UI - Design Specification

## Design Philosophy

**Target Users:** Network engineers (junior to senior) with minimal web development knowledge.

**Core Principles:**
1. **Clarity over Cleverness**: Obvious beats clever
2. **Network-First Language**: Use network terminology, not web dev jargon
3. **Progressive Disclosure**: Show complexity only when needed
4. **Fail-Safe**: Prevent accidental destructive operations
5. **Real-time Feedback**: Always show what's happening

## Color Palette

### Light Mode
```
Primary (Brand):     #2563eb  (Blue 600)   - Action buttons, links
Secondary:           #7c3aed  (Violet 600) - Running tasks
Success:             #16a34a  (Green 600)  - Successful operations
Warning:             #ea580c  (Orange 600) - Warnings, downgrades
Error:               #dc2626  (Red 600)    - Failures
Background:          #ffffff  (White)
Surface:             #f9fafb  (Gray 50)
Surface Elevated:    #f3f4f6  (Gray 100)
Text Primary:        #111827  (Gray 900)
Text Secondary:      #6b7280  (Gray 500)
Border:              #e5e7eb  (Gray 200)
```

### Dark Mode
```
Primary:             #3b82f6  (Blue 500)
Secondary:           #8b5cf6  (Violet 500)
Success:             #22c55e  (Green 500)
Warning:             #f97316  (Orange 500)
Error:               #ef4444  (Red 500)
Background:          #0f172a  (Slate 900)
Surface:             #1e293b  (Slate 800)
Surface Elevated:    #334155  (Slate 700)
Text Primary:        #f8fafc  (Slate 50)
Text Secondary:      #94a3b8  (Slate 400)
Border:              #334155  (Slate 700)
```

## Typography

```
Font Family: Inter (system-ui fallback)
Headings:    700 (Bold)
Body:        400 (Regular)
Code:        JetBrains Mono

Scale:
  xs:   0.75rem (12px)  - Timestamps, meta info
  sm:   0.875rem (14px) - Secondary text
  base: 1rem (16px)     - Body text
  lg:   1.125rem (18px) - Subheadings
  xl:   1.25rem (20px)  - Card titles
  2xl:  1.5rem (24px)   - Page titles
  3xl:  1.875rem (30px) - Hero text
```

## Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│  Header (60px fixed)                                         │
│  [Logo]  Scripts  Executions  Devices  [Theme] [User]      │
├──────────┬──────────────────────────────────────────────────┤
│          │                                                   │
│ Sidebar  │             Main Content Area                    │
│ (240px)  │                                                   │
│          │                                                   │
│  Filters │   ┌──────────────────────────────────────────┐   │
│  Quick   │   │                                          │   │
│  Actions │   │          Dynamic Content                 │   │
│          │   │          (Route-based)                   │   │
│          │   │                                          │   │
│          │   └──────────────────────────────────────────┘   │
│          │                                                   │
└──────────┴──────────────────────────────────────────────────┘
```

## Page Layouts

### 1. Script Library Page

```
┌─────────────────────────────────────────────────────────────┐
│  Scripts                                      [+ New Script] │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  🔍 Search scripts...              [Category ▼] [Sort ▼]   │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐│
│  │ 📦 Code Upgrade  │  │ ⚙️ Config Backup │  │ 🔍 BGP Tool││
│  │                  │  │                  │  │            ││
│  │ Upgrade Juniper  │  │ Backup and       │  │ Monitor &  ││
│  │ device software  │  │ restore configs  │  │ manage BGP ││
│  │                  │  │                  │  │            ││
│  │ Category: Upgrade│  │ Category: Config │  │ Category:  ││
│  │ Modified: 2d ago │  │ Modified: 1w ago │  │ Routing    ││
│  │                  │  │                  │  │ Modified:  ││
│  │ [Execute] [Edit] │  │ [Execute] [Edit] │  │ 3d ago     ││
│  │                  │  │                  │  │            ││
│  └──────────────────┘  └──────────────────┘  │ [Execute]  ││
│                                                │ [Edit]     ││
│  ┌──────────────────┐  ┌──────────────────┐  │            ││
│  │ 🔌 Interface     │  │ 📊 State Capture │  └────────────┘│
│  │    Config        │  │                  │                │
│  │                  │  │ Pre/Post state   │                │
│  │ Configure network│  │ snapshots        │                │
│  │ interfaces       │  │                  │                │
│  │                  │  │ Category:        │                │
│  │ Category: Config │  │ Diagnostic       │                │
│  │ Modified: 5d ago │  │ Modified: 1d ago │                │
│  │                  │  │                  │                │
│  │ [Execute] [Edit] │  │ [Execute] [Edit] │                │
│  └──────────────────┘  └──────────────────┘                │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Interactions:**
- Hover: Card lifts with shadow
- Click card: Navigate to script detail page
- Click "Execute": Opens execution modal
- Click "Edit": Opens code editor

**Card States:**
- Default: Gray border
- Recently modified (< 7 days): Blue left border
- Has running task: Violet left border with pulse animation

---

### 2. Script Detail Page

```
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Scripts                                          │
├─────────────────────────────────────────────────────────────┤
│  📦 Code Upgrade                          [Edit] [Execute]  │
│  Category: Upgrade  •  Modified: 2 days ago                 │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 📝 Description                                         │ │
│  │                                                        │ │
│  │ Performs code upgrades on Juniper networking devices  │ │
│  │ such as SRX firewalls and EX switches. Supports       │ │
│  │ interactive selection of vendor, product, and release.│ │
│  │                                                        │ │
│  │ Validates current version, installs software, reboots │ │
│  │ device, and verifies new version.                     │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ ⚙️ Parameters                                          │ │
│  │                                                        │ │
│  │  Device Selection Method                               │ │
│  │  Type: Choice  •  Required                            │ │
│  │  Options: Load from inventory, Enter manually         │ │
│  │                                                        │ │
│  │  Devices (if manual)                                   │ │
│  │  Type: List of IPs  •  Optional                       │ │
│  │                                                        │ │
│  │  Credentials                                           │ │
│  │  Type: Object (username, password)  •  Required       │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 📊 Recent Executions                                   │ │
│  │                                                        │ │
│  │  ✅ Success  •  Dec 9, 2:30 PM  •  10.177.102.45      │ │
│  │  ✅ Success  •  Dec 8, 11:15 AM  •  3 devices         │ │
│  │  ❌ Failed   •  Dec 7, 4:45 PM  •  Connection timeout │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

### 3. Script Execution Modal

```
┌─────────────────────────────────────────────┐
│  Execute: Code Upgrade                  [✕] │
├─────────────────────────────────────────────┤
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │ 1️⃣ Device Selection                   │ │
│  │                                       │ │
│  │  ○ Load from inventory (hosts_data)  │ │
│  │  ○ Enter manually                    │ │
│  │                                       │ │
│  │  [If manual selected:]               │ │
│  │  Device IPs (one per line)           │ │
│  │  ┌─────────────────────────────────┐ │ │
│  │  │ 10.177.102.45                   │ │ │
│  │  │ 10.177.102.46                   │ │ │
│  │  │                                 │ │ │
│  │  └─────────────────────────────────┘ │ │
│  │                                       │ │
│  │  Username:  ┌─────────────────────┐  │ │
│  │             │ admin               │  │ │
│  │             └─────────────────────┘  │ │
│  │                                       │ │
│  │  Password:  ┌─────────────────────┐  │ │
│  │             │ •••••••••           │  │ │
│  │             └─────────────────────┘  │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │ 2️⃣ Upgrade Configuration              │ │
│  │                                       │ │
│  │  Vendor:  [Juniper ▼]                │ │
│  │  Product: [SRX300 ▼]                 │ │
│  │  Release: [21.2R1 ▼]                 │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  ⚠️ Warning: This will reboot devices      │
│                                             │
│             [Cancel]  [Execute Script]     │
└─────────────────────────────────────────────┘
```

**Form Validation:**
- Real-time validation on each field
- Red border + error message for invalid input
- "Execute Script" disabled until form valid
- Show warning badge for destructive operations

---

### 4. Execution Monitor Page

```
┌─────────────────────────────────────────────────────────────┐
│  Executing: Code Upgrade                            Running  │
│  Task ID: abc123  •  Started: 2:30 PM  •  Elapsed: 00:02:35│
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 🔄 Progress                                            │ │
│  │                                                        │ │
│  │  ████████████████████─────────────  65%               │ │
│  │                                                        │ │
│  │  Current Stage: Installing software on 10.177.102.45  │ │
│  │                                                        │ │
│  │  ✅ Connected to devices (2/2)                        │ │
│  │  ✅ Validated software versions                       │ │
│  │  🔄 Installing software (1/2)                         │ │
│  │  ⏳ Rebooting devices                                  │ │
│  │  ⏳ Verifying new versions                             │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 📋 Live Logs                              [Auto-scroll]│ │
│  │                                            [Download] │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │                                                        │ │
│  │ 14:30:15  INFO     Starting code upgrade process      │ │
│  │ 14:30:16  INFO     Loading vendor data from YAML      │ │
│  │ 14:30:17  INFO     Selected vendor: Juniper           │ │
│  │ 14:30:18  INFO     Connecting to 10.177.102.45...     │ │
│  │ 14:30:22  SUCCESS  Connected to 10.177.102.45         │ │
│  │ 14:30:23  INFO     Current version: 20.4R3            │ │
│  │ 14:30:24  INFO     Target version: 21.2R1             │ │
│  │ 14:30:25  INFO     Checking software image...         │ │
│  │ 14:30:28  SUCCESS  Image found on device              │ │
│  │ 14:30:29  INFO     Installing software package...     │ │
│  │ 14:32:15  SUCCESS  Installation complete              │ │
│  │ 14:32:16  INFO     Rebooting device...                │ │
│  │                                                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│                               [Cancel Execution] [Detach]  │
└──────────────────────────────────────────────────────────────┘
```

**Real-time Updates:**
- Progress bar animates as tasks complete
- Logs append in real-time via WebSocket
- Stage checklist updates with checkmarks/spinners
- Elapsed time updates every second

**States:**
- **Running**: Violet border, spinner animation
- **Success**: Green border, checkmark
- **Failed**: Red border, error icon
- **Cancelled**: Gray border, stop icon

---

### 5. Executions History Page

```
┌─────────────────────────────────────────────────────────────┐
│  Execution History                                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  🔍 Search...    [Script ▼] [Status ▼] [Date Range ▼]     │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Task ID     Script         Status    Started    Time   │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ abc123  Code Upgrade      ✅ Success  2:30 PM   8m 42s │ │
│  │         10.177.102.45                                  │ │
│  │         [View Details] [View Logs] [Retry]            │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ def456  BGP Toolbox       ❌ Failed   1:15 PM   2m 03s │ │
│  │         Connection timeout                             │ │
│  │         [View Details] [View Logs] [Retry]            │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ ghi789  Config Backup     ✅ Success  11:20 AM  45s    │ │
│  │         3 devices                                      │ │
│  │         [View Details] [View Logs]                    │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ jkl012  State Capture     🔄 Running  10:05 AM  5m 12s │ │
│  │         In progress...                                 │ │
│  │         [Monitor] [Cancel]                            │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│                            ← 1 2 3 4 5 ... 23 →            │
└──────────────────────────────────────────────────────────────┘
```

**Features:**
- Filter by script, status, date range
- Sortable columns
- Pagination
- Quick actions (View, Retry, Cancel)

---

### 6. Code Editor Page

```
┌─────────────────────────────────────────────────────────────┐
│  Editing: code_upgrade.py                [Save] [Cancel]    │
├─────────────────────────────────────────────────────────────┤
│  ┌─ Metadata ──────────────────────────────────────────────┐│
│  │ Script Name:  [Code Upgrade                          ]  ││
│  │ Category:     [Upgrade ▼]                               ││
│  │ Description:  ┌──────────────────────────────────────┐  ││
│  │               │ Upgrade Juniper device software      │  ││
│  │               │                                      │  ││
│  │               └──────────────────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  ┌─ Code ─────────────────────────────────────────────────┐ │
│  │   1  import logging                                    │ │
│  │   2  import os                                         │ │
│  │   3  from typing import List, Dict                     │ │
│  │   4                                                    │ │
│  │   5  from jnpr.junos import Device                     │ │
│  │   6  from jnpr.junos.utils.sw import SW                │ │
│  │   7                                                    │ │
│  │   8  logger = logging.getLogger(__name__)              │ │
│  │   9                                                    │ │
│  │  10  def code_upgrade():                               │ │
│  │  11      """Perform code upgrade on selected..."""     │ │
│  │  12      upgrade_status = []                           │ │
│  │  13      try:                                          │ │
│  │  14          logger.info("Starting upgrade...")        │ │
│  │                                                        │ │
│  │                                              Line 14   │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ⚠️ Syntax validation: ✅ No errors                         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Editor Features:**
- Syntax highlighting (Python)
- Line numbers
- Real-time syntax validation
- Auto-save (draft mode)
- Confirm before saving
- Show git diff if file is tracked

---

## Component Library

### Buttons

```
Primary:   [Blue bg, white text]      "Execute Script"
Secondary: [Gray border, dark text]   "Cancel"
Danger:    [Red bg, white text]       "Delete Script"
Ghost:     [Transparent, hover gray]  "Edit"
Icon:      [Circle, icon only]        [⚙️]
```

**States:**
- Default: Solid color
- Hover: Slightly darker
- Active: Even darker
- Disabled: 50% opacity, no pointer
- Loading: Spinner replaces text

---

### Status Badges

```
✅ Success   [Green bg, dark green text]
❌ Failed    [Red bg, dark red text]
🔄 Running   [Violet bg, dark violet text, pulse animation]
⏳ Pending   [Yellow bg, dark yellow text]
⏸️ Paused    [Gray bg, dark gray text]
```

---

### Cards

```
Default:
┌─────────────────────┐
│                     │  Shadow: sm
│   Card Content      │  Border: 1px gray
│                     │  Padding: 1.5rem
└─────────────────────┘

Hover:
┌─────────────────────┐
│                     │  Shadow: md
│   Card Content      │  Border: 1px blue
│                     │  Transform: translateY(-2px)
└─────────────────────┘
```

---

### Form Inputs

```
Text Input:
┌─────────────────────────────────┐
│ Value here                      │
└─────────────────────────────────┘

Error State:
┌─────────────────────────────────┐
│ Invalid value                   │ Red border
└─────────────────────────────────┘
❌ Error message here

Success State:
┌─────────────────────────────────┐
│ Valid value                     │ Green border
└─────────────────────────────────┘
✅ Looks good
```

---

### Progress Indicators

**Linear Progress Bar:**
```
████████████──────────  60%
```

**Circular Spinner:**
```
   ⣾  Loading...
```

**Step Progress:**
```
● ─────── ○ ─────── ○ ─────── ○
Step 1    Step 2    Step 3    Step 4
```

---

## Responsive Behavior

### Desktop (≥1024px)
- Sidebar always visible
- Cards in grid: 3 columns
- Logs: Full width

### Tablet (768px - 1023px)
- Sidebar collapsible
- Cards in grid: 2 columns
- Logs: Full width

### Mobile (< 768px)
- Sidebar hidden, hamburger menu
- Cards in grid: 1 column (stacked)
- Logs: Horizontal scroll for long lines
- Execution modal: Full screen

---

## Accessibility (a11y)

- **Keyboard Navigation**: All actions accessible via Tab/Enter
- **ARIA Labels**: Screen reader support
- **Focus Indicators**: Visible focus rings
- **Color Contrast**: WCAG AA compliant (4.5:1 ratio)
- **Alt Text**: All icons have descriptive labels
- **Skip Links**: Jump to main content

---

## Dark Mode Toggle

Located in top right header:

```
Light Mode: ☀️
Dark Mode:  🌙

Toggle animates smoothly (0.2s transition)
Persists in localStorage
```

---

## Animations

**Subtle & Purposeful:**

- **Page Transitions**: 200ms fade-in
- **Card Hover**: 150ms lift + shadow
- **Button Hover**: 100ms color change
- **Progress Bar**: Smooth 300ms width change
- **Spinner**: Continuous rotation
- **Pulse**: 2s infinite (running tasks)
- **Toast Notifications**: Slide in from top-right

**No Animations:**
- Respect `prefers-reduced-motion`
- Disable for accessibility

---

## Loading States

**Page Load:**
```
  ⣾  Loading scripts...
```

**Button Click:**
```
[⣾ Executing...]
```

**Skeleton Screens:**
```
┌─────────────────────┐
│ ████████            │  Gray shimmer
│ ██████              │
│ ████████████        │
└─────────────────────┘
```

---

## Error States

**Empty State:**
```
  📭

  No scripts found

  Upload your first script to get started

  [+ Upload Script]
```

**Error State:**
```
  ⚠️

  Failed to load scripts

  Check your connection and try again

  [Retry]
```

**404 Page:**
```
  🔍

  Page not found

  The page you're looking for doesn't exist

  [← Back to Scripts]
```

---

## Mobile Considerations

- Touch targets: Minimum 44x44px
- Swipe gestures: Left/right on cards
- Pull-to-refresh on lists
- Bottom navigation bar (easier thumb reach)
- Sticky "Execute" button at bottom

---

This design balances professional aesthetics with practical usability for network engineers. The visual language mirrors network concepts (connections, flows, states) while keeping interactions straightforward.
