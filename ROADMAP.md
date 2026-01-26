# AI Part Designer - Product Roadmap

**Version:** 2.1  
**Last Updated:** January 25, 2026  
**Status:** Active Development  

---

## Executive Summary

This roadmap outlines the remaining development work to complete the AI Part Designer platform. Based on a comprehensive gap analysis, the following phases address critical missing features required for a production-ready product.

---

## Current State Assessment

### ✅ Completed Features (Sprints 1-35)
- Core CAD engine (primitives, operations, export)
- AI generation pipeline (Claude integration)
- User authentication (JWT, email/password)
- File management (upload, storage, thumbnails)
- Job queue system (Celery workers, priority tiers)
- Template library (CRUD, categories, parameters)
- Version history and trash bin
- Content moderation system
- Backup and disaster recovery
- Reference component upload and library
- Basic spatial layout editor
- Enclosure generation (basic styles)

### 🔴 Critical Bugs & Missing Features (Sprint 36 - URGENT)
- Dashboard "Recent Designs" shows static data, not user's actual designs
- Projects page errors (`projects.filter is not a function`)
- File upload not working
- No templates available; no way for users to create templates
- Sharing page not implemented
- No way to save a design from chat (only download option)

### ❌ Remaining Gaps (Sprints 37-43)
- Reference component CAD file updates
- GPT-4 Vision PDF extraction
- File alignment and CAD combination
- Advanced enclosure styles and mounting options
- Payment/subscription integration
- OAuth social login
- Real-time WebSocket updates
- Collaboration features (UI integration)
- Onboarding flow integration

---

## Phase 4a: Critical Bug Fixes (Week 1)

### Sprint 36: Dashboard & Core Functionality Fixes
**Goal:** Fix all broken dashboard links and core functionality before new features  
**Priority:** 🔴 BLOCKER - Must complete before other work

| Epic | Features | Priority | Points |
|------|----------|----------|--------|
| Dashboard Fixes | Fix "Recent Designs" to show user's actual designs | P0 | 5 |
| Dashboard Fixes | Fix Projects page `filter` error | P0 | 3 |
| Dashboard Fixes | Fix file upload functionality | P0 | 5 |
| Template System | Create seed templates for users | P0 | 3 |
| Template System | Implement "Save as Template" from design | P0 | 5 |
| Template System | Template creation UI in dashboard | P0 | 5 |
| Chat Experience | Add "Save Design" button in chat interface | P0 | 3 |
| Chat Experience | Save design to user's library from generation | P0 | 5 |
| Sharing | Implement basic sharing page UI | P1 | 5 |
| Sharing | Connect sharing UI to existing backend APIs | P1 | 5 |

**Deliverables:**
- [ ] Dashboard shows actual user designs from API
- [ ] Projects page loads without errors
- [ ] File upload works end-to-end
- [ ] Users can browse and use templates
- [ ] Users can save designs from chat
- [ ] Basic sharing functionality works

**Definition of Done:**
- All dashboard links functional (no console errors)
- Users can complete full design workflow: create → save → find in library
- Template browsing and creation works

---

## Phase 4b: Feature Completion (Weeks 2-9)

### Sprint 37-38: Component Management & CAD Operations (Weeks 2-3)
**Goal:** Enable iterative component refinement and CAD file operations

| Epic | Features | Priority | Points |
|------|----------|----------|--------|
| Component Updates | Replace/update CAD files for components | P0 | 8 |
| Component Updates | Re-trigger AI extraction on file update | P0 | 3 |
| File Alignment | Alignment service (face, edge, center, origin) | P1 | 8 |
| File Alignment | `/api/v1/cad/align` endpoint | P1 | 5 |
| File Alignment | Frontend alignment editor with 3D preview | P1 | 8 |
| Assembly | Save aligned files as reusable assemblies | P2 | 5 |

**Deliverables:**
- [ ] PUT `/api/v1/components/{id}/files` endpoint for CAD replacement
- [ ] Alignment service with 4 alignment modes
- [ ] Interactive 3D alignment editor component
- [ ] Assembly model with transformation storage

---

### Sprint 39-40: AI Extraction & Enclosure Enhancements (Weeks 4-5)
**Goal:** Complete AI vision capabilities and expand enclosure options

| Epic | Features | Priority | Points |
|------|----------|----------|--------|
| AI Extraction | GPT-4 Vision API integration | P0 | 8 |
| AI Extraction | PDF-to-image conversion pipeline | P0 | 3 |
| AI Extraction | Dimension annotation overlay UI | P1 | 5 |
| Enclosure Styles | Rugged style template | P1 | 3 |
| Enclosure Styles | Stackable style template | P1 | 3 |
| Enclosure Styles | Industrial/Desktop/Handheld styles | P2 | 5 |
| Mounting Types | Snap-fit clips generator | P1 | 3 |
| Mounting Types | DIN rail mount generator | P1 | 3 |
| Mounting Types | Wall mount brackets | P2 | 3 |
| Mounting Types | Heat-set insert support | P2 | 3 |

**Deliverables:**
- [ ] Working GPT-4 Vision extraction from PDF mechanical drawings
- [ ] 5+ enclosure style templates
- [ ] 5+ mounting type options
- [ ] Style customization UI with live preview

---

### Sprint 40-41: Monetization & Authentication (Weeks 5-6)
**Goal:** Enable revenue generation and expand authentication options

| Epic | Features | Priority | Points |
|------|----------|----------|--------|
| Payments | Stripe SDK integration | P0 | 5 |
| Payments | Subscription tier models (Free/Pro/Enterprise) | P0 | 5 |
| Payments | Checkout and upgrade flow UI | P0 | 8 |
| Payments | Billing portal integration | P1 | 5 |
| Payments | Tier enforcement middleware | P0 | 5 |
| Payments | Usage metering and limits | P1 | 5 |
| OAuth | Google OAuth 2.0 integration | P1 | 5 |
| OAuth | GitHub OAuth integration | P1 | 5 |
| OAuth | Account linking for existing users | P2 | 3 |

**Deliverables:**
- [ ] Stripe payment processing
- [ ] Subscription management portal
- [ ] Feature gating by tier
- [ ] Google and GitHub social login
- [ ] Pricing page with tier comparison

---

### Sprint 42: Real-time & Collaboration Polish (Weeks 7-8)
**Goal:** Complete real-time features and collaboration UX

| Epic | Features | Priority | Points |
|------|----------|----------|--------|
| WebSocket | WebSocket connection manager | P1 | 5 |
| WebSocket | Real-time job status updates | P1 | 5 |
| WebSocket | Real-time notifications | P2 | 3 |
| Collaboration | Persist comments to database | P1 | 5 |
| Collaboration | Sharing UI integration in file manager | P1 | 5 |
| Collaboration | Share link generation UI | P1 | 3 |
| Onboarding | Trigger onboarding on first login | P1 | 3 |
| Onboarding | Track completion in user profile | P1 | 2 |
| Onboarding | Skip/resume capability | P2 | 2 |
| Layout Editor | Collision detection | P2 | 5 |
| Layout Editor | Clearance visualization | P2 | 3 |
| Layout Editor | Auto-arrange algorithm | P2 | 5 |

**Deliverables:**
- [ ] WebSocket-based job progress
- [ ] Persistent comment system with threading
- [ ] Sharing integration in main UI
- [ ] Complete onboarding flow
- [ ] Enhanced layout editor with collision detection

---

## Phase 5: Launch Preparation (Weeks 9-10)

### Sprint 43: Testing & Documentation
- Comprehensive E2E test suite for new features
- API documentation updates
- User documentation and help center content
- Performance optimization

### Sprint 44: Soft Launch
- Beta testing with select users
- Monitoring and observability setup
- Final security audit
- Production deployment

---

## Timeline Summary

```
Week 1-2:   Sprint 36-37 - Component Updates & File Alignment
Week 3-4:   Sprint 38-39 - AI Extraction & Enclosure Enhancements  
Week 5-6:   Sprint 40-41 - Payments & OAuth
Week 7-8:   Sprint 42    - Real-time & Collaboration
Week 9:     Sprint 43    - Testing & Documentation
Week 10:    Sprint 44    - Soft Launch
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Feature Completion | 100% of P0/P1 features | Sprint tracking |
| Test Coverage | >80% backend, >60% frontend | Coverage reports |
| API Response Time | <500ms p95 | APM monitoring |
| User Onboarding | >70% completion rate | Analytics |
| Payment Conversion | >5% free to paid | Stripe metrics |

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Stripe integration complexity | Medium | High | Start early, use test mode extensively |
| GPT-4 Vision API rate limits | Medium | Medium | Implement retry logic, caching |
| WebSocket scaling | Low | Medium | Use Redis pub/sub for horizontal scaling |
| OAuth security vulnerabilities | Low | High | Follow OWASP guidelines, security audit |

---

## Dependencies

| Dependency | Required For | Status |
|------------|--------------|--------|
| Stripe API credentials | Sprint 40-41 | ⏳ Pending |
| OpenAI GPT-4 Vision access | Sprint 38-39 | ✅ Available |
| Google OAuth credentials | Sprint 40-41 | ⏳ Pending |
| GitHub OAuth app | Sprint 40-41 | ⏳ Pending |

---

---

## Phase 6: AI Assistant Enhancements (Weeks 11-14)

### Sprint 45-46: AI Chat Commands & Intelligence (Weeks 11-12)
**Goal:** Enhance AI Assistant with slash commands and advanced understanding

| Epic | Features | Priority | Points |
|------|----------|----------|--------|
| Chat Commands | `/save` command to save current design | P0 | 3 |
| Chat Commands | `/maketemplate` command to create template | P0 | 3 |
| Chat Commands | `/export [format]` command for exports | P1 | 3 |
| Chat Commands | `/help` command with command reference | P0 | 2 |
| Chat Commands | Command autocomplete in input | P1 | 3 |
| AI Intelligence | Gridfinity pattern understanding | P1 | 5 |
| AI Intelligence | Dovetail joint generation | P1 | 5 |
| AI Intelligence | Complex constraint understanding | P1 | 8 |
| AI Intelligence | Clarifying questions for ambiguous input | P0 | 5 |
| AI Intelligence | Multi-step design workflow support | P1 | 8 |

**Deliverables:**
- [ ] Slash command parser and router
- [ ] 5+ built-in commands (`/save`, `/maketemplate`, `/export`, `/help`, `/undo`)
- [ ] Gridfinity grid pattern recognition
- [ ] Dovetail joint parametric generation
- [ ] AI clarification dialog flow

---

### Sprint 47-48: AI Performance & Manufacturing Awareness (Weeks 13-14)
**Goal:** Optimize AI response times and add manufacturing intelligence

| Epic | Features | Priority | Points |
|------|----------|----------|--------|
| Performance | Response time optimization (<3s target) | P0 | 8 |
| Performance | Model caching and precomputation | P1 | 5 |
| Performance | Streaming responses for long generations | P1 | 5 |
| Manufacturing | 3D printing optimization (support minimization) | P1 | 5 |
| Manufacturing | Material recommendation engine | P1 | 5 |
| Manufacturing | Print settings suggestions (layer height, infill) | P1 | 5 |
| Manufacturing | Manufacturer constraint awareness (3D print vs CNC) | P0 | 8 |
| Manufacturing | Printability warnings and suggestions | P1 | 5 |

**Deliverables:**
- [ ] Sub-3-second average response time
- [ ] Material recommendation API
- [ ] Manufacturer constraint validation
- [ ] Print optimization suggestions

---

## Phase 7: User Experience & Theming (Weeks 15-18)

### Sprint 49-50: Design System & Theming (Weeks 15-16)
**Goal:** Implement comprehensive theming with industrial-modern aesthetic

| Epic | Features | Priority | Points |
|------|----------|----------|--------|
| Theme System | Industrial brand color palette implementation | P0 | 5 |
| Theme System | Dark mode (primary) with CAD-adjacent aesthetic | P0 | 5 |
| Theme System | Light mode alternative | P1 | 5 |
| Theme System | Theme persistence in user preferences | P1 | 2 |
| Theme System | CSS custom properties for all colors | P0 | 3 |
| UI Polish | Remove "Create" button from navbar | P0 | 1 |
| UI Polish | Move history to left slide-out tray | P1 | 5 |
| UI Polish | Conversation history panel redesign | P1 | 5 |

**Brand Color Palette:**
```
Primary Background:    #0E1A26 (deep navy)
Primary Accent (AI):   #21C4F3 (bright cyan)
Secondary Accent:      #1F6FDB (trustworthy blue)
Surface/Cards:         #123A5F (elevated UI)
Primary Text:          #F4F7FA (high-contrast white)
Secondary Text:        #9FB2C8 (muted gray-blue)
Borders/Dividers:      #2A3A4A (subtle lines)
Success:               #2EE6C8 (confirmations)
```

**Deliverables:**
- [ ] Complete design system with CSS variables
- [ ] Dark mode (default) and light mode toggle
- [ ] Redesigned navigation with slide-out history
- [ ] Industrial-modern visual refresh

---

### Sprint 51-52: Chat History & Privacy (Weeks 17-18)
**Goal:** Enhanced chat management and user privacy controls

| Epic | Features | Priority | Points |
|------|----------|----------|--------|
| Chat History | Persistent conversation storage | P0 | 5 |
| Chat History | Conversation list in slide-out panel | P0 | 5 |
| Chat History | Search within conversations | P1 | 3 |
| Chat History | Export history (PDF, TXT, JSON) | P1 | 5 |
| Privacy | Delete individual conversations | P0 | 3 |
| Privacy | Delete all chat history option | P0 | 3 |
| Privacy | Data retention settings | P2 | 3 |
| Privacy | Privacy dashboard in settings | P1 | 3 |

**Deliverables:**
- [ ] Persistent chat history database model
- [ ] Slide-out conversation history panel
- [ ] Export to PDF/TXT/JSON
- [ ] Complete privacy controls

---

## Phase 8: User Feedback & Quality (Weeks 19-22)

### Sprint 53-54: Response Rating & Feedback (Weeks 19-20)
**Goal:** Enable users to improve AI quality through feedback

| Epic | Features | Priority | Points |
|------|----------|----------|--------|
| Rating System | Thumbs up/down on AI responses | P0 | 3 |
| Rating System | Optional feedback text on ratings | P1 | 3 |
| Rating System | Rating aggregation and analytics | P1 | 5 |
| Favorites | Save favorite responses to library | P1 | 5 |
| Favorites | Organize favorites with tags | P2 | 3 |
| Favorites | Quick reference panel for favorites | P1 | 3 |
| Feedback | Detailed feedback form for responses | P1 | 3 |
| Feedback | Feedback categorization (accuracy, style, etc.) | P2 | 3 |

**Deliverables:**
- [ ] Response rating UI (thumbs up/down)
- [ ] Feedback collection and storage
- [ ] Favorites library with organization
- [ ] Admin feedback analytics dashboard

---

### Sprint 55-56: AI Personalization (Weeks 21-22)
**Goal:** Allow users to customize AI behavior and personality

| Epic | Features | Priority | Points |
|------|----------|----------|--------|
| AI Naming | Custom AI Assistant name (default: "CADdy") | P2 | 2 |
| AI Naming | Name appears in chat and UI | P2 | 2 |
| Personality | Response style presets (Concise/Detailed/Technical) | P1 | 5 |
| Personality | Custom personality instructions | P2 | 5 |
| Voice | Voice output for responses (TTS) | P2 | 8 |
| Voice | Voice input for prompts (STT) | P2 | 8 |
| Voice | Hands-free interaction mode | P3 | 5 |

**Deliverables:**
- [ ] AI naming system with branding
- [ ] Response style customization
- [ ] Voice input/output integration (Web Speech API)

---

## Phase 9: Admin & Analytics (Weeks 23-26)

### Sprint 57-58: Admin Dashboard Improvements (Weeks 23-24)
**Goal:** Comprehensive admin tools for platform management

| Epic | Features | Priority | Points |
|------|----------|----------|--------|
| Metrics | Real-time usage dashboard | P0 | 5 |
| Metrics | User activity analytics | P0 | 5 |
| Metrics | Generation success/failure rates | P0 | 3 |
| Metrics | API performance monitoring | P1 | 5 |
| Metrics | Revenue and subscription analytics | P1 | 5 |
| User Management | User search and filtering | P0 | 3 |
| User Management | User detail view with activity history | P1 | 5 |
| User Management | Bulk user actions (disable, message) | P1 | 3 |
| User Management | Role and permission management | P1 | 5 |

**Deliverables:**
- [ ] Admin analytics dashboard with charts
- [ ] Enhanced user management interface
- [ ] Real-time metrics and alerts

---

### Sprint 59-60: Logging & Audit (Weeks 25-26)
**Goal:** Comprehensive logging for debugging and compliance

| Epic | Features | Priority | Points |
|------|----------|----------|--------|
| Logging | Structured logging throughout system | P0 | 5 |
| Logging | Log search and filtering interface | P1 | 5 |
| Logging | Log retention and archival policies | P1 | 3 |
| Audit | User action audit trail | P0 | 5 |
| Audit | Admin action audit trail | P0 | 3 |
| Audit | Audit log export for compliance | P1 | 3 |
| Monitoring | Error alerting and notifications | P1 | 5 |
| Monitoring | System health dashboard | P1 | 5 |

**Deliverables:**
- [ ] Centralized logging system
- [ ] Audit log with user/admin activity
- [ ] Admin monitoring and alerting

---

## Phase 10: Social & Collaboration (Weeks 27-30)

### Sprint 61-62: Sharing & Social Features (Weeks 27-28)
**Goal:** Enable users to share and collaborate on designs

| Epic | Features | Priority | Points |
|------|----------|----------|--------|
| Social Sharing | Share designs to social media | P2 | 5 |
| Social Sharing | Email sharing with preview | P2 | 3 |
| Social Sharing | Shareable design links (public/unlisted) | P1 | 3 |
| Social Sharing | Embed code for websites | P2 | 3 |
| Collaboration | Invite collaborators to conversation | P1 | 8 |
| Collaboration | Shared workspace for teams | P2 | 8 |
| Collaboration | Real-time collaborative editing | P3 | 13 |
| Collaboration | Team conversation history | P2 | 5 |

**Deliverables:**
- [ ] Social sharing integrations
- [ ] Team collaboration features
- [ ] Shared workspaces

---

### Sprint 63-64: Multi-Language Support (Weeks 29-30)
**Goal:** Internationalization for global audience

| Epic | Features | Priority | Points |
|------|----------|----------|--------|
| i18n | Internationalization framework setup | P1 | 5 |
| i18n | Language detection and selection | P1 | 3 |
| i18n | Initial language pack (EN, ES, DE, FR, ZH, JA) | P1 | 8 |
| i18n | AI responses in user's language | P1 | 5 |
| i18n | Translation management system | P2 | 5 |
| i18n | RTL language support | P2 | 5 |

**Deliverables:**
- [ ] i18n framework integration
- [ ] 6+ language translations
- [ ] AI multilingual responses

---

## Phase 11: Mobile & Extended Platforms (Weeks 31-36)

### Sprint 65-68: Mobile Application (Weeks 31-34)
**Goal:** Native mobile app for iOS and Android

| Epic | Features | Priority | Points |
|------|----------|----------|--------|
| Mobile App | React Native project setup | P1 | 5 |
| Mobile App | Authentication and user sync | P0 | 5 |
| Mobile App | Chat interface for mobile | P0 | 8 |
| Mobile App | 3D preview viewer (mobile-optimized) | P1 | 8 |
| Mobile App | Design management (view, organize) | P1 | 5 |
| Mobile App | Push notifications for job completion | P1 | 5 |
| Mobile App | Offline mode for viewing designs | P2 | 8 |
| Mobile App | Camera integration for reference photos | P2 | 5 |
| Mobile App | iOS App Store submission | P0 | 3 |
| Mobile App | Google Play Store submission | P0 | 3 |

**Deliverables:**
- [ ] React Native mobile application
- [ ] iOS and Android app store listings
- [ ] Mobile-optimized 3D viewer
- [ ] Push notifications

---

### Sprint 69-70: Progressive Web App (Weeks 35-36)
**Goal:** PWA for cross-platform access

| Epic | Features | Priority | Points |
|------|----------|----------|--------|
| PWA | Service worker for offline support | P1 | 5 |
| PWA | App manifest and installation | P1 | 3 |
| PWA | Background sync for uploads | P2 | 5 |
| PWA | Push notifications (web) | P2 | 5 |
| PWA | Home screen installation prompt | P1 | 2 |

**Deliverables:**
- [ ] Full PWA capabilities
- [ ] Installable web app
- [ ] Offline design viewing

---

## Timeline Summary (Extended)

```
Weeks 1-2:   Sprint 36-37 - Component Updates & File Alignment
Weeks 3-4:   Sprint 38-39 - AI Extraction & Enclosure Enhancements  
Weeks 5-6:   Sprint 40-41 - Payments & OAuth
Weeks 7-8:   Sprint 42    - Real-time & Collaboration
Weeks 9-10:  Sprint 43-44 - Testing & Soft Launch

--- PHASE 5: ENHANCEMENTS ---

Weeks 11-12: Sprint 45-46 - AI Chat Commands & Intelligence
Weeks 13-14: Sprint 47-48 - AI Performance & Manufacturing
Weeks 15-16: Sprint 49-50 - Design System & Theming
Weeks 17-18: Sprint 51-52 - Chat History & Privacy
Weeks 19-20: Sprint 53-54 - Response Rating & Feedback
Weeks 21-22: Sprint 55-56 - AI Personalization
Weeks 23-24: Sprint 57-58 - Admin Dashboard Improvements
Weeks 25-26: Sprint 59-60 - Logging & Audit
Weeks 27-28: Sprint 61-62 - Sharing & Social Features
Weeks 29-30: Sprint 63-64 - Multi-Language Support
Weeks 31-34: Sprint 65-68 - Mobile Application
Weeks 35-36: Sprint 69-70 - Progressive Web App
```

---

## Appendix: Feature Priority Matrix

### P0 - Must Have (Launch Blockers)
- Component CAD file updates
- Payment integration
- Tier enforcement
- GPT-4 Vision extraction

### P1 - Should Have (Core Experience)
- File alignment
- OAuth login
- WebSocket updates
- Enclosure styles
- Mounting types
- Collaboration UI

### P2 - Nice to Have (Polish)
- Heat-set inserts
- Auto-arrange
- Collision detection
- Advanced sharing features

### Enhancement Priorities (Post-Launch)

#### P0 - Critical Enhancements
- AI clarifying questions
- Manufacturer constraint awareness
- Dark mode theming
- Chat history delete (privacy)
- Response rating system

#### P1 - High Value Enhancements  
- Slash commands (`/save`, `/export`, etc.)
- Gridfinity/dovetail understanding
- Slide-out history panel
- Admin dashboard metrics
- Multi-language support
- Mobile application

#### P2 - Medium Value Enhancements
- AI voice input/output
- AI personality customization
- Social sharing
- Team collaboration
- Chat export (PDF/TXT)

#### P3 - Future Considerations
- Real-time collaborative editing
- Hands-free interaction mode
- AI Assistant naming/branding