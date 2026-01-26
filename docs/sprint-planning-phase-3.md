# Sprint Planning: Phase 3 - Quality, UX, and Production Readiness

**Date:** 2026-01-24  
**Author:** Development Team  
**Status:** ✅ PLANNING COMPLETE - Sprints Added to Backlog  

---

## Key Decisions Made

| Decision | Answer | Impact |
|----------|--------|--------|
| Testing Strategy | Backend unit tests first, then E2E | Sprint 15-16 focuses on backend |
| Mobile Strategy | Responsive design (not PWA) | Sprint 19-20 includes responsive audit |
| Accessibility Target | WCAG 2.1 AAA | Sprint 19-20 has AAA contrast ratios (7:1) |
| Collaboration Features | Included in MVP | Sprint 17-18 includes sharing + comments |
| Sprint Order | Confirmed as proposed | Testing → Integration → UX → E2E |

---

## Current State Analysis

### What We Have Built (Sprints 1-14)

#### Backend (Solid Foundation)
- ✅ CAD Engine: Primitives, operations, export (STEP/STL/3MF)
- ✅ AI Integration: Claude client, prompts, parser, generator
- ✅ Authentication: JWT, OAuth, password reset, email verification
- ✅ File Management: Upload, storage, conversion, thumbnails
- ✅ Job Queue: Celery workers, priority tiers, progress tracking
- ✅ Templates: CRUD, categories, parameters, validation
- ✅ Version History: Design versions, restore, compare, diff
- ✅ CAD Modification: Transform, boolean, features API
- ✅ Content Moderation: Detection, admin review, warnings/bans
- ✅ Backup/Recovery: Scheduled backups, restore, verification
- ✅ Trash Bin: Soft delete, retention, restore

#### Frontend (Needs Work)
- ✅ Auth Pages: Login, register, password reset, email verify
- ✅ Dashboard: Basic layout
- ✅ Templates: List, detail, parameter form
- ✅ Generate: AI generation page
- ✅ File Uploader: Drag-drop upload
- ✅ Model Viewer: Three.js 3D viewer
- ⚠️ File Manager: Created but not integrated
- ⚠️ Admin Dashboard: Created but not routed
- ⚠️ Job Status: Component created, not integrated
- ❌ User Settings: Not implemented
- ❌ Project Organization: Not implemented
- ❌ Onboarding: Not implemented
- ❌ Mobile Responsiveness: Not verified

#### Testing Coverage
| Area | Existing Tests | Coverage Gap |
|------|---------------|--------------|
| CAD Primitives | ✅ test_primitives.py | Good |
| CAD Operations | ✅ test_operations.py | Good |
| CAD Export | ✅ test_export.py | Good |
| AI Client | ✅ test_client.py | Good |
| Auth API | ✅ test_auth.py | Good |
| Health API | ✅ test_health.py | Good |
| Generate API | ✅ test_generate.py | Good |
| Files API | ❌ None | **HIGH PRIORITY** |
| Jobs API | ❌ None | **HIGH PRIORITY** |
| Templates API | ❌ None | Medium |
| Modify API | ❌ None | Medium |
| Versions API | ❌ None | Medium |
| Admin API | ❌ None | Medium |
| Trash API | ❌ None | Low |
| Moderation Service | ❌ None | Medium |
| Backup Service | ❌ None | Medium |
| **Frontend** | ❌ setup.ts only | **CRITICAL** |

---

## Gap Analysis from User Stories

| User Story | Status | Gap |
|------------|--------|-----|
| US1: Intuitive navigation | ⚠️ Partial | Need tooltips, better menu |
| US2: Sharing/collaboration | ❌ Not started | Need share API + UI |
| US3: Onboarding tutorial | ❌ Not started | Need guided tour |
| US4: Accessibility (a11y) | ❌ Not audited | Need audit + fixes |
| US5: Recent projects | ⚠️ Dashboard exists | Need project history |

---

## Proposed Sprint Plan: Sprints 15-22

### Sprint 15-16: Testing Infrastructure & Backend Coverage (Weeks 17-18)
**Goal:** Achieve 80% backend test coverage, establish frontend testing patterns

| Task | Points | Priority |
|------|--------|----------|
| Create test fixtures/factories for all models | 3 | P0 |
| Write Files API tests (upload, download, delete) | 3 | P0 |
| Write Jobs API tests (create, status, cancel, retry) | 3 | P0 |
| Write Templates API tests | 2 | P1 |
| Write Modify API tests | 2 | P1 |
| Write Versions API tests | 2 | P1 |
| Write Moderation Service tests | 2 | P1 |
| Set up frontend testing (Vitest + RTL) | 2 | P0 |
| Write frontend auth flow tests | 2 | P0 |
| **Total** | **21** | |

### Sprint 17-18: Frontend Integration & Polish (Weeks 19-20)
**Goal:** Wire up all created components, fix navigation, add missing pages

| Task | Points | Priority |
|------|--------|----------|
| Add File Manager to routes/navigation | 2 | P0 |
| Add Admin Dashboard to routes (admin-only) | 2 | P0 |
| Create User Settings page (profile, preferences) | 3 | P1 |
| Create Projects page (organize designs) | 3 | P1 |
| Integrate JobStatusCard into relevant pages | 2 | P1 |
| Add toast notifications system | 2 | P1 |
| Add loading states/skeletons throughout | 2 | P2 |
| Fix navigation menu + breadcrumbs | 2 | P1 |
| **Total** | **18** | |

### Sprint 19-20: UX Polish & Accessibility (Weeks 21-22)
**Goal:** Improve UX based on user stories, ensure accessibility compliance

| Task | Points | Priority |
|------|--------|----------|
| Onboarding flow for new users (guided tour) | 4 | P1 |
| Tooltips for all major UI elements | 2 | P1 |
| Keyboard navigation throughout app | 3 | P1 |
| Screen reader compatibility (ARIA labels) | 3 | P1 |
| Color contrast audit + fixes | 2 | P1 |
| Mobile responsive audit + fixes | 3 | P1 |
| Error handling UX (friendly messages) | 2 | P2 |
| **Total** | **19** | |

### Sprint 21-22: E2E Testing & Production Hardening (Weeks 23-24)
**Goal:** E2E test coverage, performance, production readiness

| Task | Points | Priority |
|------|--------|----------|
| Set up Playwright E2E testing | 3 | P0 |
| E2E: User registration + login flow | 2 | P0 |
| E2E: Template → Generate → Download flow | 3 | P0 |
| E2E: File upload → Modify → Export flow | 3 | P0 |
| Performance audit (Lighthouse) | 2 | P1 |
| Bundle size optimization | 2 | P1 |
| API rate limiting review | 2 | P1 |
| Production deployment documentation | 2 | P1 |
| **Total** | **19** | |

---

## Priority Matrix

### Must Have (P0) - Sprint 15-18
- [ ] Backend test coverage for Files, Jobs APIs
- [ ] Frontend testing infrastructure
- [ ] Route/navigation fixes
- [ ] Admin dashboard integration

### Should Have (P1) - Sprint 19-22
- [ ] Onboarding tutorial
- [ ] Accessibility compliance
- [ ] Mobile responsiveness
- [ ] E2E test suite

### Nice to Have (P2) - Post-MVP
- [ ] Collaboration/sharing features (US2)
- [ ] Real-time updates (WebSocket)
- [ ] Advanced analytics dashboard
- [ ] Plugin/extension system

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Backend test coverage | ~40% | 80% |
| Frontend test coverage | 0% | 60% |
| E2E test scenarios | 0 | 10+ |
| Lighthouse Performance | Unknown | >80 |
| Lighthouse Accessibility | Unknown | >90 |
| Core Web Vitals | Unknown | Pass |

---

## Technical Debt to Address

1. **Inconsistent imports** - Some files use `app.core.auth`, others `app.api.deps`
2. **Missing type exports** - Frontend types not exported from index
3. **Hardcoded API URLs** - Need consistent env var usage
4. **No error boundaries** - React error handling missing
5. **No loading states** - Many pages lack proper loading UX
6. **Missing 404 page** - No catch-all route

---

## Questions for Team Discussion

1. **Testing priority:** Unit tests vs E2E tests first? → **Backend unit tests first, then E2E**
2. **Mobile:** Progressive Web App (PWA) or mobile-responsive only? → **Responsive only for MVP**
3. **Accessibility:** WCAG 2.1 AA or AAA compliance? → **AAA (most accessible)**
4. **Collaboration:** Is sharing/commenting in scope for MVP? → **Yes, include collaboration**
5. **Analytics:** What metrics matter most for launch?

---

## Decisions Made

- ✅ Backend unit tests are priority before E2E
- ✅ Mobile-responsive design (not PWA)
- ✅ Target WCAG 2.1 AAA accessibility
- ✅ Collaboration/sharing features included in MVP
- ✅ Sprint order confirmed: Testing → Integration → UX/A11y → E2E

---

## Recommended Next Steps

1. Review this plan and prioritize
2. Start Sprint 15-16 with testing infrastructure
3. Run initial accessibility audit to size the work
4. Get user feedback on current UI before polish sprints
