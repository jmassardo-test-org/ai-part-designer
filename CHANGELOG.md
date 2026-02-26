# Changelog

All notable changes to AI Part Designer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.0] - 2026-02-26

### 🛡️ Epic 13: Model Licensing & IP Protection

Adds Creative Commons licensing, remix enforcement, and IP violation reporting to the marketplace.

### ✨ Added

#### License Management
- **License catalog**: 9 standard license types (CC0, CC BY, CC BY-SA, CC BY-NC, CC BY-NC-SA, CC BY-ND, CC BY-NC-ND, All Rights Reserved, Custom)
- **Publish with license**: Assign license type when publishing to marketplace
- **Custom licenses**: Optional free-text license with configurable remix permission
- **License filtering**: Browse marketplace by `license_type`, `allows_remix`, `allows_commercial`

#### Remix Enforcement
- Block remix for No-Derivatives and All-Rights-Reserved licenses
- Auto-inject attribution metadata on remix

#### IP Violation Reporting
- **Report endpoint**: `POST /api/v2/marketplace/designs/{id}/report-violation` (rate limited: 5/hr)
- **Admin takedown**: `POST /api/v2/admin/designs/{id}/takedown`
- **Violation listing**: `GET /api/v2/admin/license-violations` (paginated, filterable)

#### User Dashboard
- `GET /api/v2/licenses/my/published` — View published designs with license info
- `GET /api/v2/licenses/my/remixed` — View remixed designs with attribution

### 🗃️ Database Migrations

- `029_design_license_columns`: Adds `license_type`, `custom_license_text`, `custom_allows_remix` to `designs`
- `030_content_report_evidence_url`: Adds `evidence_url` to `content_reports`

### 📈 Observability

- Prometheus alert: `LicenseViolationRateHigh` (>20 reports/hr)
- Prometheus alert: `LicenseAdminTakedownRateHigh` (>10 takedowns/hr)
- All new endpoints auto-instrumented via existing HTTP metrics

### 🧪 Testing

- 142 tests (all passing)
- Unit, integration, and service-layer coverage
- Rate limiter, remix enforcement, and admin authorization tests

---

## [1.1.0] - 2026-01-30

### 🚀 CAD v2 Generation Engine

This release introduces the new CAD v2 generation engine with declarative schema-based enclosure design.

### ✨ Added

#### Enclosure Generator (v2)
- **AI Mode**: Natural language description to enclosure generation
- **Manual Mode**: Precise dimension and feature configuration
- Dimension presets (Small, Medium, Large, Pi Case, Arduino)
- Port/cutout presets (USB-C, USB-A, HDMI, Ethernet, Power Jack, SD Card, Audio)
- Side selection for each feature

#### New Lid Types
- Snap-fit lid with inner lip
- Screw-on lid (M3 screws)
- Hinged lid support

#### Ventilation Patterns
- Slot pattern (default)
- Honeycomb pattern
- Circular holes pattern
- Configurable sides and margins

#### Multi-Part Export
- Separate body and lid parts
- STEP + STL formats for each part
- Job-based download URLs

#### Async Generation
- Background compilation with Celery
- Job status polling endpoint
- WebSocket progress updates
- Queue visibility in job header

#### History Management
- Delete conversation from history
- Confirmation dialog for safety
- Auto-clear current view on delete

### 🔧 Changed

- `/generate` route now uses GeneratePageV2
- Lazy loader updated for v2 page
- v1 generate endpoint routes through v2 pipeline

### 📝 Documentation

- New API reference: `docs/architecture/api-v2-cad.md`
- User guide updated with Enclosure Generator section
- Release notes: `docs/releases/v1.0-cad-v2-release.md`

### 🧪 Testing

- 335 CAD v2 backend tests
- 9 worker task tests
- 9 integration tests
- 45 frontend v2 tests
- 18 E2E generation flow tests
- 15 E2E project management tests

---

## [1.0.0] - 2026-01-26

### 🎉 Initial Production Release

This is the first production release of AI Part Designer, featuring AI-powered CAD generation, subscription management, social login, and real-time collaboration.

---

### ✨ Added

#### AI-Powered Design Generation
- Natural language prompts to generate 3D CAD models
- GPT-4 Vision integration for dimension extraction from datasheets
- Intelligent parameter inference from context
- Iterative refinement with conversation history

#### Subscription & Payment
- Stripe integration for subscription management
- Three-tier pricing: Free, Pro, Enterprise
- Usage tracking and billing dashboard
- Secure checkout via Stripe Checkout
- Invoice history and PDF receipts

#### Social Authentication
- Sign in with Google (OAuth 2.0)
- Sign in with GitHub (OAuth 2.0)
- Link multiple OAuth providers to account
- Secure token handling with refresh rotation

#### Real-time Features
- WebSocket connection for live updates
- Real-time job progress notifications
- Instant notification delivery
- Presence indicators for collaboration

#### Slash Commands
- `/help` - View available commands
- `/clear` - Clear conversation
- `/export` - Export current design
- `/template` - Load a template
- `/dimension` - Set dimensions
- Autocomplete with arrow key navigation

#### File Alignment
- Visual 3D alignment editor
- Alignment presets (stack, center, side-by-side)
- Manual positioning with numeric inputs
- Save as assembly for reuse
- Export combined STEP files

#### Industrial Theme
- Professional dark mode (default)
- Light mode option
- System preference detection
- Theme persistence across sessions
- Industrial color palette (navy, cyan, blue)

#### UX Enhancements
- Slide-out history panel (Ctrl+H)
- Keyboard shortcuts for power users
- Conversation cards with thumbnails
- Clean navbar without redundant buttons
- Notification center with unread counts

#### Templates
- Pre-built design templates
- Template browser with search
- Save designs as templates
- Template customization with parameters
- Category organization

#### Core Features
- User dashboard with recent designs
- Project organization
- Design version history
- Multi-format export (STEP, STL, OBJ, GLTF)
- File upload for components and datasheets

---

### 🔧 Technical

#### Backend
- FastAPI with async support
- PostgreSQL with SQLAlchemy ORM
- Redis for caching and WebSocket pub/sub
- Celery for background job processing
- MinIO/S3 for file storage
- OpenAI GPT-4 and GPT-4 Vision integration

#### Frontend
- React 18 with TypeScript
- Vite build system
- Tailwind CSS with dark mode
- Three.js for 3D visualization
- React Query for server state
- WebSocket context for real-time updates

#### Testing
- 1658+ unit tests
- E2E tests with Playwright
- Performance testing with k6
- Security audit (OWASP Top 10)
- Accessibility audit (WCAG 2.1 AA)

#### DevOps
- Docker Compose for development
- CI/CD pipeline with GitHub Actions
- Monitoring with Sentry
- Structured logging with JSON

---

### 📊 Metrics

| Metric | Value |
|--------|-------|
| Frontend Tests | 1658 |
| Backend Tests | 450+ |
| E2E Tests | 100+ |
| API Endpoints | 50+ |
| Components | 100+ |
| Code Coverage | 85%+ |

---

### 🙏 Acknowledgments

Special thanks to all contributors who made this release possible!

---

## [0.9.0] - 2026-01-12

### Added
- Sprint 55: AI Enhancement & Slash Commands
- Slash command system with autocomplete
- Template creation and customization
- CAD alignment API integration

### Changed
- Improved chat interface responsiveness
- Enhanced 3D viewer performance

---

## [0.8.0] - 2025-12-29

### Added
- Sprint 54: CAD Alignment & Vision UI
- File alignment editor with presets
- GPT-4 Vision dimension extraction
- Assembly creation and management

---

## [0.7.0] - 2025-12-15

### Added
- Sprint 53: Real-time & WebSocket
- WebSocket connection manager
- Real-time job progress updates
- Notification center in navbar
- Notification preferences

---

## [0.6.0] - 2025-12-01

### Added
- Sprint 52: OAuth & Onboarding
- Google and GitHub OAuth login
- Interactive product tour
- Onboarding progress tracking
- Connected accounts management

---

## [0.5.0] - 2025-11-17

### Added
- Sprint 51: Payment & Subscription
- Pricing page with tier comparison
- Stripe checkout integration
- Usage and billing page
- Subscription management

---

## [0.4.0] - 2025-11-03

### Added
- Sprint 50: Critical Bug Fixes
- Fixed dashboard real designs display
- Fixed projects filter error
- Fixed file upload functionality
- Template seeding system

---

## Pre-release History

Versions prior to 0.4.0 were internal development releases.

---

## Upgrade Guide

### From 0.x to 1.0.0

1. **Database Migration**
   ```bash
   alembic upgrade head
   ```

2. **Environment Variables**
   New required variables:
   - `STRIPE_SECRET_KEY`
   - `STRIPE_WEBHOOK_SECRET`
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `GITHUB_CLIENT_ID`
   - `GITHUB_CLIENT_SECRET`

3. **Redis Update**
   Redis is now required for WebSocket pub/sub. Ensure Redis is running.

4. **Frontend Build**
   ```bash
   cd frontend && npm install && npm run build
   ```

---

[1.2.0]: https://github.com/jmassardo-test-org/ai-part-designer/releases/tag/v1.2.0
[1.0.0]: https://github.com/jmassardo-test-org/ai-part-designer/releases/tag/v1.0.0
[0.9.0]: https://github.com/jmassardo-test-org/ai-part-designer/releases/tag/v0.9.0
[0.8.0]: https://github.com/jmassardo-test-org/ai-part-designer/releases/tag/v0.8.0
[0.7.0]: https://github.com/jmassardo-test-org/ai-part-designer/releases/tag/v0.7.0
[0.6.0]: https://github.com/jmassardo-test-org/ai-part-designer/releases/tag/v0.6.0
[0.5.0]: https://github.com/jmassardo-test-org/ai-part-designer/releases/tag/v0.5.0
[0.4.0]: https://github.com/jmassardo-test-org/ai-part-designer/releases/tag/v0.4.0
