# Trapdoor Mobile - UI Design Language

## Design Philosophy

**"n8n designed by someone classy from the 70s"**

- Crisp, functional modernism
- Bold color blocks as functional indicators
- Generous whitespace
- Helvetica Neue / SF Pro
- Simple, purposeful animations
- Grid-based layout
- No decoration - every element serves a purpose

## Color System

Colors indicate **state and function**, not decoration.

```
┌──────────────────────────────────────┐
│ ONLINE    │ #00C853  │ ███████████  │  Agents active
│ BUSY      │ #FF6D00  │ ███████████  │  Task executing
│ IDLE      │ #0091EA  │ ███████████  │  Available
│ OFFLINE   │ #616161  │ ███████████  │  Disconnected
│ ERROR     │ #D50000  │ ███████████  │  Failure state
│ PENDING   │ #FFD600  │ ███████████  │  Waiting
│           │          │              │
│ BACKGROUND│ #FAFAFA  │ ███████████  │  Surface
│ SURFACE   │ #FFFFFF  │ ███████████  │  Cards
│ TEXT      │ #212121  │ ███████████  │  Primary text
│ TEXT_SEC  │ #757575  │ ███████████  │  Secondary
└──────────────────────────────────────┘
```

## Typography

```
TITLE       56pt  SF Pro Display Medium
HEADING     28pt  SF Pro Display Regular
BODY        17pt  SF Pro Text Regular
CAPTION     13pt  SF Pro Text Regular
LABEL       11pt  SF Pro Text Medium  (uppercase, tracked)
```

## Main Dashboard

```
┌─────────────────────────────────────┐
│                                     │
│  TRAPDOOR                           │  ← 28pt, tracked
│                                     │
│  ┌───────────────────────────────┐ │
│  │                               │ │
│  │         4                     │ │  ← 56pt number
│  │      AGENTS                   │ │  ← 11pt label
│  │                               │ │
│  │    ███  ██   ██   ██          │ │  ← Big colored blocks
│  │   ONLINE BUSY IDLE OFF        │ │     representing agents
│  │                               │ │
│  └───────────────────────────────┘ │
│                                     │
│                                     │
│  ┌─────────────────┐               │
│  │                 │               │  ← Square buttons
│  │    COMMAND      │               │     with single word
│  │                 │               │     Big touch targets
│  └─────────────────┘               │
│                                     │
│  ┌─────────────────┐               │
│  │                 │               │
│  │     CAMERA      │               │
│  │                 │               │
│  └─────────────────┘               │
│                                     │
│  ┌─────────────────┐               │
│  │                 │               │
│  │     SEARCH      │               │
│  │                 │               │
│  └─────────────────┘               │
│                                     │
│                                     │
│  TASKS                              │  ← Section header
│                                     │
│  ┌───────────────────────────────┐ │
│  │ ██████████████░░░░░░░  68%    │ │  ← Progress bar
│  │ Backup repositories            │ │     Bold color fill
│  │ black · 2m 14s                 │ │     Simple percentage
│  └───────────────────────────────┘ │
│                                     │
│  ┌───────────────────────────────┐ │
│  │ ████░░░░░░░░░░░░░░░░░  14%    │ │
│  │ Train model                    │ │
│  │ nvidia-spark · 14m 3s          │ │
│  └───────────────────────────────┘ │
│                                     │
│                                     │
│  AGENTS                             │
│                                     │
│  ┌─────┬─────────────────────────┐ │
│  │  ●  │ black                   │ │  ← Colored dot
│  │     │ Terminal                │ │     Status indicator
│  │     │ 3 tasks completed       │ │     Minimal text
│  └─────┴─────────────────────────┘ │
│                                     │
│  ┌─────┬─────────────────────────┐ │
│  │  ●  │ silver-fox              │ │
│  │     │ Terminal                │ │
│  │     │ Idle                    │ │
│  └─────┴─────────────────────────┘ │
│                                     │
└─────────────────────────────────────┘
```

## Command Input

```
┌─────────────────────────────────────┐
│                                     │
│                                     │
│                                     │
│  What should I do?                  │  ← Simple question
│                                     │
│  ┌───────────────────────────────┐ │
│  │                               │ │
│  │ [Text input area]             │ │  ← Large, clear input
│  │                               │ │
│  └───────────────────────────────┘ │
│                                     │
│                                     │
│  Or choose:                         │
│                                     │
│  Backup repos                       │  ← Past commands
│  Update CLAUDE.md files             │     as suggestions
│  Check Trapdoor status              │     Single tap
│                                     │
│                                     │
│  ┌───────────┐  ┌──────────────┐   │
│  │  CANCEL   │  │  SEND        │   │  ← Clear actions
│  └───────────┘  └──────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

## Task Detail View

```
┌─────────────────────────────────────┐
│  ←  TASK                            │
│                                     │
│                                     │
│  ████████████████████░░░  82%       │  ← Large progress
│                                     │
│                                     │
│  Backup repositories                │  ← Task name, 28pt
│                                     │
│  Started  2m 14s ago                │
│  Agent    black                     │
│  Status   In progress               │
│                                     │
│                                     │
│  ┌───────────────────────────────┐ │
│  │                               │ │
│  │  Processing repo 43 of 53     │ │  ← Live updates
│  │  03:14:23                     │ │     Timestamped
│  │                               │ │
│  │  Copied 8.2 GB                │ │
│  │  03:14:19                     │ │
│  │                               │ │
│  │  Verifying checksums          │ │
│  │  03:14:12                     │ │
│  │                               │ │
│  └───────────────────────────────┘ │
│                                     │
│                                     │
│  ┌─────────────────┐               │
│  │                 │               │
│  │     CANCEL      │               │  ← Single action
│  │                 │               │     If applicable
│  └─────────────────┘               │
│                                     │
└─────────────────────────────────────┘
```

## Agent Detail View

```
┌─────────────────────────────────────┐
│  ←  AGENT                           │
│                                     │
│                                     │
│  ●  black                           │  ← Large status dot
│                                     │     Agent name
│                                     │
│  Terminal agent                     │
│  100.70.207.76                      │
│  Connected 4h 23m                   │
│                                     │
│                                     │
│  CAPABILITIES                       │
│                                     │
│  Filesystem                         │  ← Simple list
│  Git operations                     │     No icons
│  Process management                 │     Just text
│  MCP servers                        │
│                                     │
│                                     │
│  ACTIVITY                           │
│                                     │
│  3 tasks completed today            │
│  Last: Backup repositories          │
│  14m 23s ago                        │
│                                     │
│                                     │
│  ┌─────────────────┐               │
│  │                 │               │
│  │   NEW TASK      │               │
│  │                 │               │
│  └─────────────────┘               │
│                                     │
└─────────────────────────────────────┘
```

## Memory Search

```
┌─────────────────────────────────────┐
│  ←  MEMORY                          │
│                                     │
│  ┌───────────────────────────────┐ │
│  │ How did I...                  │ │  ← Search bar
│  └───────────────────────────────┘ │
│                                     │
│                                     │
│  WORKFLOWS                          │
│                                     │
│  ┌───────────────────────────────┐ │
│  │ Backup repositories           │ │  ← Past workflow
│  │                               │ │     Tap to reuse
│  │ Last used 1 month ago         │ │
│  │ Executed 12 times             │ │
│  └───────────────────────────────┘ │
│                                     │
│  ┌───────────────────────────────┐ │
│  │ Deploy to production          │ │
│  │                               │ │
│  │ Last used 2 weeks ago         │ │
│  │ Executed 47 times             │ │
│  └───────────────────────────────┘ │
│                                     │
│  ┌───────────────────────────────┐ │
│  │ Configure nginx               │ │
│  │                               │ │
│  │ Last used 3 months ago        │ │
│  │ Executed 3 times              │ │
│  └───────────────────────────────┘ │
│                                     │
└─────────────────────────────────────┘
```

## Notifications

```
┌─────────────────────────────────────┐
│                                     │
│  ✓                                  │  ← Large checkmark
│                                     │     or status symbol
│                                     │
│  Backup complete                    │  ← Clear message
│                                     │
│  53 repositories                    │  ← Key metric
│  8.2 GB transferred                 │
│  14m 23s                            │
│                                     │
│  black → silver-fox                 │  ← Simple routing info
│                                     │
│  ┌───────────┐                      │
│  │   VIEW    │                      │  ← Single action
│  └───────────┘                      │
│                                     │
└─────────────────────────────────────┘
```

## Animation Principles

**All animations are functional, not decorative**

1. **State Transitions** (200ms ease-out)
   - Agent status: Circle fills with color
   - Task progress: Bar grows smoothly
   - Screen transitions: Simple slide

2. **Loading States** (1000ms loop)
   - Single pulsing dot
   - No spinners, no complex animations

3. **Success/Error** (300ms)
   - Color change
   - Simple scale animation (1.0 → 1.05 → 1.0)

4. **Updates** (fade in 150ms)
   - New messages appear with quick fade
   - No sliding or bouncing

## Component Library

### Button
```
┌─────────────────┐
│                 │
│   BUTTON TEXT   │  ← 13pt uppercase, tracked
│                 │     Single color fill
└─────────────────┘     Generous padding (16pt all sides)
```

### Status Indicator
```
● TEXT                  ← 24pt dot + 17pt text
                          Color indicates state
```

### Progress Bar
```
████████░░░░░░░  68%   ← 8pt height
                          Bold color fill
                          Percentage right-aligned
```

### Card
```
┌───────────────────────────────┐
│                               │  ← White surface
│  Title text                   │     16pt padding
│  Secondary information        │     Drop shadow: 0 2 8 rgba(0,0,0,0.08)
│                               │
└───────────────────────────────┘
```

### Input Field
```
┌───────────────────────────────┐
│                               │  ← 44pt height minimum
│  [Input text]                 │     17pt text
│                               │     1pt border
└───────────────────────────────┘
```

## Dark Mode

```
BACKGROUND │ #121212  │  Not pure black
SURFACE    │ #1E1E1E  │  Elevated surfaces
TEXT       │ #FFFFFF  │  Primary text
TEXT_SEC   │ #AAAAAA  │  Secondary text

All status colors remain the same for consistency
```

## Grid System

- 8pt base unit
- 16pt gutters
- 24pt margins
- Content max width: 375pt (mobile)
- All spacing in multiples of 8

## Interaction Design

**Touch Targets**
- Minimum 44×44pt
- Prefer square buttons for primary actions
- Cards are tappable in full

**Feedback**
- Instant visual response (color change)
- Haptic feedback on actions
- No loading spinners unless >2 seconds

**Navigation**
- Simple back button (←)
- No hamburger menus
- Tab bar for main sections (if needed)

## Success States

Keep them understated:
```
✓  Task complete        ← Simple checkmark
                           Brief color flash
                           Haptic feedback
```

## Error States

Clear and actionable:
```
!  Connection failed    ← Exclamation mark
                           Error color
                           Retry button below
```

## Implementation Notes

**React Native Components**
```typescript
// Button component
<TouchableOpacity style={styles.button}>
  <Text style={styles.buttonText}>BUTTON TEXT</Text>
</TouchableOpacity>

const styles = StyleSheet.create({
  button: {
    backgroundColor: '#0091EA',
    paddingVertical: 16,
    paddingHorizontal: 24,
    borderRadius: 0,  // Square corners
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '500',
    letterSpacing: 1,
    textTransform: 'uppercase',
  }
});
```

**Status Dot**
```typescript
<View style={styles.statusContainer}>
  <View style={[styles.dot, { backgroundColor: statusColor }]} />
  <Text style={styles.statusText}>{agentName}</Text>
</View>

const styles = StyleSheet.create({
  dot: {
    width: 24,
    height: 24,
    borderRadius: 12,
  },
  statusText: {
    fontSize: 17,
    marginLeft: 12,
  }
});
```

**Progress Bar**
```typescript
<View style={styles.progressContainer}>
  <View style={styles.progressTrack}>
    <View style={[styles.progressFill, { width: `${progress}%` }]} />
  </View>
  <Text style={styles.progressText}>{progress}%</Text>
</View>

const styles = StyleSheet.create({
  progressTrack: {
    height: 8,
    backgroundColor: '#E0E0E0',
    flex: 1,
  },
  progressFill: {
    height: 8,
    backgroundColor: '#00C853',
  },
  progressText: {
    fontSize: 17,
    marginLeft: 12,
    minWidth: 50,
  }
});
```

## Design References

**Inspiration Sources**:
- Braun product design (Dieter Rams)
- Vitsœ furniture interface
- Early Apple Lisa/Macintosh UI
- Swiss International Style posters
- Massimo Vignelli's work
- n8n workflow editor
- Linear app (modern execution)

**Key Principle**:
*"Weniger, aber besser" - Less, but better*

Every element must justify its existence through function.
