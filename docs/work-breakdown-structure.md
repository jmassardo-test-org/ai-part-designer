# Work Breakdown Structure (WBS)
# AI Part Designer

**Version:** 1.0  
**Date:** 2026-01-24  
**Status:** Ready for Development  

---

## Document Overview

This document breaks down the AI Part Designer project into atomic, implementable units of work. Each task is sized for 1-3 days of development effort and includes clear acceptance criteria.

### Naming Convention
`P{phase}.{epic}.{feature}.{task}` - Example: `P1.1.1.1`

### Story Point Reference
| Points | Effort | Description |
|--------|--------|-------------|
| 1 | 2-4 hours | Trivial, well-understood |
| 2 | 4-8 hours | Small, straightforward |
| 3 | 1-2 days | Medium complexity |
| 5 | 2-3 days | Complex, some unknowns |
| 8 | 3-5 days | Large, should be split |

---

## Phase 0: Foundation (Weeks 1-3)

### Epic 0.1: Technology Validation

#### Feature 0.1.1: CAD Library Proof of Concept

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P0.1.1.1 | Set up CadQuery development environment | 1 | Install CadQuery, OCC, dependencies in Docker container |
| P0.1.1.2 | Create basic primitive generation | 2 | Box, cylinder, sphere with parameterized dimensions |
| P0.1.1.3 | Implement boolean operations | 2 | Union, difference, intersection between primitives |
| P0.1.1.4 | Add fillet and chamfer operations | 2 | Edge modifications with configurable radius |
| P0.1.1.5 | Implement STEP/STL export | 2 | Export to multiple formats with quality settings |
| P0.1.1.6 | Create project box template | 3 | Parameterized enclosure with wall thickness, screw posts |
| P0.1.1.7 | Performance benchmarking | 2 | Measure generation times for various complexities |
| P0.1.1.8 | Document CAD API patterns | 1 | Document working patterns and limitations |

**Feature Total:** 15 points (~2 weeks)

---

#### Feature 0.1.2: AI-to-CAD Pipeline POC

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P0.1.2.1 | Set up OpenAI integration | 1 | Configure API keys, rate limiting, error handling |
| P0.1.2.2 | Create prompt engineering framework | 3 | Design prompts for dimension extraction |
| P0.1.2.3 | Build NL→JSON parser | 3 | Convert natural language to structured CAD parameters |
| P0.1.2.4 | Implement CAD operation mapper | 3 | Map parsed operations to CadQuery functions |
| P0.1.2.5 | Create end-to-end generation test | 2 | "Create a box 100x50x30mm" → STEP file |
| P0.1.2.6 | Handle ambiguous inputs | 2 | Ask clarifying questions or use defaults |
| P0.1.2.7 | Document AI integration patterns | 1 | Token usage, latency, reliability metrics |

**Feature Total:** 15 points (~2 weeks)

---

### Epic 0.2: Infrastructure Setup

#### Feature 0.2.1: Repository & Development Environment

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P0.2.1.1 | Create monorepo structure | 1 | frontend/, backend/, infrastructure/, docs/ |
| P0.2.1.2 | Set up backend project skeleton | 2 | FastAPI app structure, pyproject.toml, dependencies |
| P0.2.1.3 | Set up frontend project skeleton | 2 | Vite + React + TypeScript scaffold |
| P0.2.1.4 | Create Docker Compose for local dev | 2 | API, worker, PostgreSQL, Redis, MinIO |
| P0.2.1.5 | Configure pre-commit hooks | 1 | Linting (ruff, eslint), formatting (black, prettier) |
| P0.2.1.6 | Create Makefile with dev commands | 1 | make dev, make test, make lint, make migrate |
| P0.2.1.7 | Set up environment configuration | 1 | .env templates, settings validation |

**Feature Total:** 10 points (~1 week)

---

#### Feature 0.2.2: CI/CD Pipeline

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P0.2.2.1 | Create GitHub Actions test workflow | 2 | Run pytest, jest on push/PR |
| P0.2.2.2 | Create lint workflow | 1 | Run linters, type checking |
| P0.2.2.3 | Create build workflow | 2 | Build Docker images, tag with SHA |
| P0.2.2.4 | Create staging deployment workflow | 3 | Deploy to staging on merge to main |
| P0.2.2.5 | Create production deployment workflow | 3 | Deploy to production on release tag |
| P0.2.2.6 | Set up Dependabot | 1 | Automated dependency updates |
| P0.2.2.7 | Configure branch protection rules | 1 | Require reviews, passing checks |

**Feature Total:** 13 points (~1.5 weeks)

---

#### Feature 0.2.3: Infrastructure as Code

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P0.2.3.1 | Create Terraform module structure | 2 | Modules for VPC, EKS, RDS, ElastiCache, S3 |
| P0.2.3.2 | Implement VPC/networking module | 3 | Multi-AZ VPC with public/private subnets |
| P0.2.3.3 | Implement database module | 2 | RDS PostgreSQL with backups, encryption |
| P0.2.3.4 | Implement cache module | 2 | ElastiCache Redis cluster |
| P0.2.3.5 | Implement storage module | 2 | S3 buckets with lifecycle policies |
| P0.2.3.6 | Implement Kubernetes module | 3 | EKS cluster with node groups |
| P0.2.3.7 | Create Helm charts for application | 3 | API, worker, ingress deployments |
| P0.2.3.8 | Set up Terraform Cloud/remote state | 1 | Remote state with locking |

**Feature Total:** 18 points (~2 weeks)

---

## Phase 1: Core MVP (Weeks 4-12)

### Epic 1.1: User Authentication

#### Feature 1.1.1: User Registration (US-101)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.1.1.1 | Create User model and migration | 2 | SQLAlchemy model with all fields, Alembic migration |
| P1.1.1.2 | Implement password hashing service | 1 | bcrypt hashing with cost factor 12 ✓ (exists) |
| P1.1.1.3 | Create registration endpoint | 2 | POST /api/v1/auth/register |
| P1.1.1.4 | Implement email validation | 1 | Validate format, check uniqueness |
| P1.1.1.5 | Implement password strength validation | 1 | Min 8 chars, complexity requirements ✓ (exists) |
| P1.1.1.6 | Create email verification service | 2 | Generate token, send email via SendGrid |
| P1.1.1.7 | Implement verification endpoint | 2 | GET /api/v1/auth/verify/{token} |
| P1.1.1.8 | Create registration form component | 3 | React form with validation, error display |
| P1.1.1.9 | Create verification pending page | 1 | UI for "check your email" state |
| P1.1.1.10 | Add resend verification endpoint | 1 | POST /api/v1/auth/resend-verification |
| P1.1.1.11 | Write registration API tests | 2 | Unit + integration tests |
| P1.1.1.12 | Write registration E2E tests | 2 | Playwright tests for happy path + errors |

**Feature Total:** 20 points

**Acceptance Criteria:**
- [ ] User can register with email/password/display name
- [ ] Password must meet complexity requirements
- [ ] Verification email sent within 60 seconds
- [ ] Duplicate email shows appropriate error
- [ ] Account status is "pending" until verified

---

#### Feature 1.1.2: User Login (US-102)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.1.2.1 | Create JWT token service | 2 | Access/refresh token generation ✓ (exists) |
| P1.1.2.2 | Implement login endpoint | 2 | POST /api/v1/auth/login |
| P1.1.2.3 | Add account status validation | 1 | Check pending/suspended/active states |
| P1.1.2.4 | Implement refresh token endpoint | 2 | POST /api/v1/auth/refresh |
| P1.1.2.5 | Create token blacklist for logout | 2 | Redis-based token invalidation ✓ (exists) |
| P1.1.2.6 | Implement logout endpoint | 1 | POST /api/v1/auth/logout |
| P1.1.2.7 | Create login form component | 2 | React form with remember me |
| P1.1.2.8 | Implement auth context in frontend | 2 | React context for auth state |
| P1.1.2.9 | Add protected route component | 2 | HOC for authenticated routes |
| P1.1.2.10 | Implement auth interceptor | 2 | Axios interceptor for token refresh |
| P1.1.2.11 | Write login API tests | 2 | Test all login scenarios |
| P1.1.2.12 | Write login E2E tests | 2 | Playwright tests |

**Feature Total:** 22 points

**Acceptance Criteria:**
- [ ] User can log in with correct credentials
- [ ] Invalid credentials show generic error (prevent enumeration)
- [ ] Unverified accounts cannot log in
- [ ] Suspended accounts show suspension message
- [ ] "Remember me" extends session to 30 days
- [ ] Tokens refresh automatically

---

#### Feature 1.1.3: Password Reset (US-103)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.1.3.1 | Create password reset token model | 1 | Time-limited token storage |
| P1.1.3.2 | Implement reset request endpoint | 2 | POST /api/v1/auth/forgot-password |
| P1.1.3.3 | Create reset email template | 1 | HTML email with reset link |
| P1.1.3.4 | Implement reset execution endpoint | 2 | POST /api/v1/auth/reset-password |
| P1.1.3.5 | Add token expiration validation | 1 | 1-hour expiration check |
| P1.1.3.6 | Create forgot password form | 2 | React form with success message |
| P1.1.3.7 | Create reset password form | 2 | React form with token validation |
| P1.1.3.8 | Write password reset tests | 2 | API + E2E tests |

**Feature Total:** 13 points

**Acceptance Criteria:**
- [ ] Reset request always shows success (prevent enumeration)
- [ ] Reset email sent only if email exists
- [ ] Reset link expires after 1 hour
- [ ] Password updated and user logged in after reset
- [ ] All other sessions invalidated after reset

---

#### Feature 1.1.4: Profile Management (US-104)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.1.4.1 | Create get profile endpoint | 1 | GET /api/v1/users/me |
| P1.1.4.2 | Create update profile endpoint | 2 | PATCH /api/v1/users/me |
| P1.1.4.3 | Implement email change flow | 3 | Verification required for email change |
| P1.1.4.4 | Implement password change endpoint | 2 | Requires current password |
| P1.1.4.5 | Create notification preferences model | 1 | Email preferences storage |
| P1.1.4.6 | Create profile settings page | 3 | React page with all settings sections |
| P1.1.4.7 | Write profile management tests | 2 | API + E2E tests |

**Feature Total:** 14 points

---

#### Feature 1.1.5: Account Deletion (US-105)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.1.5.1 | Create account deletion endpoint | 2 | POST /api/v1/users/me/delete |
| P1.1.5.2 | Implement 30-day grace period | 2 | Scheduled deletion, cancellation option |
| P1.1.5.3 | Create data export before deletion | 3 | Generate ZIP of user's data |
| P1.1.5.4 | Create deletion confirmation UI | 2 | Type "DELETE" confirmation |
| P1.1.5.5 | Create scheduled deletion job | 2 | Celery task for permanent deletion |
| P1.1.5.6 | Write account deletion tests | 2 | API + E2E tests |

**Feature Total:** 13 points

---

### Epic 1.2: Template Library

#### Feature 1.2.1: Template Catalog (US-202)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.2.1.1 | Create Template model and migration | 2 | name, category, parameters, tier, etc. |
| P1.2.1.2 | Create TemplateCategory model | 1 | Categories with ordering |
| P1.2.1.3 | Seed initial template data | 2 | 10 core templates with parameters |
| P1.2.1.4 | Implement list templates endpoint | 2 | GET /api/v1/templates with filtering |
| P1.2.1.5 | Implement get template endpoint | 1 | GET /api/v1/templates/{id} |
| P1.2.1.6 | Create template list component | 3 | Grid view with category filtering |
| P1.2.1.7 | Create template card component | 2 | Thumbnail, name, tier badge |
| P1.2.1.8 | Add tier-based filtering | 1 | Show available/locked templates |
| P1.2.1.9 | Write template API tests | 2 | API tests for listing/filtering |

**Feature Total:** 16 points

**Acceptance Criteria:**
- [ ] Templates organized by category
- [ ] Thumbnail preview on hover
- [ ] Pro templates shown with upgrade prompt for free users
- [ ] Search/filter by category and name

---

#### Feature 1.2.2: Template Customization (US-203)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.2.2.1 | Create parameter schema system | 3 | JSON schema for template parameters |
| P1.2.2.2 | Implement parameter validation | 2 | Min/max, dependencies, constraints |
| P1.2.2.3 | Create parameter form component | 3 | Dynamic form from schema |
| P1.2.2.4 | Implement real-time preview API | 3 | Quick generation for preview |
| P1.2.2.5 | Create 3D preview component | 5 | Three.js viewer with STL loading |
| P1.2.2.6 | Add slider controls for dimensions | 2 | Linked sliders and input fields |
| P1.2.2.7 | Implement reset to defaults | 1 | Button to restore default values |
| P1.2.2.8 | Add parameter presets | 2 | Save/load parameter combinations |
| P1.2.2.9 | Write customization tests | 2 | API + component tests |

**Feature Total:** 23 points

**Acceptance Criteria:**
- [ ] 3D preview updates within 2 seconds of parameter change
- [ ] Invalid parameters show validation errors
- [ ] Dependent parameters update automatically
- [ ] Can reset all parameters to defaults

---

#### Feature 1.2.3: Core Template Implementation

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.2.3.1 | Implement Project Box template | 3 | Length, width, height, wall thickness, corner radius |
| P1.2.3.2 | Implement Project Box with Lid template | 3 | Adds lid with tolerance, lip height |
| P1.2.3.3 | Implement L-Bracket template | 2 | Arm lengths, thickness, mounting holes |
| P1.2.3.4 | Implement Corner Bracket template | 2 | Size, thickness, gusset options |
| P1.2.3.5 | Implement Cylindrical Container template | 2 | Diameter, height, wall, thread options |
| P1.2.3.6 | Implement Cable Clip template | 2 | Cable diameter, mounting options |
| P1.2.3.7 | Implement Phone Stand template | 3 | Phone dimensions, viewing angle |
| P1.2.3.8 | Implement Pegboard Hook template | 2 | Hook size, peg spacing |
| P1.2.3.9 | Implement Drawer Divider template | 2 | Grid size, height, slot width |
| P1.2.3.10 | Implement Standoff/Spacer template | 2 | Inner/outer diameter, height, shape |

**Feature Total:** 23 points

---

### Epic 1.3: Natural Language Generation

#### Feature 1.3.1: Description Parser (US-201)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.3.1.1 | Design AI prompt templates | 3 | System prompts for dimension extraction |
| P1.3.1.2 | Implement dimension extraction | 3 | Parse measurements from text |
| P1.3.1.3 | Implement shape recognition | 3 | Identify primitive shapes and modifiers |
| P1.3.1.4 | Implement feature extraction | 3 | Holes, fillets, chamfers, patterns |
| P1.3.1.5 | Create structured output parser | 2 | JSON schema validation |
| P1.3.1.6 | Handle unit conversions | 2 | mm, cm, inches normalization |
| P1.3.1.7 | Implement clarification flow | 3 | Detect ambiguity, generate questions |
| P1.3.1.8 | Write parser tests | 2 | Test various input patterns |

**Feature Total:** 21 points

**Acceptance Criteria:**
- [ ] Correctly extracts dimensions (±5% tolerance)
- [ ] Identifies shapes: box, cylinder, sphere, cone
- [ ] Recognizes features: holes, fillets, chamfers
- [ ] Handles multiple units consistently
- [ ] Asks clarifying questions for ambiguous input

---

#### Feature 1.3.2: CAD Generation Engine

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.3.2.1 | Create CAD operations registry | 2 | Map operation types to CadQuery functions |
| P1.3.2.2 | Implement primitive generation | 3 | Box, cylinder, sphere from parsed params |
| P1.3.2.3 | Implement feature application | 3 | Apply holes, fillets, arrays |
| P1.3.2.4 | Implement boolean operations | 2 | Combine/subtract shapes |
| P1.3.2.5 | Add mesh generation | 2 | STL tessellation with quality levels |
| P1.3.2.6 | Implement error recovery | 3 | Handle geometry failures gracefully |
| P1.3.2.7 | Add generation caching | 2 | Cache identical requests |
| P1.3.2.8 | Write CAD engine tests | 3 | Test common generation patterns |

**Feature Total:** 20 points

---

#### Feature 1.3.3: Design Modification (US-205)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.3.3.1 | Implement scaling commands | 2 | "Make it 20% larger" parsing and execution |
| P1.3.3.2 | Implement feature addition | 3 | "Add a hole for M5 bolt" |
| P1.3.3.3 | Implement feature removal | 3 | "Remove the tabs" |
| P1.3.3.4 | Implement dimension changes | 2 | "Change width to 150mm" |
| P1.3.3.5 | Create modification history | 2 | Track changes for undo |
| P1.3.3.6 | Implement undo/redo | 2 | Revert modifications |
| P1.3.3.7 | Create modification input UI | 2 | Chat-like interface for modifications |
| P1.3.3.8 | Write modification tests | 2 | Test common modification patterns |

**Feature Total:** 18 points

---

#### Feature 1.3.4: Content Moderation (US-802)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.3.4.1 | Create prohibited content keywords list | 1 | Weapons, illegal items, etc. |
| P1.3.4.2 | Implement keyword filtering | 2 | Fast regex-based pre-filter |
| P1.3.4.3 | Integrate OpenAI moderation API | 2 | Check content before generation |
| P1.3.4.4 | Implement intent classification | 3 | ML-based intent detection |
| P1.3.4.5 | Create ModerationLog model | 1 | Log all moderation decisions |
| P1.3.4.6 | Create admin moderation queue UI | 3 | Review flagged content |
| P1.3.4.7 | Implement user warning system | 2 | Track violations, issue warnings |
| P1.3.4.8 | Write moderation tests | 2 | Test detection accuracy |

**Feature Total:** 16 points

---

### Epic 1.4: File Management

#### Feature 1.4.1: File Upload (US-301)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.4.1.1 | Create Design model and migration | 2 | Design with file reference, metadata |
| P1.4.1.2 | Create DesignFile model | 1 | File versions, types, paths |
| P1.4.1.3 | Implement file upload endpoint | 3 | POST /api/v1/designs/upload |
| P1.4.1.4 | Add file type validation | 1 | STEP, STL, OBJ, 3MF only |
| P1.4.1.5 | Add file size validation | 1 | Max 100MB check |
| P1.4.1.6 | Implement STEP parser | 3 | Extract geometry from STEP files |
| P1.4.1.7 | Implement STL parser | 2 | Parse binary/ASCII STL |
| P1.4.1.8 | Create upload progress component | 2 | Drag-drop with progress bar |
| P1.4.1.9 | Implement chunked upload | 3 | Large file upload handling |
| P1.4.1.10 | Write file upload tests | 2 | Test various file types/sizes |

**Feature Total:** 20 points

**Acceptance Criteria:**
- [ ] Drag-drop and browse file selection
- [ ] Progress indicator during upload
- [ ] Reject unsupported file types
- [ ] Reject files over 100MB
- [ ] Parse and validate file geometry

---

#### Feature 1.4.2: 3D Preview (US-302)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.4.2.1 | Set up Three.js viewer component | 3 | Basic scene, camera, lighting |
| P1.4.2.2 | Implement STL mesh loading | 2 | Load and display STL files |
| P1.4.2.3 | Implement orbit controls | 2 | Rotate, pan, zoom interactions |
| P1.4.2.4 | Add standard view buttons | 1 | Front, back, top, isometric |
| P1.4.2.5 | Implement render modes | 2 | Solid, wireframe, transparent |
| P1.4.2.6 | Add measurement tool | 3 | Click two points, show distance |
| P1.4.2.7 | Implement thumbnail generation | 2 | Server-side preview images |
| P1.4.2.8 | Add WebGL fallback | 2 | Handle unsupported browsers |
| P1.4.2.9 | Write viewer component tests | 2 | Test interactions and rendering |

**Feature Total:** 19 points

---

#### Feature 1.4.3: Export (US-303)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.4.3.1 | Implement STL export | 2 | Binary/ASCII with quality options |
| P1.4.3.2 | Implement STEP export | 2 | AP203/AP214 standards |
| P1.4.3.3 | Implement OBJ export | 2 | With material export option |
| P1.4.3.4 | Implement 3MF export | 2 | With print settings |
| P1.4.3.5 | Add unit conversion | 1 | Export in mm or inches |
| P1.4.3.6 | Create export dialog component | 2 | Format selection, options |
| P1.4.3.7 | Implement batch export | 2 | Export multiple as ZIP |
| P1.4.3.8 | Create export download endpoint | 2 | GET /api/v1/designs/{id}/export |
| P1.4.3.9 | Write export tests | 2 | Test each format |

**Feature Total:** 17 points

---

#### Feature 1.4.4: Version History (US-304)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.4.4.1 | Create DesignVersion model | 2 | Version number, timestamp, changes |
| P1.4.4.2 | Implement auto-versioning on save | 2 | Create version on each modification |
| P1.4.4.3 | Create version list endpoint | 1 | GET /api/v1/designs/{id}/versions |
| P1.4.4.4 | Create version restore endpoint | 2 | POST /api/v1/designs/{id}/versions/{v}/restore |
| P1.4.4.5 | Create version history UI | 3 | Timeline view with thumbnails |
| P1.4.4.6 | Implement version comparison | 3 | Side-by-side 3D comparison |
| P1.4.4.7 | Write version history tests | 2 | API + E2E tests |

**Feature Total:** 15 points

---

#### Feature 1.4.5: Trash Bin (US-305)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.4.5.1 | Add soft delete to Design model | 1 | deleted_at timestamp |
| P1.4.5.2 | Implement soft delete endpoint | 1 | DELETE /api/v1/designs/{id} |
| P1.4.5.3 | Create trash list endpoint | 1 | GET /api/v1/designs/trash |
| P1.4.5.4 | Implement restore endpoint | 1 | POST /api/v1/designs/{id}/restore |
| P1.4.5.5 | Implement permanent delete endpoint | 2 | DELETE /api/v1/designs/{id}/permanent |
| P1.4.5.6 | Create trash cleanup job | 2 | Celery task for 14/30 day cleanup |
| P1.4.5.7 | Create trash UI component | 2 | List with restore/delete actions |
| P1.4.5.8 | Write trash tests | 1 | API + E2E tests |

**Feature Total:** 11 points

---

### Epic 1.5: Job Queue

#### Feature 1.5.1: Job Submission (US-401)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.5.1.1 | Create Job model and migration | 2 | Status, type, priority, user, params |
| P1.5.1.2 | Configure Celery with Redis | 2 | Worker setup, task routing |
| P1.5.1.3 | Create job submission endpoint | 2 | POST /api/v1/jobs |
| P1.5.1.4 | Implement queue position calculation | 2 | Based on priority and time |
| P1.5.1.5 | Create CAD generation task | 3 | Celery task for generation |
| P1.5.1.6 | Implement quota checking | 2 | Check user's remaining quota |
| P1.5.1.7 | Add concurrent job limit | 1 | Max 3 free / 10 pro |
| P1.5.1.8 | Write job submission tests | 2 | API + worker tests |

**Feature Total:** 16 points

**Acceptance Criteria:**
- [ ] Job created with unique ID
- [ ] Queue position returned
- [ ] Quota enforced per user tier
- [ ] Concurrent job limit enforced

---

#### Feature 1.5.2: Job Status Tracking (US-402)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.5.2.1 | Create job status endpoint | 1 | GET /api/v1/jobs/{id} |
| P1.5.2.2 | Create job list endpoint | 1 | GET /api/v1/jobs with filtering |
| P1.5.2.3 | Implement progress updates | 2 | Update progress during processing |
| P1.5.2.4 | Set up WebSocket for real-time updates | 3 | Socket.io for job status |
| P1.5.2.5 | Create job status component | 2 | Progress bar, status badge |
| P1.5.2.6 | Create active jobs list component | 2 | Dashboard widget |
| P1.5.2.7 | Implement email notification | 2 | Send email on completion |
| P1.5.2.8 | Write job tracking tests | 2 | API + WebSocket tests |

**Feature Total:** 15 points

---

#### Feature 1.5.3: Priority Queue (US-403)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.5.3.1 | Configure priority queues in Celery | 2 | Separate queues for tiers |
| P1.5.3.2 | Implement tier-based routing | 2 | Route jobs to appropriate queue |
| P1.5.3.3 | Create priority worker config | 1 | Worker pool allocation |
| P1.5.3.4 | Add priority badge to UI | 1 | Show "Priority" for pro jobs |
| P1.5.3.5 | Show time savings estimate | 2 | Display benefit to free users |
| P1.5.3.6 | Write priority queue tests | 2 | Test ordering and routing |

**Feature Total:** 10 points

---

#### Feature 1.5.4: Job Cancellation (US-404)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.5.4.1 | Implement cancel endpoint | 2 | POST /api/v1/jobs/{id}/cancel |
| P1.5.4.2 | Handle queued job cancellation | 1 | Remove from queue |
| P1.5.4.3 | Handle in-progress cancellation | 2 | Celery task revocation |
| P1.5.4.4 | Add cancel button to UI | 1 | Disabled when processing |
| P1.5.4.5 | Refund quota on cancellation | 1 | Return quota for cancelled jobs |
| P1.5.4.6 | Write cancellation tests | 1 | API tests |

**Feature Total:** 8 points

---

### Epic 1.6: Dashboard

#### Feature 1.6.1: User Dashboard (US-501)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.6.1.1 | Create dashboard layout | 2 | Responsive grid layout |
| P1.6.1.2 | Create quick actions component | 1 | New design, upload, templates buttons |
| P1.6.1.3 | Create recent designs component | 2 | Last 10 designs with thumbnails |
| P1.6.1.4 | Create active jobs widget | 2 | Real-time job status |
| P1.6.1.5 | Create usage statistics component | 2 | Generations remaining, storage used |
| P1.6.1.6 | Create empty state component | 1 | Welcome message for new users |
| P1.6.1.7 | Write dashboard tests | 2 | Component + E2E tests |

**Feature Total:** 12 points

---

#### Feature 1.6.2: Project Organization (US-502)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.6.2.1 | Create Project model and migration | 2 | Name, description, user, designs |
| P1.6.2.2 | Create project CRUD endpoints | 2 | CRUD for /api/v1/projects |
| P1.6.2.3 | Implement design-project association | 1 | Move designs between projects |
| P1.6.2.4 | Create project list component | 2 | Grid/list view with design counts |
| P1.6.2.5 | Create project detail page | 2 | Designs in project, actions |
| P1.6.2.6 | Implement drag-drop organization | 3 | Drag designs between projects |
| P1.6.2.7 | Write project tests | 2 | API + E2E tests |

**Feature Total:** 14 points

---

#### Feature 1.6.3: Design Search (US-503)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P1.6.3.1 | Implement full-text search | 3 | PostgreSQL full-text on name/description |
| P1.6.3.2 | Create search endpoint | 1 | GET /api/v1/designs/search |
| P1.6.3.3 | Add filters (date, project, source) | 2 | Filter parameters |
| P1.6.3.4 | Create search UI component | 2 | Search input with suggestions |
| P1.6.3.5 | Create search results component | 2 | Grid view with highlighting |
| P1.6.3.6 | Write search tests | 1 | API + component tests |

**Feature Total:** 11 points

---

## Phase 2: Monetization (Weeks 13-17)

### Epic 2.1: Subscription System

#### Feature 2.1.1: Stripe Integration (US-602)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P2.1.1.1 | Set up Stripe account and products | 1 | Create products/prices in Stripe |
| P2.1.1.2 | Create Subscription model | 2 | stripe_id, tier, status, dates |
| P2.1.1.3 | Implement checkout session endpoint | 3 | POST /api/v1/subscriptions/checkout |
| P2.1.1.4 | Implement Stripe webhook handler | 3 | Handle subscription events |
| P2.1.1.5 | Create subscription update endpoint | 2 | Upgrade/downgrade handling |
| P2.1.1.6 | Implement cancellation endpoint | 2 | End of billing period cancellation |
| P2.1.1.7 | Create billing portal redirect | 1 | Stripe customer portal |
| P2.1.1.8 | Write Stripe integration tests | 2 | Mock Stripe API tests |

**Feature Total:** 16 points

---

#### Feature 2.1.2: Subscription UI

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P2.1.2.1 | Create pricing page | 3 | Tier comparison table |
| P2.1.2.2 | Create checkout flow | 3 | Stripe Elements integration |
| P2.1.2.3 | Create subscription management page | 2 | Current plan, billing history |
| P2.1.2.4 | Create upgrade modal | 2 | In-app upgrade prompts |
| P2.1.2.5 | Add tier badges throughout app | 1 | Show tier benefits |
| P2.1.2.6 | Write subscription UI tests | 2 | E2E tests for upgrade flow |

**Feature Total:** 13 points

---

#### Feature 2.1.3: Tier Enforcement

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P2.1.3.1 | Create tier limits configuration | 1 | Limits per tier (generations, storage) |
| P2.1.3.2 | Implement quota tracking | 2 | Track usage against limits |
| P2.1.3.3 | Create quota check middleware | 2 | Block actions when quota exceeded |
| P2.1.3.4 | Implement storage limit checks | 2 | Check before upload |
| P2.1.3.5 | Create limit reached UI components | 2 | Upgrade prompts when limited |
| P2.1.3.6 | Add quota reset job | 1 | Monthly quota reset |
| P2.1.3.7 | Write tier enforcement tests | 2 | API + E2E tests |

**Feature Total:** 12 points

---

### Epic 2.2: AI Suggestions

#### Feature 2.2.1: Printability Analysis (US-204)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P2.2.1.1 | Implement overhang detection | 3 | Identify surfaces > 45° |
| P2.2.1.2 | Implement thin wall detection | 2 | Find walls < 0.8mm |
| P2.2.1.3 | Implement bridging detection | 2 | Identify unsupported spans |
| P2.2.1.4 | Create suggestion generation | 2 | Generate improvement suggestions |
| P2.2.1.5 | Create suggestions panel UI | 2 | Display with highlighting |
| P2.2.1.6 | Implement one-click fixes | 3 | Apply suggestions automatically |
| P2.2.1.7 | Write printability tests | 2 | Test detection accuracy |

**Feature Total:** 16 points

---

### Epic 2.3: Design Sharing

#### Feature 2.3.1: Share Links (US-701)

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P2.3.1.1 | Create DesignShare model | 1 | Share tokens, permissions |
| P2.3.1.2 | Implement share link generation | 2 | POST /api/v1/designs/{id}/share |
| P2.3.1.3 | Create public view endpoint | 2 | GET /api/v1/public/designs/{token} |
| P2.3.1.4 | Implement user-specific sharing | 2 | Share with email addresses |
| P2.3.1.5 | Create share dialog component | 2 | Link generation, permission settings |
| P2.3.1.6 | Create shared designs page | 2 | "Shared with me" view |
| P2.3.1.7 | Implement access revocation | 1 | Remove share access |
| P2.3.1.8 | Write sharing tests | 2 | API + E2E tests |

**Feature Total:** 14 points

---

## Phase 3: Launch Prep (Weeks 18-20)

### Epic 3.1: Testing & QA

#### Feature 3.1.1: Unit Tests

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P3.1.1.1 | Backend auth service tests | 2 | 90%+ coverage |
| P3.1.1.2 | Backend CAD service tests | 3 | Test all operations |
| P3.1.1.3 | Backend job service tests | 2 | Queue, status, cancel |
| P3.1.1.4 | Backend moderation tests | 2 | Detection accuracy |
| P3.1.1.5 | Frontend component tests | 3 | Key components |
| P3.1.1.6 | Frontend hook tests | 2 | Custom hooks |

**Feature Total:** 14 points

---

#### Feature 3.1.2: Integration Tests

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P3.1.2.1 | Auth flow integration tests | 2 | Registration → login → logout |
| P3.1.2.2 | Design generation integration tests | 3 | NL → CAD → export |
| P3.1.2.3 | Subscription integration tests | 2 | Checkout → tier → limits |
| P3.1.2.4 | Queue integration tests | 2 | Submit → process → complete |
| P3.1.2.5 | API contract tests | 2 | OpenAPI validation |

**Feature Total:** 11 points

---

#### Feature 3.1.3: E2E Tests

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P3.1.3.1 | Critical path E2E tests | 3 | Register, generate, export |
| P3.1.3.2 | Subscription E2E tests | 2 | Upgrade, downgrade flows |
| P3.1.3.3 | Error handling E2E tests | 2 | Validation, network errors |
| P3.1.3.4 | Mobile responsiveness tests | 2 | Key pages on mobile |

**Feature Total:** 9 points

---

#### Feature 3.1.4: Performance Testing

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P3.1.4.1 | Set up k6 load testing | 2 | Configure test scripts |
| P3.1.4.2 | API endpoint load tests | 2 | Test key endpoints |
| P3.1.4.3 | CAD generation benchmarks | 2 | Measure generation times |
| P3.1.4.4 | Frontend performance audit | 2 | Lighthouse scores |
| P3.1.4.5 | Database query optimization | 2 | Identify slow queries |

**Feature Total:** 10 points

---

### Epic 3.2: Documentation

#### Feature 3.2.1: User Documentation

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P3.2.1.1 | Create getting started guide | 2 | First design tutorial |
| P3.2.1.2 | Create template guide | 2 | How to use templates |
| P3.2.1.3 | Create natural language guide | 2 | Tips for descriptions |
| P3.2.1.4 | Create export guide | 1 | Format options, settings |
| P3.2.1.5 | Create FAQ page | 2 | Common questions |

**Feature Total:** 9 points

---

#### Feature 3.2.2: Developer Documentation

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P3.2.2.1 | Update API documentation | 2 | OpenAPI spec complete |
| P3.2.2.2 | Create developer setup guide | 2 | Local development |
| P3.2.2.3 | Create contribution guidelines | 1 | Code style, PR process |
| P3.2.2.4 | Create architecture overview | 2 | System documentation |
| P3.2.2.5 | Create runbooks | 2 | Operational procedures |

**Feature Total:** 9 points

---

### Epic 3.3: Production Deployment

#### Feature 3.3.1: Infrastructure

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P3.3.1.1 | Deploy production infrastructure | 3 | Apply Terraform |
| P3.3.1.2 | Configure DNS and SSL | 2 | Domain, certificates |
| P3.3.1.3 | Set up CDN | 2 | CloudFront/CloudFlare |
| P3.3.1.4 | Configure auto-scaling | 2 | HPA for API/workers |
| P3.3.1.5 | Set up database replicas | 2 | Read replicas |

**Feature Total:** 11 points

---

#### Feature 3.3.2: Monitoring

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P3.3.2.1 | Set up Prometheus | 2 | Metrics collection |
| P3.3.2.2 | Set up Grafana dashboards | 3 | Key metrics visualization |
| P3.3.2.3 | Configure alerting | 2 | PagerDuty/Slack alerts |
| P3.3.2.4 | Set up log aggregation | 2 | CloudWatch/ELK |
| P3.3.2.5 | Configure error tracking | 1 | Sentry integration |

**Feature Total:** 10 points

---

#### Feature 3.3.3: Launch Checklist

| Task ID | Title | Points | Description |
|---------|-------|--------|-------------|
| P3.3.3.1 | Security audit | 3 | OWASP checklist |
| P3.3.3.2 | Backup verification | 2 | Test restore process |
| P3.3.3.3 | Load test production | 2 | Verify capacity |
| P3.3.3.4 | Create incident response plan | 2 | Runbooks, contacts |
| P3.3.3.5 | Final QA signoff | 2 | Complete testing |

**Feature Total:** 11 points

---

## Summary

### Total Story Points by Phase

| Phase | Epic | Points |
|-------|------|--------|
| **Phase 0** | Foundation | 71 |
| **Phase 1** | Core MVP | 360 |
| **Phase 2** | Monetization | 71 |
| **Phase 3** | Launch | 94 |
| **Total** | | **596** |

### Velocity Assumptions
- Team: 2 backend, 1 frontend, 0.5 DevOps
- Sprint: 2 weeks
- Velocity: ~40-50 points/sprint

### Estimated Timeline
- Phase 0: 2 sprints (4 weeks)
- Phase 1: 8 sprints (16 weeks)
- Phase 2: 2 sprints (4 weeks)
- Phase 3: 2 sprints (4 weeks)
- **Total: 14 sprints (28 weeks)** with buffer

### Critical Path

```
P0.1.1 (CAD POC) → P0.1.2 (AI POC) → P1.3 (NL Generation) → P1.5 (Queue) → P2.1 (Subscriptions)
                                          ↓
P0.2.1 (Repo) → P1.1 (Auth) → P1.2 (Templates) → P1.4 (Files) → P1.6 (Dashboard)
                                          ↓
                                    P3.1 (Testing) → P3.3 (Deploy)
```

---

*End of Work Breakdown Structure*
