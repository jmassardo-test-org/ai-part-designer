# User Stories

**Version:** 2.1  
**Last Updated:** January 25, 2026  

> **Note:** For detailed user stories for Phase 4 remaining features, see [docs/user-stories-phase-4.md](docs/user-stories-phase-4.md)  
> For Phase 5+ enhancement stories, see [docs/user-stories-phase-5.md](docs/user-stories-phase-5.md)

---

## Status Legend
- ✅ **Implemented** - Feature is complete and tested
- 🔄 **Partial** - Feature is partially implemented
- 🔴 **Broken** - Feature exists but is broken/not working
- ❌ **Not Started** - Feature not yet implemented

---

# 🔴 Critical Bug Fixes (Sprint 36 - BLOCKER)

> **Priority:** These issues MUST be fixed before any new feature work.

## Bug Fix 1: Dashboard Recent Designs 🔴
**As a** returning user,  
**I want** to see my actual recent designs on the dashboard,  
**so that** I can quickly resume my work.

**Status:** 🔴 BROKEN - Shows static/mock data, causes errors

**Current Issue:**  
- Dashboard displays hardcoded sample data instead of user's real designs
- Clicking on designs may cause errors

**Acceptance Criteria:**
- [ ] Dashboard fetches actual user designs from API
- [ ] Shows loading skeleton while fetching
- [ ] Shows empty state if no designs exist
- [ ] Each design links to correct detail page
- [ ] No console errors

**Sprint:** 36 | **Points:** 5 | **Priority:** P0

---

## Bug Fix 2: Projects Page Error 🔴
**As a** user,  
**I want** to view my projects,  
**so that** I can organize my work.

**Status:** 🔴 BROKEN - `TypeError: projects.filter is not a function`

**Current Issue:**  
- Page crashes with filter error
- API response format not handled correctly
- Projects state may not be initialized as array

**Acceptance Criteria:**
- [ ] Projects page loads without errors
- [ ] Projects list displays correctly
- [ ] Empty state shown when no projects
- [ ] Filtering works when projects exist

**Sprint:** 36 | **Points:** 3 | **Priority:** P0

---

## Bug Fix 3: File Upload 🔴
**As a** user,  
**I want** to upload CAD files and datasheets,  
**so that** I can use them in my designs.

**Status:** 🔴 BROKEN - Upload functionality not working

**Current Issue:**  
- File upload fails (exact cause TBD - frontend/backend/storage)

**Acceptance Criteria:**
- [ ] Can upload STEP files successfully
- [ ] Can upload STL files successfully
- [ ] Can upload PDF files successfully
- [ ] Upload progress indicator works
- [ ] Error messages shown on failure
- [ ] Uploaded files appear in file list

**Sprint:** 36 | **Points:** 5 | **Priority:** P0

---

## Bug Fix 4: Templates Not Available 🔴
**As a** user,  
**I want** to browse and use templates,  
**so that** I can quickly start common designs.

**Status:** 🔴 BROKEN - No templates exist; no way to create them

**Current Issue:**  
- Template browser shows empty/error state
- No seed templates available
- No mechanism to create user templates

**Acceptance Criteria:**
- [ ] At least 10 seed templates available
- [ ] Templates visible in template browser
- [ ] Can use a template to start a design
- [ ] Can save a design as template ("Save as Template")
- [ ] User templates appear in "My Templates" section

**Sprint:** 36 | **Points:** 13 | **Priority:** P0

---

## Bug Fix 5: Sharing Page Empty 🔴
**As a** user,  
**I want** to see shared designs and share my own,  
**so that** I can collaborate with others.

**Status:** 🔴 BROKEN - Sharing page has no implementation

**Current Issue:**  
- Sharing page renders but has no functional content
- Backend APIs exist but aren't connected

**Acceptance Criteria:**
- [ ] Sharing page loads without errors
- [ ] "Shared With Me" section shows designs others shared
- [ ] "My Shares" section shows designs user has shared
- [ ] Can share a design via email
- [ ] Can revoke shares

**Sprint:** 36 | **Points:** 10 | **Priority:** P1

---

## Bug Fix 6: Save Design from Chat 🔴
**As a** user generating designs,  
**I want** to save a generated design to my library,  
**so that** I can find and edit it later.

**Status:** 🔴 MISSING - Only download option exists; cannot save to library

**Current Issue:**  
- Chat only shows "Download" button after generation
- No "Save to My Designs" option
- Generated designs may not persist to user's library

**Acceptance Criteria:**
- [ ] "Save to My Designs" button visible after generation
- [ ] Button is prominent (primary styling)
- [ ] Clicking saves design to user's library
- [ ] Success confirmation shown
- [ ] Design appears in "My Designs" / "Recent Designs"
- [ ] Saved design can be reopened later

**Sprint:** 36 | **Points:** 8 | **Priority:** P0

---

# Core User Experience Stories

### User Story 1: Intuitive Navigation ✅
**As a** user who is interested in AI design tools,  
**I want** to be able to easily navigate the interface,  
**so that** I can efficiently access the tools I need for my design projects.  

**Status:** ✅ Implemented (Sprint 1-14)

### Tasks:  
- ✅ Design an intuitive main menu.  
- ✅ Include tooltips for all interface elements.  

---

### User Story 2: Design Collaboration 🔄
**As a** designer working on a collaborative project,  
**I want** to share my design drafts with team members,  
**so that** we can offer feedback and make necessary revisions together.  

**Status:** 🔄 Partial - Backend APIs exist, UI integration pending

### Tasks:  
- ✅ Implement a sharing feature with customizable permissions (API ready)
- 🔄 Set up a commenting system for feedback (in-memory, needs DB)
- 🔴 Integrate sharing UI into main application (BROKEN - see Bug Fix 5)
- ❌ Real-time collaboration notifications

**See:** [US-9001, US-9002, US-9003](docs/user-stories-phase-4.md#epic-9-collaboration-features)

---

### User Story 3: Onboarding Tutorial 🔄
**As a** new user,  
**I want** a guided tutorial when I first access the application,  
**so that** I can quickly learn how to use the features.

**Status:** 🔄 Partial - Component exists, not integrated with login flow

### Tasks:  
- ✅ Develop an onboarding experience with step-by-step instructions
- ❌ Trigger on first login
- ❌ Track completion in user profile
- ❌ Include example projects to illustrate feature use

**See:** [US-10001, US-10002](docs/user-stories-phase-4.md#epic-10-onboarding-experience)

---

### User Story 4: Accessibility Support ✅
**As a** user of accessibility tools,  
**I want** the application to be compatible with screen readers,  
**so that** I can navigate the design tools independently.  

**Status:** ✅ Implemented (Sprint 19-20)

### Tasks:  
- ✅ Conduct an accessibility audit of the user interface
- ✅ Implement ARIA labels and keyboard navigation
- ✅ WCAG 2.1 AAA compliance

---

### User Story 5: Recent Projects Dashboard 🔴
**As a** returning user,  
**I want** to see a history of my recent projects on the dashboard,  
**so that** I can quickly resume my work without searching.

**Status:** 🔴 BROKEN - See Bug Fix 1

### Tasks:  
- ✅ Create a section on the dashboard for recent projects
- 🔴 Implement actual data fetching (BROKEN)
- ✅ Implement a project preview feature

---

# Reference Components & Enclosure Generation Stories

## User Story 6: Upload Reference Components 🔴
**As a** maker designing an electronics enclosure,  
**I want** to upload PDF datasheets or CAD files of the components I'm using,  
**so that** the AI can automatically extract dimensions and mounting specifications.

**Status:** 🔴 BROKEN - File upload not working (See Bug Fix 3)

### Acceptance Criteria:
- ✅ Upload PDF datasheet and extract key dimensions
- ✅ Upload STEP file and extract bounding box + features
- ✅ Upload STL file and extract dimensions
- ✅ View extracted specifications for verification
- ✅ Edit/correct extracted data if needed
- ✅ Save component to project or personal library

### **NEW: Update Component Files** ❌
- ❌ Replace/update CAD file for existing component
- ❌ Replace/update PDF datasheet
- ❌ View file version history
- ❌ Restore previous file versions

**See:** [US-1001, US-1002](docs/user-stories-phase-4.md#epic-1-component-file-management)

---

## User Story 7: AI Dimension Extraction from PDFs 🔄
**As a** user with a component datasheet PDF,  
**I want** the AI to automatically find and extract mechanical dimensions,  
**so that** I don't have to manually enter this data.

**Status:** 🔄 Partial - Basic extraction works, GPT-4 Vision not integrated

### Acceptance Criteria:
- 🔄 Extract overall dimensions (L × W × H) - Basic working
- ❌ GPT-4 Vision analysis of mechanical drawings
- ❌ Identify mounting hole positions from drawings
- ❌ Detect connector cutout requirements visually
- ❌ Confidence scores for extracted data
- ❌ Extraction review UI with overlays

**See:** [US-3001, US-3002, US-3003](docs/user-stories-phase-4.md#epic-3-ai-dimension-extraction)

---

## User Story 8: Use Component Library ✅
**As a** user designing an enclosure for a Raspberry Pi 5,  
**I want** to select the Pi from a pre-built component library,  
**so that** I can quickly start my design with accurate specifications.

**Status:** ✅ Implemented (Sprint 29-30)

### Acceptance Criteria:
- ✅ Browse component library by category
- ✅ Search components by name
- ✅ View component specifications before adding
- ✅ Add component to current design
- ✅ See 3D preview of component (if available)
- ❌ Community-submitted components (moderated) - Future

---

## User Story 9: Generate Enclosure Around Components ✅
**As a** user who has added reference components to my project,  
**I want** to generate an enclosure for these components,  
**so that** it creates a properly-sized box with mounting points and cutouts.

**Status:** ✅ Implemented (Sprint 31-32)

### Acceptance Criteria:
- ✅ Enclosure sized to fit all components with clearance
- ✅ Mounting standoffs at correct hole positions
- ✅ Cutouts aligned with ports/connectors
- ❌ Ventilation near heat-generating components - Partial
- ✅ Lid with snap-fit or screw mounts
- ❌ Cable routing channels - Future

---

## User Story 10: Spatial Layout Tool 🔄
**As a** user arranging multiple components in an enclosure,  
**I want** a visual tool to position components relative to each other,  
**so that** I can optimize the layout before generating the enclosure.

**Status:** 🔄 Partial - Basic editor implemented, advanced features pending

### Acceptance Criteria:
- ✅ 2D canvas showing component footprints
- ✅ Drag components to position them
- ✅ Rotate components (90° increments)
- ❌ Show clearance zones
- ❌ Collision warnings
- ❌ Auto-arrange option
- ✅ Export layout to 3D generation

**See:** [US-11001, US-11002, US-11003](docs/user-stories-phase-4.md#epic-11-layout-editor-enhancements)

---

## User Story 11: Custom Mounting Options 🔄
**As a** user generating an enclosure,  
**I want** to specify mounting preferences (standoffs, clips, brackets, rails),  
**so that** components are secured appropriately for my use case.

**Status:** 🔄 Partial - Basic standoffs implemented, advanced types pending

### Acceptance Criteria:
- ✅ Select mounting type per component (basic types)
- ✅ Configure standoff dimensions
- ❌ Snap-fit clips for tool-less assembly
- ❌ DIN rail mounting for industrial use
- ❌ Wall mount brackets
- ❌ Heat-set insert options for 3D printing

**See:** [US-5001, US-5002, US-5003, US-5004](docs/user-stories-phase-4.md#epic-5-mounting-type-expansion)

---

## User Story 12: Enclosure Style Templates 🔄
**As a** user generating an enclosure,  
**I want** to choose from style templates (minimal, rugged, vented, stackable),  
**so that** the design matches my aesthetic and functional needs.

**Status:** 🔄 Partial - 3 basic styles implemented, 5+ needed

### Acceptance Criteria:
- 🔄 At least 5 enclosure style templates (3 implemented)
- ✅ Style preview with component layout
- ✅ Customizable wall thickness
- ✅ Closure type selection (snap, screws, slide)
- ❌ Rugged style (thick walls, gasket)
- ❌ Stackable style (interlocking)
- ❌ Industrial/Desktop/Handheld styles

**See:** [US-4001, US-4002, US-4003, US-4004](docs/user-stories-phase-4.md#epic-4-enclosure-style-templates)

---

# NEW: File Operations Stories

## User Story 13: File Alignment & Combination ❌
**As a** maker combining multiple CAD files,  
**I want** to align and combine them into an assembly,  
**so that** I can create complex designs from separate components.

**Status:** ❌ Not Started

### Acceptance Criteria:
- ❌ Align files by face, edge, center, or origin
- ❌ Interactive 3D alignment editor
- ❌ Save aligned files as assembly
- ❌ Export combined assembly

**See:** [US-2001, US-2002, US-2003](docs/user-stories-phase-4.md#epic-2-file-alignment--cad-combination)

---

# NEW: Monetization Stories

## User Story 14: Subscription & Payment ❌
**As a** user who wants more features,  
**I want** to upgrade to a paid subscription,  
**so that** I can access priority queue and more export options.

**Status:** ❌ Not Started

### Acceptance Criteria:
- ❌ View pricing page with tier comparison
- ❌ Subscribe via Stripe Checkout
- ❌ Manage subscription in billing portal
- ❌ Feature limits enforced by tier

**See:** [US-6001, US-6002, US-6003, US-6004](docs/user-stories-phase-4.md#epic-6-payment--subscription)

---

## User Story 15: Social Login ❌
**As a** user who prefers not to create a new password,  
**I want** to sign in with Google or GitHub,  
**so that** I can access the platform quickly.

**Status:** ❌ Not Started

### Acceptance Criteria:
- ❌ Sign in with Google
- ❌ Sign in with GitHub
- ❌ Link OAuth to existing account

**See:** [US-7001, US-7002, US-7003](docs/user-stories-phase-4.md#epic-7-oauth-authentication)

---

# NEW: Real-time Features Stories

## User Story 16: Real-time Job Updates ❌
**As a** user with jobs running in the background,  
**I want** to see real-time progress updates,  
**so that** I know when my designs are ready.

**Status:** ❌ Not Started (polling used currently)

### Acceptance Criteria:
- ❌ WebSocket connection for live updates
- ❌ Job progress updates in real-time
- ❌ Notification when job completes

**See:** [US-8001, US-8002](docs/user-stories-phase-4.md#epic-8-real-time-updates)

---

# Summary: Implementation Status

| Epic | Stories | Implemented | Partial | Not Started |
|------|---------|-------------|---------|-------------|
| Core UX | US1-5 | 2 | 2 | 1 |
| Components | US6-8 | 1 | 1 | 1 |
| Enclosure | US9-12 | 1 | 3 | 0 |
| File Operations | US13 | 0 | 0 | 1 |
| Monetization | US14-15 | 0 | 0 | 2 |
| Real-time | US16 | 0 | 0 | 1 |
| **Subtotal (Phase 4)** | **16** | **4** | **6** | **6** |

---

# 🔴 Critical Bugs Summary (Sprint 36)

| Bug | Description | Points | Priority |
|-----|-------------|--------|----------|
| Bug Fix 1 | Dashboard Recent Designs - static data | 5 | P0 |
| Bug Fix 2 | Projects Page - filter error | 3 | P0 |
| Bug Fix 3 | File Upload - not working | 5 | P0 |
| Bug Fix 4 | Templates - none available, can't create | 13 | P0 |
| Bug Fix 5 | Sharing Page - not implemented | 10 | P1 |
| Bug Fix 6 | Save Design from Chat - missing | 8 | P0 |
| **Total** | | **44** | |

**Sprint 36 Goal:** Fix all blocking bugs before feature work resumes.

---

# Enhancement Stories (Phase 5+)

> **Full Details:** See [docs/user-stories-phase-5.md](docs/user-stories-phase-5.md)

## AI Assistant Enhancements

### User Story 17: Slash Commands ❌
**As a** power user,  
**I want** slash commands like `/save` and `/export`,  
**So that** I have quick shortcuts for common actions.

**Status:** ❌ Not Started (Sprint 45)

**Commands:**
- `/save` - Save current design
- `/export [format]` - Export design (STL/STEP/OBJ)
- `/maketemplate` - Create template from design
- `/help` - Show available commands
- `/undo` - Undo last change

---

### User Story 18: Clarifying Questions ❌
**As a** user with vague requirements,  
**I want** the AI to ask clarifying questions,  
**So that** I get a design that matches my actual needs.

**Status:** ❌ Not Started (Sprint 46)

---

### User Story 19: Advanced Pattern Understanding ❌
**As a** maker,  
**I want** the AI to understand patterns like Gridfinity and dovetail joints,  
**So that** I can create specialized designs.

**Status:** ❌ Not Started (Sprint 45-46)

---

### User Story 20: Manufacturing Awareness ❌
**As a** user designing for production,  
**I want** the AI to understand manufacturing constraints,  
**So that** my designs work with my chosen manufacturing method.

**Status:** ❌ Not Started (Sprint 48)

**Features:**
- 3D printing optimization
- CNC milling constraints
- Material recommendations
- Print settings suggestions

---

## User Experience Enhancements

### User Story 21: Industrial Theme ❌
**As a** CAD user,  
**I want** a professional dark-mode industrial theme,  
**So that** the app looks credible and is easy on my eyes.

**Status:** ❌ Not Started (Sprint 49-50)

**Color Palette:**
- Primary Background: #0E1A26 (deep navy)
- Primary Accent: #21C4F3 (bright cyan)
- Secondary Accent: #1F6FDB (trustworthy blue)
- Surface: #123A5F (elevated UI)

---

### User Story 22: Light Mode ❌
**As a** user who prefers light interfaces,  
**I want** a light mode option,  
**So that** I can work comfortably in bright environments.

**Status:** ❌ Not Started (Sprint 49)

---

### User Story 23: Slide-out History Panel ❌
**As a** user,  
**I want** a slide-out history panel on the left,  
**So that** I can quickly access past conversations.

**Status:** ❌ Not Started (Sprint 50)

**Tasks:**
- ❌ Remove "Create" button from navbar
- ❌ Move history to left slide-out tray
- ❌ Show conversation previews

---

## Privacy & History

### User Story 24: Delete Chat History ❌
**As a** privacy-conscious user,  
**I want** to delete my chat history,  
**So that** my data isn't stored longer than I want.

**Status:** ❌ Not Started (Sprint 52)

**Tasks:**
- ❌ Delete individual conversations
- ❌ Delete all chat history
- ❌ Data retention settings

---

### User Story 25: Export Chat History ❌
**As a** user,  
**I want** to export my conversations,  
**So that** I have backups in PDF, TXT, or JSON format.

**Status:** ❌ Not Started (Sprint 51)

---

## Feedback & Quality

### User Story 26: Rate AI Responses ❌
**As a** user,  
**I want** to rate AI responses (thumbs up/down),  
**So that** I can help improve the AI over time.

**Status:** ❌ Not Started (Sprint 53)

---

### User Story 27: Provide Detailed Feedback ❌
**As a** user,  
**I want** to provide detailed feedback on responses,  
**So that** specific issues can be addressed.

**Status:** ❌ Not Started (Sprint 53)

---

### User Story 28: Save Favorite Responses ❌
**As a** user,  
**I want** to save and organize favorite responses,  
**So that** I can reference them later.

**Status:** ❌ Not Started (Sprint 54)

---

## AI Personalization

### User Story 29: AI Assistant Name ❌
**As a** user,  
**I want** the AI to have a memorable name,  
**So that** interactions feel more personal.

**Status:** ❌ Not Started (Sprint 55)

**Default Name:** "CADdy" (CAD + buddy)

---

### User Story 30: Response Style Customization ❌
**As a** user,  
**I want** to customize the AI's response style,  
**So that** it matches my preferences.

**Status:** ❌ Not Started (Sprint 55)

**Presets:** Concise, Detailed, Technical, Friendly

---

### User Story 31: Voice Input/Output ❌
**As a** hands-busy user,  
**I want** voice input and output,  
**So that** I can interact hands-free.

**Status:** ❌ Not Started (Sprint 56)

---

## Admin & Platform

### User Story 32: Admin Dashboard Improvements ❌
**As an** admin,  
**I want** comprehensive metrics and user management,  
**So that** I can effectively manage the platform.

**Status:** ❌ Not Started (Sprint 57-58)

**Features:**
- Real-time usage dashboard
- User activity analytics
- Generation success/failure rates
- User search and management
- Role/permission management

---

### User Story 33: Logging & Audit ❌
**As an** operations engineer,  
**I want** structured logging and audit trails,  
**So that** I can debug issues and meet compliance requirements.

**Status:** ❌ Not Started (Sprint 59-60)

---

## Social & Collaboration

### User Story 34: Share on Social Media ❌
**As a** proud maker,  
**I want** to share my designs on social media,  
**So that** I can show off my work.

**Status:** ❌ Not Started (Sprint 61)

---

### User Story 35: Team Collaboration ❌
**As a** team member,  
**I want** to invite others to my conversations,  
**So that** we can work together on projects.

**Status:** ❌ Not Started (Sprint 62)

---

## Internationalization

### User Story 36: Multi-Language Support ❌
**As an** international user,  
**I want** to use the app in my language,  
**So that** I can work more comfortably.

**Status:** ❌ Not Started (Sprint 63-64)

**Initial Languages:** English, Spanish, German, French, Chinese, Japanese

---

## Mobile & Cross-Platform

### User Story 37: Mobile App ❌
**As a** user on the go,  
**I want** a native mobile app,  
**So that** I can design from anywhere.

**Status:** ❌ Not Started (Sprint 65-68)

**Platforms:** iOS, Android

---

### User Story 38: Progressive Web App ❌
**As a** frequent user,  
**I want** to install the app on my device,  
**So that** I can access it like a native app.

**Status:** ❌ Not Started (Sprint 69-70)

**Features:**
- Installable
- Offline viewing
- Push notifications

---

# Summary: All Stories Status

| Category | Stories | Implemented | Partial | Not Started |
|----------|---------|-------------|---------|-------------|
| Phase 4 (Core) | US1-16 | 6 | 6 | 4 |
| AI Commands | US17-20 | 0 | 0 | 4 |
| UX & Theming | US21-23 | 0 | 0 | 3 |
| Privacy & History | US24-25 | 0 | 0 | 2 |
| Feedback | US26-28 | 0 | 0 | 3 |
| Personalization | US29-31 | 0 | 0 | 3 |
| Admin | US32-33 | 0 | 0 | 2 |
| Social | US34-35 | 0 | 0 | 2 |
| i18n | US36 | 0 | 0 | 1 |
| Mobile | US37-38 | 0 | 0 | 2 |
| **Total** | **38** | **6** | **6** | **26** |

---

## Documentation Map

| Document | Content |
|----------|---------|
| **[ROADMAP.md](ROADMAP.md)** | Overall product roadmap and timeline |
| **[docs/product-roadmap.md](docs/product-roadmap.md)** | RICE-scored feature backlog |
| **[docs/sprint-planning-phase-4.md](docs/sprint-planning-phase-4.md)** | Detailed sprint plans (36-56) |
| **[docs/user-stories-phase-4.md](docs/user-stories-phase-4.md)** | Detailed Phase 4 user stories |
| **[docs/user-stories-phase-5.md](docs/user-stories-phase-5.md)** | Detailed Phase 5+ enhancement stories |