# Functional Requirements Document (FRD)
# AI Part Designer

**Version:** 1.0  
**Date:** 2026-01-24  
**Status:** Draft  
**Author:** Business Analysis Team  

---

## Table of Contents
1. [Introduction](#1-introduction)
2. [System Overview](#2-system-overview)
3. [Functional Requirements](#3-functional-requirements)
4. [Non-Functional Requirements](#4-non-functional-requirements)
5. [System Interfaces](#5-system-interfaces)
6. [Data Requirements](#6-data-requirements)
7. [Security Requirements](#7-security-requirements)
8. [Appendices](#appendices)

---

## 1. Introduction

### 1.1 Purpose
This document defines the detailed functional and non-functional requirements for the AI Part Designer platform. It serves as the primary reference for development, testing, and validation activities.

### 1.2 Scope
This FRD covers the MVP release of AI Part Designer, including:
- Part generation and design workflows
- File upload and export functionality
- Queue and job processing system
- User authentication and subscription management
- Dashboard and project management
- Abuse detection and content moderation
- Backup and disaster recovery

### 1.3 Definitions & Abbreviations
| Term | Definition |
|------|------------|
| FR | Functional Requirement |
| NFR | Non-Functional Requirement |
| API | Application Programming Interface |
| JWT | JSON Web Token |
| RBAC | Role-Based Access Control |

### 1.4 References
- Business Requirements Document (BRD) v1.0
- User Stories Document
- Architecture Decision Records (ADRs)

---

## 2. System Overview

### 2.1 System Context Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USERS                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                │
│  │  Maker   │  │ Engineer │  │ Educator │  │  Admin   │                │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘                │
│       │             │             │             │                        │
└───────┼─────────────┼─────────────┼─────────────┼────────────────────────┘
        │             │             │             │
        └─────────────┴──────┬──────┴─────────────┘
                             │
                             ▼
        ┌─────────────────────────────────────────────┐
        │           AI PART DESIGNER PLATFORM          │
        │  ┌─────────────────────────────────────────┐ │
        │  │           Web Application (UI)          │ │
        │  └─────────────────┬───────────────────────┘ │
        │                    │                         │
        │  ┌─────────────────▼───────────────────────┐ │
        │  │              API Gateway                │ │
        │  └─────────────────┬───────────────────────┘ │
        │                    │                         │
        │  ┌────────┬────────┼────────┬────────┐      │
        │  ▼        ▼        ▼        ▼        ▼      │
        │ ┌────┐ ┌─────┐ ┌──────┐ ┌─────┐ ┌──────┐   │
        │ │Auth│ │Queue│ │Design│ │Files│ │Abuse │   │
        │ │Svc │ │ Svc │ │ Svc  │ │ Svc │ │Detect│   │
        │ └────┘ └─────┘ └──────┘ └─────┘ └──────┘   │
        │                    │                         │
        │  ┌─────────────────▼───────────────────────┐ │
        │  │           Data Layer (DB/Storage)       │ │
        │  └─────────────────────────────────────────┘ │
        └─────────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────────┐
        │    EXTERNAL SERVICES                         │
        │  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
        │  │ AI/LLM   │ │ Payment  │ │    Email     │ │
        │  │ Provider │ │ Gateway  │ │   Service    │ │
        │  └──────────┘ └──────────┘ └──────────────┘ │
        └──────────────────────────────────────────────┘
```

### 2.2 User Roles

| Role | Description | Access Level |
|------|-------------|--------------|
| Anonymous | Unauthenticated visitor | View marketing pages, pricing |
| Free User | Registered user, free tier | Limited features, standard queue |
| Pro User | Paid subscriber | Full features, priority queue |
| Enterprise User | Enterprise account | API access, team features |
| Admin | Platform administrator | Full system access, moderation |
| Super Admin | System administrator | Infrastructure, user management |

---

## 3. Functional Requirements

### 3.1 User Authentication & Authorization

#### FR-101: User Registration
| Attribute | Value |
|-----------|-------|
| **ID** | FR-101 |
| **Title** | User Registration |
| **Priority** | Must Have |
| **Description** | System shall allow new users to create an account |

**Inputs:**
- Email address (required, unique)
- Password (required, min 8 chars, complexity rules)
- Display name (required)
- Acceptance of Terms of Service (required)

**Process:**
1. Validate email format and uniqueness
2. Validate password meets complexity requirements
3. Create user record with "pending" status
4. Send verification email with token
5. Upon verification, activate account

**Outputs:**
- User account created
- Verification email sent
- Redirect to onboarding flow

**Acceptance Criteria:**
- Given a valid email and password, When user submits registration, Then account is created and verification email is sent
- Given an existing email, When user attempts registration, Then error message is displayed
- Given a weak password, When user attempts registration, Then password requirements are shown

---

#### FR-102: User Login
| Attribute | Value |
|-----------|-------|
| **ID** | FR-102 |
| **Title** | User Login |
| **Priority** | Must Have |
| **Description** | System shall authenticate users with email and password |

**Inputs:**
- Email address
- Password
- Remember me (optional)

**Process:**
1. Validate credentials against stored hash
2. Check account status (active, suspended, pending)
3. Generate JWT access token and refresh token
4. Log authentication event
5. Redirect to dashboard

**Outputs:**
- Access token (expires in 15 minutes)
- Refresh token (expires in 7 days, or 30 if "remember me")
- User profile data

**Acceptance Criteria:**
- Given valid credentials, When user logs in, Then user is authenticated and redirected to dashboard
- Given invalid credentials, When user attempts login, Then generic error is shown (prevent enumeration)
- Given suspended account, When user logs in, Then suspension message is displayed

---

#### FR-103: Password Reset
| Attribute | Value |
|-----------|-------|
| **ID** | FR-103 |
| **Title** | Password Reset |
| **Priority** | Must Have |
| **Description** | System shall allow users to reset forgotten passwords |

**Inputs:**
- Email address (for request)
- Reset token + new password (for reset)

**Process:**
1. Validate email exists (always show success to prevent enumeration)
2. Generate time-limited reset token (valid 1 hour)
3. Send reset email with secure link
4. Validate token and set new password

**Acceptance Criteria:**
- Given a registered email, When reset is requested, Then reset email is sent within 30 seconds
- Given a valid reset token, When new password is submitted, Then password is updated
- Given an expired token, When reset is attempted, Then error message is shown

---

#### FR-104: Role-Based Access Control
| Attribute | Value |
|-----------|-------|
| **ID** | FR-104 |
| **Title** | Role-Based Access Control |
| **Priority** | Should Have |
| **Description** | System shall enforce permissions based on user roles |

**Permissions Matrix:**

| Action | Anonymous | Free | Pro | Enterprise | Admin |
|--------|-----------|------|-----|------------|-------|
| View public content | ✓ | ✓ | ✓ | ✓ | ✓ |
| Create account | ✓ | - | - | - | - |
| Create designs | - | ✓ (limited) | ✓ | ✓ | ✓ |
| Upload files | - | ✓ (limited) | ✓ | ✓ | ✓ |
| Priority queue | - | - | ✓ | ✓ | ✓ |
| API access | - | - | - | ✓ | ✓ |
| View all users | - | - | - | - | ✓ |
| Moderate content | - | - | - | - | ✓ |

---

### 3.2 Part Design & Generation

#### FR-201: Natural Language Part Generation
| Attribute | Value |
|-----------|-------|
| **ID** | FR-201 |
| **Title** | Natural Language Part Generation |
| **Priority** | Must Have |
| **Description** | System shall generate 3D parts from natural language descriptions |

**Inputs:**
- Text description of desired part (max 2000 characters)
- Optional: target dimensions (length, width, height)
- Optional: material type hint (for wall thickness recommendations)

**Process:**
1. Parse and validate input text
2. Submit to abuse detection system
3. If approved, submit to AI generation queue
4. AI processes description and generates CAD geometry
5. Validate generated geometry (manifold, printable)
6. Store result and notify user

**Outputs:**
- 3D model file (internal format)
- Preview image (PNG/WebP)
- Geometry metadata (dimensions, volume, surface area)
- Generation report (success/warnings/suggestions)

**Acceptance Criteria:**
- Given a clear description "a box with lid 100mm x 50mm x 30mm", When submitted, Then valid geometry is generated matching dimensions ±5%
- Given an ambiguous description, When submitted, Then system requests clarification or makes reasonable assumptions with explanation
- Given a prohibited description, When submitted, Then request is rejected with policy message

**Example Inputs:**
```
"Create a rectangular project box with dimensions 100mm x 60mm x 40mm with 
screw posts in each corner and a removable lid with snap-fit tabs"
```

---

#### FR-202: Template Library
| Attribute | Value |
|-----------|-------|
| **ID** | FR-202 |
| **Title** | Template Library |
| **Priority** | Must Have |
| **Description** | System shall provide pre-built parametric templates for common part types |

**Template Categories:**
| Category | Templates | Tier |
|----------|-----------|------|
| Enclosures | Project box, Electronics enclosure, Wall-mount box | Free |
| Brackets | L-bracket, Corner bracket, Adjustable bracket | Free |
| Mechanical | Gear, Pulley, Bearing mount, Shaft coupler | Pro |
| Fasteners | Knob, Handle, Standoff, Cable clip | Free |
| Organization | Drawer divider, Pegboard hook, Tool holder | Free |
| Custom | User-created templates | Pro |

**Template Parameters:**
Each template exposes configurable parameters:
- Dimensions (length, width, height, thickness)
- Features (holes, slots, fillets, chamfers)
- Mounting options (screw holes, snap-fits, magnets)
- Material presets (PLA, PETG, ABS wall thickness defaults)

**Acceptance Criteria:**
- Given the template library, When user browses, Then templates are organized by category with previews
- Given a selected template, When user adjusts parameters, Then preview updates in real-time
- Given invalid parameters, When user attempts generation, Then validation errors are shown

---

#### FR-203: Template Customization
| Attribute | Value |
|-----------|-------|
| **ID** | FR-203 |
| **Title** | Template Customization |
| **Priority** | Must Have |
| **Description** | System shall allow users to customize template parameters |

**Customization Interface:**
- Parameter sliders with numeric input
- Real-time 3D preview updates
- Undo/redo for parameter changes
- Reset to defaults button
- Save as new template (Pro users)

**Validation Rules:**
| Parameter | Validation |
|-----------|------------|
| Wall thickness | Min 0.8mm, Max 10mm |
| Overall dimensions | Max 500mm per axis |
| Hole diameter | Min 1mm, Max 100mm |
| Fillet radius | Max 50% of smallest adjacent dimension |

---

#### FR-204: AI Optimization Suggestions
| Attribute | Value |
|-----------|-------|
| **ID** | FR-204 |
| **Title** | AI Optimization Suggestions |
| **Priority** | Should Have |
| **Description** | System shall provide AI-powered suggestions to improve designs |

**Suggestion Categories:**
1. **Printability**
   - Overhang warnings (>45°)
   - Support requirement estimates
   - Bridge length warnings

2. **Structural**
   - Wall thickness recommendations
   - Stress concentration warnings
   - Infill suggestions for load-bearing areas

3. **Material Efficiency**
   - Volume reduction opportunities
   - Alternative design approaches
   - Weight optimization

**Output Format:**
```json
{
  "suggestions": [
    {
      "type": "printability",
      "severity": "warning",
      "message": "Overhang at 52° may require supports",
      "location": {"x": 45.2, "y": 12.1, "z": 28.0},
      "recommendation": "Add 45° chamfer or fillet to base"
    }
  ]
}
```

---

#### FR-205: Design Modification
| Attribute | Value |
|-----------|-------|
| **ID** | FR-205 |
| **Title** | Design Modification via AI |
| **Priority** | Must Have |
| **Description** | System shall allow users to modify designs using natural language commands |

**Modification Commands:**
| Command Type | Example |
|--------------|---------|
| Dimensional | "Make it 20% larger" |
| Feature Add | "Add a hole for M5 bolt on the top face" |
| Feature Remove | "Remove the tabs on the sides" |
| Feature Modify | "Make the corners more rounded" |
| Combine | "Add a mounting bracket to the left side" |

**Process:**
1. Parse modification request
2. Identify target geometry and operation
3. Apply transformation
4. Validate resulting geometry
5. Show before/after comparison
6. Allow accept/reject

---

### 3.3 File Management

#### FR-301: File Upload
| Attribute | Value |
|-----------|-------|
| **ID** | FR-301 |
| **Title** | File Upload |
| **Priority** | Must Have |
| **Description** | System shall accept file uploads for viewing and modification |

**Supported Formats:**
| Format | Extension | Max Size | Tier |
|--------|-----------|----------|------|
| STEP | .step, .stp | 100MB | Free |
| STL | .stl | 50MB | Free |
| OBJ | .obj | 50MB | Pro |
| 3MF | .3mf | 100MB | Pro |

**Upload Process:**
1. Client-side validation (format, size)
2. Chunked upload for files > 10MB
3. Server-side validation and virus scan
4. Geometry parsing and validation
5. Thumbnail generation
6. Storage in user's project space

**Acceptance Criteria:**
- Given a valid STEP file, When uploaded, Then file is parsed and preview is shown within 30 seconds
- Given an oversized file, When upload attempted, Then error with size limit is shown
- Given a corrupted file, When uploaded, Then appropriate error message is displayed

---

#### FR-302: File Preview
| Attribute | Value |
|-----------|-------|
| **ID** | FR-302 |
| **Title** | 3D File Preview |
| **Priority** | Must Have |
| **Description** | System shall display interactive 3D preview of designs |

**Preview Features:**
- Orbit, pan, zoom controls
- Standard views (front, back, left, right, top, bottom, isometric)
- Wireframe/solid/transparent render modes
- Measurement tool (distance between points)
- Section view (cut plane)

**Performance Requirements:**
- Models up to 100k triangles: 60fps
- Models up to 1M triangles: 30fps
- Progressive loading for large models

---

#### FR-303: File Export
| Attribute | Value |
|-----------|-------|
| **ID** | FR-303 |
| **Title** | File Export |
| **Priority** | Must Have |
| **Description** | System shall export designs in multiple formats |

**Export Formats:**
| Format | Use Case | Quality Options |
|--------|----------|-----------------|
| STL | 3D printing | Low/Medium/High polygon count |
| STEP | CAD interchange | AP203/AP214 |
| OBJ | General 3D | With/without materials |
| 3MF | 3D printing | With print settings |

**Export Options:**
- Coordinate system orientation
- Units (mm, inches)
- Scale factor
- Merge components (single/multiple bodies)

---

#### FR-304: Version History
| Attribute | Value |
|-----------|-------|
| **ID** | FR-304 |
| **Title** | Design Version History |
| **Priority** | Should Have |
| **Description** | System shall maintain version history for designs |

**Versioning Behavior:**
- New version created on: Save, Major modification, Export
- Maximum versions retained: 20 (Free), 100 (Pro)
- Version metadata: timestamp, change description, thumbnail

**Version Operations:**
- View any version
- Restore previous version (creates new version)
- Compare versions side-by-side
- Delete specific versions (except current)

---

#### FR-305: Trash Bin
| Attribute | Value |
|-----------|-------|
| **ID** | FR-305 |
| **Title** | Trash Bin for Deleted Files |
| **Priority** | Should Have |
| **Description** | System shall retain deleted files for recovery |

**Retention Policy:**
- Free tier: 14 days
- Pro tier: 30 days
- Automatic permanent deletion after retention period
- Manual permanent deletion available
- Notification 3 days before permanent deletion

---

### 3.4 Queue & Job Processing

#### FR-401: Job Submission
| Attribute | Value |
|-----------|-------|
| **ID** | FR-401 |
| **Title** | Job Submission |
| **Priority** | Must Have |
| **Description** | System shall queue design generation jobs |

**Job Types:**
| Type | Description | Typical Duration |
|------|-------------|------------------|
| generate | New part from description | 30-120 seconds |
| modify | Modify existing design | 15-60 seconds |
| convert | File format conversion | 5-30 seconds |
| analyze | Design analysis/suggestions | 10-45 seconds |

**Job Data:**
```json
{
  "jobId": "uuid",
  "userId": "uuid",
  "type": "generate",
  "priority": "standard|priority",
  "status": "queued|processing|completed|failed",
  "input": { ... },
  "createdAt": "timestamp",
  "startedAt": "timestamp",
  "completedAt": "timestamp"
}
```

---

#### FR-402: Job Status Tracking
| Attribute | Value |
|-----------|-------|
| **ID** | FR-402 |
| **Title** | Job Status Tracking |
| **Priority** | Must Have |
| **Description** | System shall provide real-time job status updates |

**Status States:**
```
queued → processing → completed
                   ↘ failed
                   ↘ cancelled
```

**Status Information:**
- Current state
- Queue position (if queued)
- Progress percentage (if processing)
- Estimated time remaining
- Error details (if failed)

**Delivery Methods:**
- Polling API endpoint
- WebSocket real-time updates
- Email notification on completion (optional)

---

#### FR-403: Priority Queue
| Attribute | Value |
|-----------|-------|
| **ID** | FR-403 |
| **Title** | Subscription-Based Priority Queue |
| **Priority** | Must Have |
| **Description** | System shall prioritize jobs based on subscription tier |

**Queue Priority Levels:**
| Tier | Priority | Max Concurrent | Max Queue |
|------|----------|----------------|-----------|
| Free | Standard | 1 | 3 |
| Pro | High | 3 | 10 |
| Enterprise | Highest | 10 | 50 |

**Priority Behavior:**
- Higher priority jobs processed before lower
- Within same priority, FIFO ordering
- Priority jobs can preempt queue position but not running jobs
- Fair scheduling to prevent starvation of lower tiers

---

### 3.5 Dashboard & Projects

#### FR-501: User Dashboard
| Attribute | Value |
|-----------|-------|
| **ID** | FR-501 |
| **Title** | User Dashboard |
| **Priority** | Must Have |
| **Description** | System shall provide personalized dashboard for users |

**Dashboard Sections:**
1. **Quick Actions**
   - New design from description
   - New design from template
   - Upload file

2. **Recent Projects** (last 10)
   - Thumbnail, name, last modified
   - Quick actions: open, duplicate, delete

3. **Active Jobs**
   - Status, progress, ETA
   - Cancel option

4. **Usage Statistics**
   - Designs created this month
   - Storage used
   - Remaining quota (free tier)

---

#### FR-502: Project Management
| Attribute | Value |
|-----------|-------|
| **ID** | FR-502 |
| **Title** | Project Management |
| **Priority** | Must Have |
| **Description** | System shall allow organizing designs into projects |

**Project Features:**
- Create, rename, delete projects
- Move designs between projects
- Project-level sharing settings
- Bulk export project contents

**Default Projects:**
- "My Designs" (default project)
- "Shared with Me" (virtual, read-only)
- "Trash" (virtual, deleted items)

---

### 3.6 Abuse Detection & Content Moderation

#### FR-601: Content Filtering
| Attribute | Value |
|-----------|-------|
| **ID** | FR-601 |
| **Title** | Input Content Filtering |
| **Priority** | Must Have |
| **Description** | System shall filter prohibited content from design requests |

**Detection Layers:**
1. **Keyword Filtering**
   - Blocklist of prohibited terms
   - Pattern matching for obfuscation attempts

2. **AI Intent Classification**
   - ML model trained on prohibited design categories
   - Confidence threshold for auto-reject vs. human review

3. **Output Validation**
   - Geometric analysis for weapon-like shapes
   - Cross-reference against prohibited design database

**Prohibited Categories:**
- Weapons and weapon components
- Illegal items (lock picks, skimmers, etc.)
- Trademark/copyright infringing designs
- Explicit content

**Response Actions:**
| Confidence | Action |
|------------|--------|
| > 95% | Auto-reject with message |
| 70-95% | Queue for human review |
| < 70% | Allow with logging |

---

#### FR-602: Rate Limiting
| Attribute | Value |
|-----------|-------|
| **ID** | FR-602 |
| **Title** | Rate Limiting |
| **Priority** | Must Have |
| **Description** | System shall enforce rate limits to prevent abuse |

**Rate Limits:**
| Resource | Free | Pro | Enterprise |
|----------|------|-----|------------|
| Generations/hour | 5 | 30 | 100 |
| Uploads/hour | 10 | 50 | 200 |
| API calls/minute | N/A | 60 | 300 |

**Rate Limit Response:**
- HTTP 429 Too Many Requests
- Retry-After header
- Remaining quota in response headers

---

#### FR-603: Admin Moderation Tools
| Attribute | Value |
|-----------|-------|
| **ID** | FR-603 |
| **Title** | Admin Moderation Interface |
| **Priority** | Should Have |
| **Description** | System shall provide tools for admins to review flagged content |

**Moderation Queue:**
- List of flagged items sorted by severity
- User history and prior violations
- Design preview (sandboxed)
- Quick actions: approve, reject, warn, suspend

**Moderation Actions:**
| Action | Effect |
|--------|--------|
| Approve | Release from hold, update ML model |
| Reject | Delete content, notify user |
| Warn | Release with warning to user |
| Suspend | Suspend user account pending review |

---

### 3.7 Notifications

#### FR-701: Email Notifications
| Attribute | Value |
|-----------|-------|
| **ID** | FR-701 |
| **Title** | Email Notifications |
| **Priority** | Should Have |
| **Description** | System shall send email notifications for key events |

**Notification Types:**
| Event | Default | User Configurable |
|-------|---------|-------------------|
| Welcome/verification | Always | No |
| Password reset | Always | No |
| Job completed | On | Yes |
| Job failed | On | Yes |
| Shared design | On | Yes |
| Subscription expiring | Always | No |
| File deletion warning | Always | No |

---

### 3.8 Backup & Recovery

#### FR-801: Automated Backups
| Attribute | Value |
|-----------|-------|
| **ID** | FR-801 |
| **Title** | Automated Backups |
| **Priority** | Must Have |
| **Description** | System shall perform automated backups of all data |

**Backup Schedule:**
| Data Type | Frequency | Retention |
|-----------|-----------|-----------|
| Database | Hourly | 7 days |
| User files | Daily | 30 days |
| System config | On change | 90 days |

**Backup Locations:**
- Primary: Same region, different availability zone
- Secondary: Different region (disaster recovery)

---

#### FR-802: Data Export
| Attribute | Value |
|-----------|-------|
| **ID** | FR-802 |
| **Title** | User Data Export |
| **Priority** | Should Have |
| **Description** | System shall allow users to export all their data |

**Export Contents:**
- All design files (original format + standard exports)
- Project structure
- Account information
- Activity history

**Export Format:**
- ZIP archive
- Manifest file with file inventory
- Available within 24 hours of request

---

## 4. Non-Functional Requirements

### 4.1 Performance

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-P01 | Page load time | < 3 seconds |
| NFR-P02 | API response time (95th percentile) | < 500ms |
| NFR-P03 | 3D preview frame rate (100k triangles) | 60 fps |
| NFR-P04 | Simple generation completion | < 60 seconds |
| NFR-P05 | Complex generation completion | < 120 seconds |
| NFR-P06 | File upload speed | Limited by user bandwidth |
| NFR-P07 | Concurrent users supported | 1,000 |

### 4.2 Scalability

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-S01 | Horizontal scaling | Support auto-scaling |
| NFR-S02 | Queue throughput | 1,000 jobs/hour |
| NFR-S03 | Storage capacity | Unlimited (cloud storage) |
| NFR-S04 | Database connections | 100 concurrent |

### 4.3 Availability & Reliability

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-A01 | System uptime | 99.9% |
| NFR-A02 | Planned maintenance window | < 4 hours/month |
| NFR-A03 | RTO (Recovery Time Objective) | 4 hours |
| NFR-A04 | RPO (Recovery Point Objective) | 1 hour |
| NFR-A05 | Data durability | 99.999999999% (11 nines) |

### 4.4 Security

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-SEC01 | Data encryption at rest | AES-256 |
| NFR-SEC02 | Data encryption in transit | TLS 1.3 |
| NFR-SEC03 | Password hashing | bcrypt (cost factor 12) |
| NFR-SEC04 | Session management | Secure, HttpOnly cookies |
| NFR-SEC05 | Vulnerability scanning | Weekly automated scans |
| NFR-SEC06 | Penetration testing | Annual third-party audit |

### 4.5 Usability

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-U01 | Time to first design (new user) | < 5 minutes |
| NFR-U02 | Mobile responsive | Yes |
| NFR-U03 | Accessibility | WCAG 2.1 AA |
| NFR-U04 | Browser support | Latest 2 versions of Chrome, Firefox, Safari, Edge |
| NFR-U05 | Internationalization ready | Unicode support, externalized strings |

### 4.6 Compliance

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-C01 | GDPR compliance | Required for EU users |
| NFR-C02 | Data retention policy | Documented and enforced |
| NFR-C03 | Privacy policy | Published and accessible |
| NFR-C04 | Terms of service | Published and accessible |
| NFR-C05 | Cookie consent | Required |

---

## 5. System Interfaces

### 5.1 External Interfaces

| Interface | Type | Description |
|-----------|------|-------------|
| AI/LLM Provider | API | Natural language processing and generation |
| Payment Gateway | API | Subscription billing (Stripe) |
| Email Service | API | Transactional emails (SendGrid) |
| Cloud Storage | API | File storage (S3-compatible) |
| Analytics | SDK | Usage tracking (optional) |
| Error Tracking | SDK | Exception monitoring (Sentry) |

### 5.2 API Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/v1/auth/register | POST | User registration |
| /api/v1/auth/login | POST | User login |
| /api/v1/auth/refresh | POST | Refresh access token |
| /api/v1/users/me | GET | Current user profile |
| /api/v1/designs | GET, POST | List/create designs |
| /api/v1/designs/{id} | GET, PATCH, DELETE | Design CRUD |
| /api/v1/designs/{id}/export | POST | Export design |
| /api/v1/templates | GET | List templates |
| /api/v1/jobs | GET, POST | List/submit jobs |
| /api/v1/jobs/{id} | GET | Job status |
| /api/v1/uploads | POST | Upload file |

---

## 6. Data Requirements

### 6.1 Data Entities

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    User     │───────│   Project   │───────│   Design    │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id          │       │ id          │       │ id          │
│ email       │       │ userId      │       │ projectId   │
│ password    │       │ name        │       │ name        │
│ displayName │       │ createdAt   │       │ description │
│ role        │       │ updatedAt   │       │ sourceType  │
│ subscription│       └─────────────┘       │ fileUrl     │
│ createdAt   │                              │ thumbnailUrl│
│ updatedAt   │                              │ metadata    │
└─────────────┘                              │ versions[]  │
                                             │ createdAt   │
┌─────────────┐       ┌─────────────┐       │ updatedAt   │
│     Job     │───────│   Design    │       └─────────────┘
├─────────────┤       └─────────────┘
│ id          │
│ userId      │       ┌─────────────┐
│ designId    │       │   Version   │
│ type        │       ├─────────────┤
│ status      │       │ id          │
│ priority    │       │ designId    │
│ input       │       │ versionNum  │
│ output      │       │ fileUrl     │
│ createdAt   │       │ changeDesc  │
│ startedAt   │       │ createdAt   │
│ completedAt │       └─────────────┘
└─────────────┘
```

### 6.2 Data Retention

| Data Type | Retention | After Deletion |
|-----------|-----------|----------------|
| Active user data | Indefinite | N/A |
| Deleted user data | 30 days | Permanent delete |
| Trashed designs | 14-30 days | Permanent delete |
| Job history | 90 days | Archive/delete |
| Audit logs | 1 year | Archive |
| Backups | Per schedule | Automatic rotation |

---

## 7. Security Requirements

### 7.1 Authentication
- Multi-factor authentication (optional, recommended for admin)
- OAuth 2.0 / OpenID Connect support (Google, GitHub)
- JWT tokens with short expiry (15 min access, 7 day refresh)
- Secure password reset flow with expiring tokens

### 7.2 Authorization
- RBAC with clearly defined roles
- API endpoint authorization middleware
- Resource-level permissions (design ownership)

### 7.3 Data Protection
- Encryption at rest and in transit
- Secure key management (cloud KMS)
- PII handling per GDPR requirements
- Regular access audits

### 7.4 Application Security
- Input validation on all endpoints
- CSRF protection
- XSS prevention (Content Security Policy)
- SQL injection prevention (parameterized queries)
- Dependency vulnerability scanning

---

## Appendices

### Appendix A: Requirements Traceability Matrix

| Business Req | Functional Req | User Story |
|--------------|----------------|------------|
| BR-001 | FR-201 | US-001 |
| BR-002 | FR-202 | US-002 |
| BR-003 | FR-203 | US-003 |
| BR-010 | FR-301 | US-010 |
| BR-011 | FR-302 | US-011 |
| BR-020 | FR-401 | US-020 |
| BR-030 | FR-101, FR-102 | US-030 |
| BR-040 | FR-601, FR-602 | US-040 |

### Appendix B: Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-24 | BA Team | Initial draft |

---

*End of Document*
