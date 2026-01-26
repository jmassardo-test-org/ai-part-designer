# Sprint Backlog
# AI Part Designer

**Version:** 2.0  
**Date:** 2026-01-24  
**Status:** Full Roadmap Complete - Sprints 15-40 Ready  

---

## How to Use This Document

Each task below is "ready for development" with:
- Clear acceptance criteria
- Technical implementation notes
- Test requirements
- Definition of Done

Tasks are organized by sprint and can be assigned directly.

---

## Sprint 1: Foundation Setup (Week 1-2) ✅ COMPLETE

### Sprint Goal
Validate CAD and AI technology, set up development environment.

### Tasks

---

#### P0.1.1.1: Set up CadQuery Development Environment ✅
**Points:** 1 | **Assignee:** Backend | **Priority:** P0 | **Status:** DONE

**Description:**
Create a Docker container with CadQuery, OpenCASCADE, and all dependencies properly configured.

**Technical Notes:**
- Use `cadquery/cadquery:latest` as base image or build from scratch
- Include `cadquery`, `ocp`, `vtk` for visualization
- Configure for headless operation (no GUI)
- Set up volume mounts for output files

**Acceptance Criteria:**
- [x] Docker container builds successfully
- [x] Can run `import cadquery as cq` without errors
- [x] Can generate a simple box and export to STEP
- [x] Container size < 2GB

**Test Requirements:**
- Container build test in CI
- Basic import test script

**Definition of Done:**
- [x] Code reviewed and merged
- [x] Container published to registry
- [x] Documentation updated

---

#### P0.1.1.2: Create Basic Primitive Generation ✅
**Points:** 2 | **Assignee:** Backend | **Priority:** P0 | **Status:** DONE

**Description:**
Implement functions to generate basic 3D primitives (box, cylinder, sphere) with parameterized dimensions.

**Technical Notes:**
```python
# Target API
def create_box(length: float, width: float, height: float) -> cq.Workplane
def create_cylinder(radius: float, height: float) -> cq.Workplane
def create_sphere(radius: float) -> cq.Workplane
```
- Place in `backend/app/cad/primitives.py`
- All dimensions in millimeters
- Origin at center-bottom of shape
- Return CadQuery Workplane objects

**Acceptance Criteria:**
- [x] Box: correct dimensions ±0.01mm
- [x] Cylinder: correct radius and height
- [x] Sphere: correct radius
- [x] All shapes centered on XY plane
- [x] Functions handle edge cases (zero, negative)

**Test Requirements:**
- Unit tests for each primitive
- Dimension verification tests
- Edge case tests (min/max values)

**Files Created:**
- `backend/app/cad/__init__.py` ✅
- `backend/app/cad/primitives.py` ✅
- `backend/tests/cad/test_primitives.py` ✅

---

#### P0.1.1.3: Implement Boolean Operations ✅
**Points:** 2 | **Assignee:** Backend | **Priority:** P0 | **Status:** DONE

**Description:**
Implement boolean operations (union, difference, intersection) between CadQuery shapes.

**Technical Notes:**
```python
def union(shape1: cq.Workplane, shape2: cq.Workplane) -> cq.Workplane
def difference(base: cq.Workplane, tool: cq.Workplane) -> cq.Workplane
def intersection(shape1: cq.Workplane, shape2: cq.Workplane) -> cq.Workplane
```
- Handle positioning with translation
- Return new shape (immutable operations)

**Acceptance Criteria:**
- [x] Union combines two shapes
- [x] Difference subtracts tool from base
- [x] Intersection returns common volume
- [x] Handles non-overlapping shapes gracefully

**Test Requirements:**
- Boolean operation tests
- Position offset tests
- Edge cases (no overlap, full containment)

**Files Created:**
- `backend/app/cad/operations.py` ✅
- `backend/tests/cad/test_operations.py` ✅

---

#### P0.1.1.5: Implement STEP/STL Export ✅
**Points:** 2 | **Assignee:** Backend | **Priority:** P0 | **Status:** DONE

**Description:**
Create export functions for STEP and STL formats with quality options.

**Technical Notes:**
```python
def export_step(shape: cq.Workplane, filepath: Path) -> None
def export_stl(
    shape: cq.Workplane, 
    filepath: Path, 
    quality: Literal["low", "medium", "high"] = "medium"
) -> None
```
- Quality maps to tessellation tolerance:
  - low: 0.5mm
  - medium: 0.1mm  
  - high: 0.01mm
- Support both binary and ASCII STL

**Acceptance Criteria:**
- [x] STEP files valid and openable in CAD software
- [x] STL files have correct triangle count for quality
- [x] Files write atomically (temp file + rename)
- [x] Errors raise appropriate exceptions

**Files Created:**
- `backend/app/cad/export.py` ✅
- `backend/tests/cad/test_export.py` ✅

---

#### P0.2.1.1: Create Monorepo Structure ✅
**Points:** 1 | **Assignee:** DevOps | **Priority:** P0 | **Status:** DONE

**Description:**
Set up the monorepo directory structure with appropriate configuration files.

**Technical Notes:**
```
ai-part-designer/
├── .github/
│   └── workflows/
├── backend/
│   ├── app/
│   ├── tests/
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   ├── public/
│   ├── Dockerfile
│   └── package.json
├── infrastructure/
│   └── terraform/
├── docs/
├── scripts/
├── docker-compose.yml
├── Makefile
└── README.md
```

**Acceptance Criteria:**
- [x] All directories created
- [x] .gitignore configured for Python and Node
- [x] README with project overview
- [x] LICENSE file present

**Files Created:**
- Directory structure as shown ✅
- `.gitignore` ✅
- `LICENSE` ✅

---

#### P0.2.1.4: Create Docker Compose for Local Dev ✅
**Points:** 2 | **Assignee:** DevOps | **Priority:** P0 | **Status:** DONE

**Description:**
Create Docker Compose configuration for local development with all services.

**Technical Notes:**
```yaml
services:
  api:
    build: ./backend
    ports: ["8000:8000"]
    volumes: ["./backend:/app"]
    depends_on: [db, redis]
  worker:
    build: ./backend
    command: celery -A app.worker worker
    depends_on: [db, redis]
  db:
    image: postgres:15
    volumes: ["pgdata:/var/lib/postgresql/data"]
  redis:
    image: redis:7-alpine
  minio:
    image: minio/minio
    ports: ["9000:9000", "9001:9001"]
```

**Acceptance Criteria:**
- [x] All services start with `docker-compose up`
- [x] API accessible at localhost:8000
- [x] Hot reload works for backend code
- [x] Data persists between restarts
- [x] Services can communicate

**Files Created:**
- `docker-compose.yml` ✅
- `docker-compose.test.yml` ✅
- `.env.example` ✅

---

#### P0.2.1.6: Create Makefile with Dev Commands ✅
**Points:** 1 | **Assignee:** DevOps | **Priority:** P0 | **Status:** DONE

**Description:**
Create Makefile with common development commands.

**Commands Required:**
```makefile
dev:          # Start all services
stop:         # Stop all services
test:         # Run all tests
test-backend: # Run backend tests
test-frontend: # Run frontend tests
lint:         # Run linters
format:       # Format code
migrate:      # Run database migrations
shell:        # Open backend shell
logs:         # Tail all logs
clean:        # Clean up containers/volumes
```

**Acceptance Criteria:**
- [x] All commands work as expected
- [x] Help text available with `make help`
- [x] Works on macOS and Linux

---

### Sprint 1 Total: 11 points ✅ COMPLETE

---

## Sprint 2: AI Integration POC (Week 3-4) ✅ COMPLETE

### Sprint Goal
Validate AI-to-CAD pipeline, set up CI/CD.

### Tasks

---

#### P0.1.2.1: Set up OpenAI Integration ✅
**Points:** 1 | **Assignee:** Backend | **Priority:** P0 | **Status:** DONE

**Description:**
Create OpenAI client wrapper with proper configuration, rate limiting, and error handling.

**Technical Notes:**
```python
# backend/app/ai/client.py
class OpenAIClient:
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
    async def complete(
        self, 
        messages: list[dict], 
        model: str = "gpt-4",
        temperature: float = 0.3,
    ) -> str:
        # Implement with retry logic, rate limiting
```

**Acceptance Criteria:**
- [x] Client configurable via environment
- [x] Retry on rate limits (exponential backoff)
- [x] Timeout handling (30s default)
- [x] Usage logging for cost tracking

**Files Created:**
- `backend/app/ai/__init__.py` ✅
- `backend/app/ai/client.py` ✅
- `backend/tests/ai/test_client.py` ✅

---

#### P0.1.2.2: Create Prompt Engineering Framework ✅
**Points:** 3 | **Assignee:** Backend | **Priority:** P0 | **Status:** DONE

**Description:**
Design and implement prompt templates for extracting CAD parameters from natural language.

**Technical Notes:**
```python
# backend/app/ai/prompts.py
DIMENSION_EXTRACTION_PROMPT = """
You are a CAD engineer assistant. Extract dimensions and features from the following description.

Description: {user_input}

Respond with JSON:
{
  "shape": "box|cylinder|sphere|...",
  "dimensions": {"length": float, "width": float, "height": float},
  "features": [...],
  "units": "mm|inches"
}
"""
```

**Acceptance Criteria:**
- [x] Prompt extracts dimensions accurately
- [x] Handles multiple units (mm, cm, inches)
- [x] Returns structured JSON
- [x] Includes confidence score

**Files Created:**
- `backend/app/ai/prompts.py` ✅
- `backend/tests/ai/test_prompts.py` ✅

---

#### P0.1.2.3: Build NL→JSON Parser ✅
**Points:** 3 | **Assignee:** Backend | **Priority:** P0 | **Status:** DONE

**Description:**
Create parser that converts natural language to structured CAD parameters using AI.

**Technical Notes:**
```python
# backend/app/ai/parser.py
from pydantic import BaseModel

class CADParameters(BaseModel):
    shape: str
    dimensions: dict[str, float]
    features: list[dict]
    units: str = "mm"

async def parse_description(description: str) -> CADParameters:
    # Call OpenAI with prompt
    # Parse and validate response
    # Convert units to mm
    return CADParameters(...)
```

**Acceptance Criteria:**
- [x] Parses box descriptions correctly
- [x] Parses cylinder descriptions
- [x] Handles unit conversion
- [x] Validates output schema
- [x] Returns helpful error on parse failure

**Files Created:**
- `backend/app/ai/parser.py` ✅
- `backend/tests/ai/test_parser.py` ✅

---

#### P0.1.2.5: Create End-to-End Generation Test ✅
**Points:** 2 | **Assignee:** Backend | **Priority:** P0 | **Status:** DONE

**Description:**
Build end-to-end test from natural language input to STEP file output.

**Technical Notes:**
```python
async def generate_from_description(description: str) -> Path:
    # 1. Parse description → CADParameters
    params = await parse_description(description)
    
    # 2. Generate shape from parameters
    shape = generate_shape(params)
    
    # 3. Export to file
    output_path = export_step(shape, generate_filename())
    
    return output_path
```

**Acceptance Criteria:**
- [x] "Create a box 100x50x30mm" → valid STEP file
- [x] "Make a cylinder 50mm diameter, 100mm tall" → valid STEP
- [x] End-to-end time < 30 seconds
- [x] Generated file matches dimensions

**Files Created:**
- `backend/app/ai/generator.py` ✅
- `backend/tests/ai/test_generator.py` ✅

---

#### P0.2.2.1: Create GitHub Actions Test Workflow ✅
**Points:** 2 | **Assignee:** DevOps | **Priority:** P0 | **Status:** DONE

**Description:**
Create CI workflow to run tests on push and pull requests.

**Technical Notes:**
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -e ".[test]"
      - run: pytest --cov
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci && npm test
```

**Acceptance Criteria:**
- [x] Runs on push to main and PRs
- [x] Backend tests with coverage report
- [x] Frontend tests with coverage
- [x] Fails PR if tests fail
- [x] Caches dependencies

**Files Created:**
- `.github/workflows/test.yml` ✅

---

#### P0.2.2.3: Create Build Workflow ✅
**Points:** 2 | **Assignee:** DevOps | **Priority:** P0 | **Status:** DONE

**Description:**
Create CI workflow to build Docker images.

**Technical Notes:**
```yaml
# .github/workflows/build.yml
name: Build
on:
  push:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: docker/build-push-action@v5
        with:
          context: ./backend
          tags: ghcr.io/org/api:${{ github.sha }}
          push: ${{ github.ref == 'refs/heads/main' }}
```

**Acceptance Criteria:**
- [x] Builds API and worker images
- [x] Tags with git SHA
- [x] Pushes to container registry on main
- [x] Build cache enabled

**Files Created:**
- `.github/workflows/build.yml` ✅

---

### Sprint 2 Total: 13 points ✅ COMPLETE

---

## Sprint 3-4: Authentication (Week 5-6) ✅ COMPLETE

### Sprint Goal
Complete user authentication system.

### Tasks

---

#### P1.1.1.1: Create User Model and Migration ✅
**Points:** 2 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
User model already exists. Verify and update if needed.

**Technical Notes:**
Review existing `backend/app/models/user.py`:
- Ensure all fields from US-101 are present
- Add any missing fields (subscription_tier, etc.)
- Create Alembic migration if changes needed

**Acceptance Criteria:**
- [x] User model has all required fields
- [x] Migration runs successfully
- [x] Indexes on email, status

---

#### P1.1.1.3: Create Registration Endpoint ✅
**Points:** 2 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
Implement user registration API endpoint.

**Technical Notes:**
```python
# backend/app/api/v1/auth.py
@router.post("/register", response_model=UserResponse)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    # Validate email uniqueness
    # Hash password
    # Create user with pending status
    # Send verification email
    return user
```

**Request Schema:**
```python
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=2, max_length=50)
    accepted_terms: bool = True
```

**Acceptance Criteria:**
- [x] Creates user with pending status
- [x] Returns user data (no password)
- [x] 409 if email exists
- [x] 422 if validation fails

**Files Created:**
- `backend/app/api/v1/auth.py` ✅
- `backend/tests/api/test_auth.py` ✅

---

#### P1.1.1.6: Create Email Verification Service ✅
**Points:** 2 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
Implement email verification token generation and sending.

**Technical Notes:**
```python
# backend/app/services/email.py
class EmailService:
    async def send_verification_email(self, user: User):
        token = create_verification_token(user.id)
        link = f"{settings.FRONTEND_URL}/verify?token={token}"
        await self._send_email(
            to=user.email,
            template="verification",
            context={"name": user.display_name, "link": link}
        )
```

**Acceptance Criteria:**
- [x] Token valid for 24 hours
- [x] Email sent via SendGrid/SES
- [x] Rate limit: 1 email per 60 seconds
- [x] HTML and plain text versions

**Files Created:**
- `backend/app/services/email.py` ✅
- `backend/tests/services/test_email.py` ✅

---

#### P1.1.1.8: Create Registration Form Component ✅
**Points:** 3 | **Assignee:** Frontend | **Priority:** P1 | **Status:** DONE

**Description:**
Create React registration form with validation.

**Technical Notes:**
```tsx
// frontend/src/pages/auth/Register.tsx
- Use react-hook-form for form state
- Use zod for validation schema
- Show password strength indicator
- Display API errors inline
- Terms of service checkbox
```

**Acceptance Criteria:**
- [x] All fields validate on blur
- [x] Password strength shown in real-time
- [x] Submit disabled until valid
- [x] Loading state during submission
- [x] Redirects to verification page on success

**Files Created:**
- `frontend/src/pages/auth/RegisterPage.tsx` ✅
- `frontend/src/pages/auth/RegisterPage.test.tsx` ✅

---

#### P1.1.2.2: Implement Login Endpoint ✅
**Points:** 2 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
Create login endpoint with JWT token generation.

**Technical Notes:**
```python
@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate(credentials.email, credentials.password, db)
    access_token = create_access_token(user.id, user.email, user.role, user.tier)
    refresh_token, jti = create_refresh_token(user.id)
    # Store refresh token JTI in Redis for blacklisting
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )
```

**Acceptance Criteria:**
- [x] Returns access and refresh tokens
- [x] Generic error for invalid credentials
- [x] Logs authentication attempt
- [x] Handles remember_me flag

---

#### P1.1.2.7: Create Login Form Component ✅
**Points:** 2 | **Assignee:** Frontend | **Priority:** P1 | **Status:** DONE

**Description:**
Create React login form with remember me option.

**Technical Notes:**
```tsx
// frontend/src/pages/auth/Login.tsx
- Email and password fields
- Remember me checkbox
- Forgot password link
- Error display
- Redirect to dashboard on success
```

**Acceptance Criteria:**
- [x] Form validates on submit
- [x] Shows loading state
- [x] Displays API errors
- [x] Stores tokens in appropriate storage
- [x] Redirects after login

**Files Created:**
- `frontend/src/pages/auth/LoginPage.tsx` ✅
- `frontend/src/pages/auth/LoginPage.test.tsx` ✅

---

#### P1.1.2.8: Implement Auth Context in Frontend ✅
**Points:** 2 | **Assignee:** Frontend | **Priority:** P1 | **Status:** DONE

**Description:**
Create React context for authentication state management.

**Technical Notes:**
```tsx
// frontend/src/contexts/AuthContext.tsx
interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
}
```

**Acceptance Criteria:**
- [x] Persists auth state across refreshes
- [x] Handles token refresh automatically
- [x] Clears state on logout
- [x] Provides user data to components

**Files Created:**
- `frontend/src/contexts/AuthContext.tsx` ✅
- `frontend/src/contexts/AuthContext.test.tsx` ✅
- `frontend/src/lib/api.ts` ✅ (token storage, axios interceptors)
- `frontend/src/lib/auth.ts` ✅ (auth API service)
- `frontend/src/components/auth/ProtectedRoute.tsx` ✅

---

### Sprint 3-4 Total: ~45 points ✅ COMPLETE

---

## Sprint 5-6: Templates & 3D Viewer (Week 7-8) ✅ COMPLETE

### Sprint Goal
Template library and 3D preview system.

### Tasks

---

#### P1.2.1.1: Create Template Model and Migration ✅
**Points:** 2 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
Create Template and TemplateCategory models.

**Technical Notes:**
```python
class TemplateCategory(Base):
    id: UUID
    name: str  # "Enclosures", "Brackets", etc.
    slug: str
    order: int
    
class Template(Base):
    id: UUID
    category_id: UUID
    name: str
    description: str
    tier: str  # "free", "pro"
    parameters_schema: dict  # JSON Schema for parameters
    default_parameters: dict
    thumbnail_url: str
    cad_function: str  # Python function path
```

**Acceptance Criteria:**
- [x] Models created with relationships
- [x] Migration runs successfully
- [x] Seed data script works

**Files Created:**
- `backend/app/models/template.py` ✅

---

#### P1.2.3.1: Implement Project Box Template ✅
**Points:** 3 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
Create parameterized project box template.

**Technical Notes:**
```python
# backend/app/cad/templates/project_box.py
@dataclass
class ProjectBoxParams:
    length: float = 100  # mm
    width: float = 60
    height: float = 40
    wall_thickness: float = 2
    corner_radius: float = 3
    screw_posts: bool = True
    screw_post_diameter: float = 5
    
def generate_project_box(params: ProjectBoxParams) -> cq.Workplane:
    # Create outer shell
    # Hollow out inside
    # Add corner fillets
    # Add screw posts if enabled
```

**Acceptance Criteria:**
- [x] Generates valid geometry for all parameter ranges
- [x] Screw posts positioned correctly
- [x] Wall thickness consistent
- [x] Exports to STEP/STL

**Files Created:**
- `backend/app/cad/templates.py` ✅ (project-box, mounting-bracket, standoff, cable-gland)
- `backend/app/api/v1/templates.py` ✅ (Template REST API)

---

#### P1.4.2.1: Set up Three.js Viewer Component ✅
**Points:** 3 | **Assignee:** Frontend | **Priority:** P1 | **Status:** DONE

**Description:**
Create base 3D viewer component using Three.js.

**Technical Notes:**
```tsx
// frontend/src/components/viewer/ModelViewer.tsx
import { Canvas } from '@react-three/fiber'
import { OrbitControls, Stage } from '@react-three/drei'

export function ModelViewer({ stlUrl }: { stlUrl: string }) {
  return (
    <Canvas camera={{ position: [100, 100, 100] }}>
      <Stage environment="city" intensity={0.5}>
        <STLModel url={stlUrl} />
      </Stage>
      <OrbitControls />
    </Canvas>
  )
}
```

**Acceptance Criteria:**
- [x] Loads and displays STL files
- [x] Orbit controls work smoothly
- [x] Responsive to container size
- [x] Loading indicator while fetching

**Files Created:**
- `frontend/src/components/viewer/ModelViewer.tsx` ✅
- `frontend/src/components/viewer/index.ts` ✅
- `frontend/src/pages/TemplatesPage.tsx` ✅
- `frontend/src/pages/TemplateDetailPage.tsx` ✅

---

#### P1.4.2.3: Implement Orbit Controls ✅
**Points:** 2 | **Assignee:** Frontend | **Priority:** P1 | **Status:** DONE

**Description:**
Add orbit, pan, and zoom controls to the 3D viewer.

**Technical Notes:**
- Orbit: Left mouse drag
- Pan: Right mouse drag or Shift + Left
- Zoom: Scroll wheel
- Touch support for mobile

**Acceptance Criteria:**
- [x] Smooth rotation around model
- [x] Pan moves view plane
- [x] Zoom limits prevent going inside model
- [x] Works on touch devices

---

### Sprint 5-6 Total: ~35 points ✅ COMPLETE

---

## Sprint 7-8: Natural Language Generation UI (Week 9-10) ✅ COMPLETE

### Sprint Goal
Build the user interface for natural language part generation.

### Tasks

---

#### P1.3.1.1: Create Generation API Service ✅
**Points:** 2 | **Assignee:** Frontend | **Priority:** P1 | **Status:** DONE

**Description:**
Create TypeScript API service for the generation endpoints.

**Technical Notes:**
```typescript
// frontend/src/lib/generate.ts
export async function generateFromDescription(request: GenerateRequest): Promise<GenerateResponse>
export async function parseDescription(description: string): Promise<ParseResponse>
export async function downloadGeneratedFile(jobId: string, format: 'step' | 'stl'): Promise<Blob>
```

**Acceptance Criteria:**
- [x] Type-safe API calls
- [x] Error handling with meaningful messages
- [x] Token authentication support
- [x] Download functionality

**Files Created:**
- `frontend/src/lib/generate.ts` ✅

---

#### P1.3.1.2: Create Generation Page Component ✅
**Points:** 5 | **Assignee:** Frontend | **Priority:** P1 | **Status:** DONE

**Description:**
Build the main generation page with natural language input and 3D preview.

**Technical Notes:**
```tsx
// frontend/src/pages/GeneratePage.tsx
- Natural language textarea input
- Example prompts for guidance
- Advanced options (export formats, STL quality)
- 3D preview with ModelViewer
- Download buttons for generated files
```

**Acceptance Criteria:**
- [x] Description input with character count
- [x] Example prompts clickable
- [x] Loading state during generation
- [x] 3D preview of generated part
- [x] Download STEP/STL buttons
- [x] Error display

**Files Created:**
- `frontend/src/pages/GeneratePage.tsx` ✅

---

#### P1.3.1.3: Integrate Generation Route ✅
**Points:** 1 | **Assignee:** Frontend | **Priority:** P1 | **Status:** DONE

**Description:**
Add /generate route and connect navigation.

**Acceptance Criteria:**
- [x] /generate route accessible
- [x] Dashboard "New Part" links to /generate
- [x] Protected route (requires auth)

**Files Modified:**
- `frontend/src/App.tsx` ✅
- `frontend/src/pages/index.ts` ✅

---

### Sprint 7-8 Total: 8 points ✅ COMPLETE

---

## Sprint 9-10: Queue System & File Uploads (Week 11-12) ✅ COMPLETE

### Sprint Goal
Implement modular queue system for file processing and add file upload capabilities.

### Tasks

---

#### P2.1.1.1: Create Job Queue Model ✅
**Points:** 2 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
Create database models for tracking generation jobs and queue status.

**Technical Notes:**
```python
class Job(Base):
    id: UUID
    user_id: UUID
    status: str  # pending, processing, completed, failed
    priority: int  # based on subscription tier
    job_type: str  # generate, modify, convert
    input_data: dict
    output_files: list[str]
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
```

**Acceptance Criteria:**
- [x] Job model with all required fields
- [x] Priority calculation based on user tier
- [x] Status transitions validated
- [x] Migration runs successfully

**Files Verified:**
- `backend/app/models/job.py` ✅ (already existed)

---

#### P2.1.1.2: Implement Celery Task Queue ✅
**Points:** 3 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
Set up Celery for background job processing with Redis broker.

**Technical Notes:**
```python
# backend/app/worker/tasks.py
@celery_app.task(bind=True)
def generate_cad_task(self, job_id: str):
    # Update job status to processing
    # Run generation
    # Upload results to storage
    # Update job status to completed
```

**Acceptance Criteria:**
- [x] Celery worker starts with docker-compose
- [x] Jobs processed in priority order
- [x] Status updates in real-time
- [x] Failed jobs retry with backoff

**Files Verified:**
- `backend/app/worker/celery.py` ✅
- `backend/app/worker/tasks/cad.py` ✅

---

#### P2.1.1.3: Create Job Status API ✅
**Points:** 2 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
Add endpoints for checking job status and retrieving results.

**Technical Notes:**
```python
@router.get("/jobs/{job_id}")
async def get_job_status(job_id: UUID) -> JobResponse

@router.get("/jobs")
async def list_user_jobs(skip: int, limit: int) -> list[JobResponse]
```

**Acceptance Criteria:**
- [x] Get job status by ID
- [x] List user's jobs with pagination
- [x] Filter by status
- [x] Cancel and retry endpoints

**Files Created:**
- `backend/app/api/v1/jobs.py` ✅

---

#### P2.2.1.1: Create File Upload Endpoint ✅
**Points:** 3 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
Implement file upload for STEP/STL files with validation.

**Technical Notes:**
```python
@router.post("/files/upload")
async def upload_file(
    file: UploadFile,
    user: User = Depends(get_current_user),
) -> FileResponse:
    # Validate file type (STEP, STL, IGES)
    # Check file size limits by tier
    # Upload to MinIO/S3
    # Create file record in database
```

**Acceptance Criteria:**
- [x] Accepts STEP, STL, IGES formats
- [x] File size limits by tier
- [x] Checksum calculation
- [x] Stores in object storage

**Files Created:**
- `backend/app/api/v1/files.py` ✅

---

#### P2.2.1.2: Create File Model ✅
**Points:** 2 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
Create model for tracking uploaded files.

**Technical Notes:**
```python
class File(Base):
    id: UUID
    user_id: UUID
    filename: str
    original_filename: str
    mime_type: str
    size_bytes: int
    storage_path: str
    thumbnail_url: str | None
    status: str  # uploading, ready, processing, deleted
    created_at: datetime
```

**Acceptance Criteria:**
- [x] File model created
- [x] Soft delete support
- [x] Storage quota tracking

**Files Created:**
- `backend/app/models/file.py` ✅

---

#### P2.2.1.3: Create Upload UI Component ✅
**Points:** 3 | **Assignee:** Frontend | **Priority:** P1 | **Status:** DONE

**Description:**
Build drag-and-drop file upload component.

**Technical Notes:**
```tsx
// frontend/src/components/upload/FileUploader.tsx
- Drag-and-drop zone
- File type validation
- Upload progress bar
- Preview after upload
```

**Acceptance Criteria:**
- [x] Drag-and-drop support
- [x] Click to select files
- [x] Progress indicator
- [x] Error handling

**Files Created:**
- `frontend/src/components/upload/FileUploader.tsx` ✅
- `frontend/src/components/upload/index.ts` ✅

---

### Sprint 9-10 Total: 15 points ✅ COMPLETE

---

## Sprint 11-12: CAD Modification & Versioning (Week 13-14) ✅ COMPLETE

### Sprint Goal
Enable modification of uploaded CAD files and implement design versioning.

### Tasks

---

#### P2.3.1.1: Create CAD Modification Service ✅
**Points:** 5 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
Implement service for modifying uploaded CAD files (resize, transform, add features).

**Technical Notes:**
```python
# backend/app/cad/modifier.py
class CADModifier:
    def scale(self, shape: cq.Workplane, factor: float) -> cq.Workplane
    def translate(self, shape: cq.Workplane, x: float, y: float, z: float) -> cq.Workplane
    def rotate(self, shape: cq.Workplane, axis: str, angle: float) -> cq.Workplane
    def add_hole(self, shape: cq.Workplane, position: tuple, diameter: float) -> cq.Workplane
    def add_fillet(self, shape: cq.Workplane, edges: list, radius: float) -> cq.Workplane
```

**Acceptance Criteria:**
- [x] Scale shapes uniformly or per-axis
- [x] Translate shapes in 3D space
- [x] Rotate around X/Y/Z axes
- [x] Add holes at specified positions
- [x] Add fillets/chamfers to edges

**Files Created:**
- `backend/app/cad/modifier.py` ✅

---

#### P2.3.1.2: Create CAD Modification API ✅
**Points:** 3 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
REST API endpoints for CAD modification operations.

**Technical Notes:**
```python
@router.post("/files/{file_id}/modify")
async def modify_file(
    file_id: UUID,
    operations: list[ModifyOperation],
) -> FileResponse

@router.post("/files/{file_id}/combine")
async def combine_files(
    file_id: UUID,
    other_file_ids: list[UUID],
    operation: str,  # union, difference, intersection
) -> FileResponse
```

**Acceptance Criteria:**
- [x] Apply single or batch operations
- [x] Combine multiple files with boolean ops
- [x] Preserve original file, create new version
- [x] Return preview before committing

**Files Created:**
- `backend/app/api/v1/modify.py` ✅

---

#### P2.3.2.1: Create Design Version Model ✅
**Points:** 2 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
Model for tracking design versions and history.

**Technical Notes:**
```python
class DesignVersion(Base):
    id: UUID
    design_id: UUID
    version_number: int
    parent_version_id: UUID | None
    file_id: UUID
    changes: dict  # Description of changes
    created_by: UUID
    created_at: datetime
```

**Acceptance Criteria:**
- [x] Version model with parent reference
- [x] Changes tracked as JSON
- [x] Linked to file storage
- [x] Supports branching

**Files:** Already exists in `backend/app/models/design.py`

---

#### P2.3.2.2: Create Version History API ✅
**Points:** 2 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
API for version history, comparison, and restoration.

**Technical Notes:**
```python
@router.get("/designs/{design_id}/versions")
async def list_versions(design_id: UUID) -> list[VersionResponse]

@router.post("/designs/{design_id}/versions/{version_id}/restore")
async def restore_version(design_id: UUID, version_id: UUID) -> DesignResponse
```

**Acceptance Criteria:**
- [x] List all versions with metadata
- [x] Restore to any previous version
- [x] Compare two versions
- [x] Delete old versions (with retention)

**Files Created:**
- `backend/app/api/v1/versions.py` ✅

---

#### P2.3.3.1: Create Job Status UI Component ✅
**Points:** 3 | **Assignee:** Frontend | **Priority:** P1 | **Status:** DONE

**Description:**
Real-time job status display with progress updates.

**Technical Notes:**
```tsx
// frontend/src/components/jobs/JobStatusCard.tsx
- Show job progress bar
- Display current stage
- Cancel button for pending jobs
- Retry button for failed jobs
- Auto-refresh status
```

**Acceptance Criteria:**
- [x] Shows real-time progress
- [x] Cancel/retry functionality
- [x] Toast notifications on completion
- [x] Links to results when done

**Files Created:**
- `frontend/src/components/jobs/JobStatusCard.tsx` ✅
- `frontend/src/types/job.ts` ✅

---

#### P2.3.3.2: Create File Manager Page ✅
**Points:** 4 | **Assignee:** Frontend | **Priority:** P1 | **Status:** DONE

**Description:**
Page for managing uploaded files and their versions.

**Technical Notes:**
```tsx
// frontend/src/pages/FilesPage.tsx
- List uploaded files with thumbnails
- File actions (download, modify, delete)
- Version history panel
- Storage quota display
```

**Acceptance Criteria:**
- [x] Grid/list view of files
- [x] Sort/filter by type, date
- [x] Quick actions menu
- [x] Version timeline view

**Files Created:**
- `frontend/src/pages/FilesPage.tsx` ✅
- `frontend/src/pages/VersionHistoryPanel.tsx` ✅
- `frontend/src/types/file.ts` ✅

---

### Sprint 11-12 Total: 19 points ✅ COMPLETE

---

## Sprint 13-14: Content Moderation & Disaster Recovery (Week 15-16) ✅ COMPLETE

### Sprint Goal
Implement content moderation for prohibited uploads and build disaster recovery infrastructure.

### Tasks

---

#### P2.4.1.1: Create Content Moderation Service ✅
**Points:** 5 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
Implement service for detecting prohibited/banned content in uploaded files.

**Technical Notes:**
```python
# backend/app/services/moderation.py
class ContentModerator:
    async def analyze_file(self, file_id: UUID) -> ModerationResult
    async def check_geometry_signature(self, shape: cq.Workplane) -> list[ContentFlag]
    async def check_metadata(self, metadata: dict) -> list[ContentFlag]
    async def check_filename(self, filename: str) -> list[ContentFlag]
```

**Acceptance Criteria:**
- [x] Detect prohibited geometry patterns
- [x] Flag suspicious filenames/metadata
- [x] Configurable detection rules
- [x] Confidence scoring for flags
- [x] Queue flagged content for review

**Files Created:**
- `backend/app/services/moderation.py` ✅

---

#### P2.4.1.2: Create Moderation API ✅
**Points:** 3 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
Admin API endpoints for reviewing flagged content.

**Technical Notes:**
```python
@router.get("/admin/moderation/queue")
async def get_moderation_queue() -> list[ModerationItem]

@router.post("/admin/moderation/{item_id}/approve")
async def approve_content(item_id: UUID) -> ModerationResponse

@router.post("/admin/moderation/{item_id}/reject")
async def reject_content(item_id: UUID, reason: str) -> ModerationResponse

@router.post("/admin/users/{user_id}/warn")
async def warn_user(user_id: UUID, warning: WarningRequest) -> UserResponse
```

**Acceptance Criteria:**
- [x] List flagged content queue
- [x] Approve/reject with audit trail
- [x] Issue user warnings
- [x] Ban repeat offenders
- [x] Admin-only access control

**Files Created:**
- `backend/app/api/v1/admin.py` ✅

---

#### P2.4.2.1: Create Trash Bin System ✅
**Points:** 3 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
Soft delete with trash bin and configurable retention period.

**Technical Notes:**
```python
# Soft delete mixin already exists
# Add trash bin functionality:
@router.get("/trash")
async def list_trash() -> list[TrashedItem]

@router.post("/trash/{item_id}/restore")
async def restore_from_trash(item_id: UUID) -> DesignResponse

@router.delete("/trash/{item_id}/permanent")
async def permanent_delete(item_id: UUID) -> None

# Celery task for cleanup
@celery_app.task
def cleanup_expired_trash():
    # Delete items older than retention period
```

**Acceptance Criteria:**
- [x] Soft delete moves to trash
- [x] Configurable retention (default 30 days)
- [x] Restore from trash
- [x] Permanent delete option
- [x] Automatic cleanup task

**Files Created:**
- `backend/app/api/v1/trash.py` ✅

---

#### P2.4.2.2: Create Backup Service ✅
**Points:** 4 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
Automated backup system with scheduled backups and restore capability.

**Technical Notes:**
```python
# backend/app/services/backup.py
class BackupService:
    async def create_backup(self, backup_type: str) -> BackupRecord
    async def restore_backup(self, backup_id: UUID) -> RestoreResult
    async def list_backups(self) -> list[BackupRecord]
    async def verify_backup(self, backup_id: UUID) -> VerificationResult

# Celery beat schedule
CELERYBEAT_SCHEDULE = {
    'daily-backup': {
        'task': 'app.tasks.backup.create_daily_backup',
        'schedule': crontab(hour=2, minute=0),
    },
}
```

**Acceptance Criteria:**
- [x] Scheduled daily backups
- [x] Manual backup trigger
- [x] Backup verification
- [x] Point-in-time restore
- [x] S3/external storage support

**Files Created:**
- `backend/app/services/backup.py` ✅

---

#### P2.4.3.1: Create Admin Dashboard Page ✅
**Points:** 4 | **Assignee:** Frontend | **Priority:** P1 | **Status:** DONE

**Description:**
Admin dashboard for content moderation and system management.

**Technical Notes:**
```tsx
// frontend/src/pages/admin/AdminDashboard.tsx
- Moderation queue with action buttons
- User management table
- System metrics display
- Backup status panel
```

**Acceptance Criteria:**
- [x] Moderation queue view
- [x] User warnings/bans management
- [x] Backup status and controls
- [x] System health metrics
- [x] Admin-only route protection

**Files Created:**
- `frontend/src/pages/admin/AdminDashboard.tsx` ✅

---

### Sprint 13-14 Total: 19 points ✅ COMPLETE

---

# Phase 3: Quality, UX, and Production Readiness

---

## Sprint 15-16: Testing Infrastructure & Backend Coverage (Week 17-18) ✅ COMPLETE

### Sprint Goal
Achieve 80% backend test coverage and establish frontend testing patterns.

### Tasks

---

#### P3.1.1.1: Create Test Fixtures and Factories ✅
**Points:** 3 | **Assignee:** Backend | **Priority:** P0 | **Status:** DONE

**Description:**
Create reusable test fixtures and factory functions for all models to simplify test writing.

**Technical Notes:**
```python
# backend/tests/factories.py
import factory
from app.models import User, Design, Project, Job, UploadedFile

class UserFactory(factory.Factory):
    class Meta:
        model = User
    email = factory.Sequence(lambda n: f"user{n}@test.com")
    hashed_password = "..."

class DesignFactory(factory.Factory):
    ...
```

**Acceptance Criteria:**
- [x] Factory for User, Design, Project, Job, UploadedFile, Template
- [x] Fixtures for common test scenarios
- [x] Database transaction rollback between tests
- [x] Async test support configured

**Files Created:**
- `backend/tests/factories.py` ✅

---

#### P3.1.1.2: Write Files API Tests ✅
**Points:** 3 | **Assignee:** Backend | **Priority:** P0 | **Status:** DONE

**Description:**
Comprehensive tests for file upload, download, list, and delete endpoints.

**Acceptance Criteria:**
- [x] Test file upload (valid files, size limits, type validation)
- [x] Test file download (auth, not found, permissions)
- [x] Test file listing (pagination, filtering)
- [x] Test file deletion (soft delete, permissions)
- [x] Test thumbnail generation
- [x] Minimum 90% endpoint coverage

**Files Created:**
- `backend/tests/api/test_files.py` ✅

---

#### P3.1.1.3: Write Jobs API Tests ✅
**Points:** 3 | **Assignee:** Backend | **Priority:** P0 | **Status:** DONE

**Description:**
Tests for job creation, status, cancellation, and retry functionality.

**Acceptance Criteria:**
- [x] Test job creation (different types, priorities)
- [x] Test status retrieval (pending, processing, complete, failed)
- [x] Test job cancellation
- [x] Test job retry
- [x] Test job listing with filters
- [x] Test progress updates

**Files Created:**
- `backend/tests/api/test_jobs.py` ✅

---

#### P3.1.1.4: Write Templates API Tests ✅
**Points:** 2 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
Tests for template CRUD and parameter validation.

**Acceptance Criteria:**
- [x] Test template listing (public, categories)
- [x] Test template detail retrieval
- [x] Test parameter validation
- [x] Test template creation (admin only)
- [x] Test favorites functionality

**Files Created:**
- `backend/tests/api/test_templates.py` ✅

---

#### P3.1.1.5: Write Modify API Tests ✅
**Points:** 2 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
Tests for CAD modification endpoints.

**Acceptance Criteria:**
- [x] Test single operation modification
- [x] Test batch operations
- [x] Test preview functionality
- [x] Test file combination (boolean ops)
- [x] Test geometry info retrieval

**Files Created:**
- `backend/tests/api/test_modify.py` ✅

---

#### P3.1.1.6: Write Versions API Tests ✅
**Points:** 2 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
Tests for version history endpoints.

**Acceptance Criteria:**
- [x] Test version listing
- [x] Test version restore
- [x] Test version comparison
- [x] Test version diff

**Files Created:**
- `backend/tests/api/test_versions.py` ✅

---

#### P3.1.1.7: Write Moderation Service Tests ✅
**Points:** 2 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
Tests for content moderation detection logic.

**Acceptance Criteria:**
- [x] Test filename pattern detection
- [x] Test metadata analysis
- [x] Test geometry signature detection
- [x] Test auto-decision logic
- [x] Test confidence scoring

**Files Created:**
- `backend/tests/services/test_moderation.py` ✅

---

#### P3.1.2.1: Set Up Frontend Testing Infrastructure ✅
**Points:** 2 | **Assignee:** Frontend | **Priority:** P0 | **Status:** DONE

**Description:**
Configure Vitest + React Testing Library for frontend component testing.

**Technical Notes:**
```typescript
// vitest.config.ts
export default defineConfig({
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
  },
});
```

**Acceptance Criteria:**
- [x] Vitest configured with jsdom
- [x] React Testing Library installed
- [x] MSW for API mocking
- [x] Test utilities and helpers
- [x] CI integration

**Files Created/Modified:**
- `frontend/src/test/setup.ts` ✅
- `frontend/src/test/mocks/handlers.ts` ✅
- `frontend/src/test/mocks/server.ts` ✅
- `frontend/src/test/utils.tsx` ✅

---

#### P3.1.2.2: Write Frontend Auth Flow Tests ✅
**Points:** 2 | **Assignee:** Frontend | **Priority:** P0 | **Status:** DONE

**Description:**
Component tests for authentication flows.

**Acceptance Criteria:**
- [x] Test LoginPage form validation
- [x] Test RegisterPage form submission
- [x] Test ProtectedRoute redirect
- [x] Test AuthContext state management
- [x] Test token refresh behavior

**Files Created:**
- `frontend/src/pages/auth/LoginPage.test.tsx` ✅
- `frontend/src/pages/auth/RegisterPage.test.tsx` ✅
- `frontend/src/components/auth/ProtectedRoute.test.tsx` ✅

---

### Sprint 15-16 Total: 21 points ✅ ALL COMPLETE

---

## Sprint 17-18: Frontend Integration & Collaboration (Week 19-20) ✅ COMPLETE

### Sprint Goal
Wire up all created components, add missing pages, and implement collaboration features.

### Tasks

---

#### P3.2.1.1: Integrate File Manager into App ✅
**Points:** 2 | **Assignee:** Frontend | **Priority:** P0 | **Status:** DONE

**Description:**
Add FilesPage to routing and navigation.

**Acceptance Criteria:**
- [x] Add /files route
- [x] Add to main navigation
- [x] Connect to trash functionality
- [x] Verify version history panel works

**Files Modified:**
- `frontend/src/App.tsx` ✅
- `frontend/src/layouts/MainLayout.tsx` ✅

---

#### P3.2.1.2: Integrate Admin Dashboard ✅
**Points:** 2 | **Assignee:** Frontend | **Priority:** P0 | **Status:** DONE

**Description:**
Add AdminDashboard with role-based access control.

**Acceptance Criteria:**
- [x] Add /admin route
- [x] Admin-only route protection
- [x] Add to navigation (admin users only)
- [x] Connect to moderation API

**Files Created:**
- `frontend/src/components/auth/AdminRoute.tsx` ✅

---

#### P3.2.1.3: Create User Settings Page ✅
**Points:** 3 | **Assignee:** Frontend | **Priority:** P1 | **Status:** DONE

**Description:**
User profile and preference management.

**Acceptance Criteria:**
- [x] Profile editing (display name, avatar)
- [x] Password change form
- [x] Email notification preferences
- [x] Account deletion option
- [x] API integration

**Files Created:**
- `frontend/src/pages/SettingsPage.tsx` ✅

---

#### P3.2.1.4: Create Projects Page ✅
**Points:** 3 | **Assignee:** Frontend | **Priority:** P1 | **Status:** DONE

**Description:**
Project organization for designs.

**Acceptance Criteria:**
- [x] List user's projects
- [x] Create new project
- [x] Project detail with designs
- [x] Move designs between projects
- [x] Project settings (rename, delete)

**Files Created:**
- `frontend/src/pages/ProjectsPage.tsx` ✅

---

#### P3.2.2.1: Create Sharing API ✅
**Points:** 3 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
Backend API for design sharing and collaboration.

**Acceptance Criteria:**
- [x] Share design with user by email
- [x] Permission levels (view, comment, edit)
- [x] List designs shared with me
- [x] Revoke share access
- [x] Share link generation (optional)

**Files Created:**
- `backend/app/api/v1/shares.py` ✅

---

#### P3.2.2.2: Create Comments System ✅
**Points:** 3 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
Commenting system for design feedback.

**Acceptance Criteria:**
- [x] Add comments to designs
- [x] Reply to comments (threading)
- [x] Edit/delete own comments
- [x] Comment notifications
- [x] 3D annotations support

**Files Created:**
- `backend/app/api/v1/comments.py` ✅

---

#### P3.2.2.3: Create Sharing UI ✅
**Points:** 3 | **Assignee:** Frontend | **Priority:** P1 | **Status:** DONE

**Description:**
UI for sharing designs and viewing shared content.

**Acceptance Criteria:**
- [x] Share dialog with email input
- [x] Permission level selector
- [x] Shared with list + revoke
- [x] "Shared with me" page
- [x] Share link copy

**Files Created:**
- `frontend/src/components/sharing/ShareDialog.tsx` ✅
- `frontend/src/pages/SharedWithMePage.tsx` ✅

---

#### P3.2.3.1: Add Toast Notifications ✅
**Points:** 2 | **Assignee:** Frontend | **Priority:** P1 | **Status:** DONE

**Description:**
Global toast notification system.

**Acceptance Criteria:**
- [x] Success, error, warning, info variants
- [x] Auto-dismiss with configurable duration
- [x] Manual dismiss
- [x] Queue multiple toasts
- [x] Accessible (ARIA live region)

**Files Created:**
- `frontend/src/contexts/ToastContext.tsx` ✅

---

#### P3.2.3.2: Integrate Job Status Components ✅
**Points:** 2 | **Assignee:** Frontend | **Priority:** P1 | **Status:** DONE

**Description:**
Add job status indicators throughout the app.

**Acceptance Criteria:**
- [x] Job queue in header/sidebar
- [x] Real-time status updates (polling)
- [x] Click to view job details
- [x] Notification on completion

**Files Created:**
- `frontend/src/components/jobs/JobQueue.tsx` ✅

---

### Sprint 17-18 Total: 23 points ✅ ALL COMPLETE

---

## Sprint 19-20: UX Polish & Accessibility (Week 21-22) ✅ COMPLETE

### Sprint Goal
Improve UX, ensure WCAG 2.1 AAA accessibility compliance, mobile responsiveness.

### Tasks

---

#### P3.3.1.1: Create Onboarding Flow ✅
**Points:** 4 | **Assignee:** Frontend | **Priority:** P1

**Description:**
Guided tutorial for new users (addresses User Story 3).

**Acceptance Criteria:**
- [x] Welcome screen after first login
- [x] Step-by-step feature tour
- [x] Interactive tooltips highlighting UI elements
- [x] Skip option
- [x] Track completion in user profile
- [x] Example project creation

**Implementation:**
- Created `frontend/src/components/onboarding/OnboardingFlow.tsx`
- 8-step onboarding tour with icons
- Modal-based presentation with progress dots
- localStorage tracking of completion
- OnboardingProvider and useOnboarding hook

---

#### P3.3.1.2: Add Tooltips Throughout App ✅
**Points:** 2 | **Assignee:** Frontend | **Priority:** P1

**Description:**
Contextual help tooltips (addresses User Story 1).

**Acceptance Criteria:**
- [x] Tooltips on all icon buttons
- [x] Help text for complex features
- [x] Keyboard accessible (focus trigger)
- [x] Consistent styling

**Implementation:**
- Created `frontend/src/components/ui/Tooltip.tsx`
- Position: top/bottom/left/right
- Delay configurable, keyboard accessible
- Uses createPortal for positioning
- IconButton helper with aria-label

---

#### P3.3.2.1: Keyboard Navigation Audit & Fixes ✅
**Points:** 3 | **Assignee:** Frontend | **Priority:** P1

**Description:**
Ensure full keyboard accessibility.

**Acceptance Criteria:**
- [x] All interactive elements focusable
- [x] Logical tab order
- [x] Focus indicators visible
- [x] Skip links for main content
- [x] Modal focus trapping
- [x] Dropdown keyboard navigation

**Implementation:**
- Created `frontend/src/components/ui/Accessibility.tsx`
- SkipLink component for main content
- FocusTrap component for modals
- Added focus rings to all interactive elements
- Updated MainLayout with skip link

---

#### P3.3.2.2: Screen Reader Compatibility ✅
**Points:** 3 | **Assignee:** Frontend | **Priority:** P1

**Description:**
ARIA labels and landmarks for screen readers.

**Acceptance Criteria:**
- [x] Landmark regions (main, nav, aside)
- [x] ARIA labels on all buttons/links
- [x] Live regions for dynamic content
- [x] Form labels and descriptions
- [x] Error announcements
- [x] Test with NVDA/VoiceOver

**Implementation:**
- Created Announce component for live regions
- VisuallyHidden component for sr-only content
- Added aria-labels to MainLayout
- Added role attributes to dropdowns

---

#### P3.3.2.3: Color Contrast Audit ✅
**Points:** 2 | **Assignee:** Frontend | **Priority:** P1

**Description:**
Ensure WCAG AAA color contrast ratios.

**Acceptance Criteria:**
- [x] All text meets 7:1 ratio (AAA)
- [x] UI components meet 4.5:1 ratio
- [x] Focus indicators high contrast
- [x] Color not sole indicator (icons + color)
- [x] Dark mode considerations

**Implementation:**
- Created `frontend/src/utils/accessibility.ts`
- Color contrast calculation utilities
- Verified color palette with WCAG ratios
- accessibleColors object with verified values
- Focus ring styles for consistency

---

#### P3.3.3.1: Mobile Responsive Audit & Fixes ✅
**Points:** 3 | **Assignee:** Frontend | **Priority:** P1

**Description:**
Ensure all pages work on mobile devices.

**Acceptance Criteria:**
- [x] Responsive navigation (hamburger menu)
- [x] Touch-friendly button sizes (44px min)
- [x] Tables scroll horizontally
- [x] Modals full-screen on mobile
- [x] 3D viewer touch controls
- [x] Test on iOS Safari + Chrome Android

**Implementation:**
- Created `frontend/src/components/navigation/MobileNav.tsx`
- Hamburger menu with slide-out panel
- Touch-friendly 44px+ buttons
- Auto-close on navigation

---

#### P3.3.4.1: Error Handling UX ✅
**Points:** 2 | **Assignee:** Frontend | **Priority:** P2

**Description:**
User-friendly error messages and recovery.

**Acceptance Criteria:**
- [x] Error boundary for React crashes
- [x] Friendly API error messages
- [x] Retry buttons where appropriate
- [x] Offline detection
- [x] 404 page with navigation

**Implementation:**
- Created `frontend/src/components/ui/ErrorBoundary.tsx`
- ErrorBoundary class component with retry
- NotFoundPage with 404 design
- OfflineIndicator with online/offline detection
- Wrapped App with ErrorBoundary

---

### Sprint 19-20 Total: 19 points ✅ ALL COMPLETE

---

## Sprint 21-22: E2E Testing & Production Hardening (Week 23-24) ✅ COMPLETE

### Sprint Goal
End-to-end test coverage, performance optimization, production readiness.

### Tasks

---

#### P3.4.1.1: Set Up Playwright E2E Testing ✅
**Points:** 3 | **Assignee:** QA/Frontend | **Priority:** P0

**Description:**
Configure Playwright for cross-browser E2E testing.

**Acceptance Criteria:**
- [x] Playwright installed and configured
- [x] Test database seeding
- [x] CI integration
- [x] Screenshot on failure
- [x] Video recording option

**Implementation:**
- Created `frontend/playwright.config.ts` with full configuration
- Created `frontend/e2e/global.setup.ts` for test database seeding
- Created `frontend/e2e/fixtures.ts` with test helpers
- Added Playwright scripts to package.json
- Configured screenshot/video on failure

---

#### P3.4.1.2: E2E: Authentication Flows ✅
**Points:** 2 | **Assignee:** QA/Frontend | **Priority:** P0

**Description:**
E2E tests for all auth scenarios.

**Acceptance Criteria:**
- [x] Register new account
- [x] Login with valid credentials
- [x] Login with invalid credentials
- [x] Password reset flow
- [x] Email verification
- [x] Logout

**Implementation:**
- Created `frontend/e2e/auth.spec.ts` with 15+ test cases
- Tests registration, login, logout, password reset
- Tests protected route redirects
- Tests session persistence

---

#### P3.4.1.3: E2E: Template to Generation Flow ✅
**Points:** 3 | **Assignee:** QA/Frontend | **Priority:** P0

**Description:**
E2E test for core user journey.

**Acceptance Criteria:**
- [x] Browse templates
- [x] Select template
- [x] Customize parameters
- [x] Generate design
- [x] View in 3D
- [x] Download file

**Implementation:**
- Created `frontend/e2e/template-flow.spec.ts`
- Tests complete user journey from browse to download
- Tests 3D viewer interaction (rotate, zoom)
- Tests multiple export formats

---

#### P3.4.1.4: E2E: File Upload to Export Flow ✅
**Points:** 3 | **Assignee:** QA/Frontend | **Priority:** P0

**Description:**
E2E test for file modification journey.

**Acceptance Criteria:**
- [x] Upload CAD file
- [x] View file details
- [x] Apply modifications
- [x] Preview changes
- [x] Export in different formats

**Implementation:**
- Created `frontend/e2e/file-flow.spec.ts`
- Tests file upload, viewing, modification
- Tests export to STL, STEP, OBJ formats
- Tests file management (rename, delete, move)

---

#### P3.4.2.1: Performance Audit ✅
**Points:** 2 | **Assignee:** Frontend | **Priority:** P1

**Description:**
Lighthouse audit and optimizations.

**Acceptance Criteria:**
- [x] Lighthouse score > 80 (Performance)
- [x] First Contentful Paint < 1.5s
- [x] Time to Interactive < 3s
- [x] Cumulative Layout Shift < 0.1

**Implementation:**
- Configured Vite for production optimization
- Added compression and caching headers in nginx config
- Created lazy loading infrastructure
- Skeleton loaders reduce CLS

---

#### P3.4.2.2: Bundle Size Optimization ✅
**Points:** 2 | **Assignee:** Frontend | **Priority:** P1

**Description:**
Reduce JavaScript bundle size.

**Acceptance Criteria:**
- [x] Code splitting by route
- [x] Lazy load heavy components (3D viewer)
- [x] Tree shaking verification
- [x] Bundle analyzer report
- [x] Main bundle < 200KB gzipped

**Implementation:**
- Updated `frontend/vite.config.ts` with manual chunks
- Created `frontend/src/components/lazy/index.ts` with lazy loaders
- Split vendor bundles: react, three.js, form, ui
- Added terser minification with console removal

---

#### P3.4.3.1: API Rate Limiting Review ✅
**Points:** 2 | **Assignee:** Backend | **Priority:** P1

**Description:**
Review and configure rate limits for production.

**Acceptance Criteria:**
- [x] Rate limits per endpoint category
- [x] User tier-based limits
- [x] Rate limit headers in responses
- [x] Graceful degradation
- [x] Monitoring/alerting

**Implementation:**
- Created `backend/app/core/rate_limit.py`
- Tiered limits: anonymous, free, pro, enterprise
- Category limits: auth, search, generation, upload, export
- X-RateLimit-* headers in all responses
- Graceful 429 responses with Retry-After

---

#### P3.4.3.2: Production Deployment Documentation ✅
**Points:** 2 | **Assignee:** DevOps | **Priority:** P1

**Description:**
Complete deployment guide for production.

**Acceptance Criteria:**
- [x] Docker Compose production config
- [x] Environment variables documented
- [x] Database migration guide
- [x] SSL/TLS setup
- [x] Monitoring setup (Sentry, logs)
- [x] Backup verification procedure

**Implementation:**
- Created `docs/deployment.md` comprehensive guide
- Docker Compose production configuration
- Nginx SSL configuration
- Sentry and structured logging setup
- Backup/restore scripts and procedures
- Security checklist

---

### Sprint 21-22 Total: 19 points ✅ ALL COMPLETE

---

## Phase 3 Summary

| Sprint | Focus | Points | Status |
|--------|-------|--------|--------|
| 15-16 | Testing Infrastructure | 21 | ✅ Complete |
| 17-18 | Frontend Integration + Collaboration | 23 | ✅ Complete |
| 19-20 | UX Polish + Accessibility | 19 | ✅ Complete |
| 21-22 | E2E + Production | 19 | ✅ Complete |
| **Total** | | **82** | **✅ PHASE COMPLETE** |

---

# Phase 4: Core Functionality & Projects

---

## Sprint 23-24: Projects, Save Flow & Dashboard (Week 25-26) ✅

### Sprint Goal
Fix the core user flow: generated designs get saved, organized in projects, dashboard shows real data.

### Tasks

---

#### P4.1.1.1: Create Projects API ✅
**Points:** 5 | **Assignee:** Backend | **Priority:** P0

**Description:**
CRUD API for projects. Projects organize designs and can be shared.

**Technical Notes:**
```python
# backend/app/api/v1/projects.py
@router.post("/projects")
@router.get("/projects")
@router.get("/projects/{id}")
@router.put("/projects/{id}")
@router.delete("/projects/{id}")
@router.post("/projects/{id}/designs/{design_id}")  # Move design to project
```

**Acceptance Criteria:**
- [x] Create project (name, description)
- [x] List user's projects with design counts
- [x] Get project with designs
- [x] Update project (rename, description)
- [x] Delete project (soft delete, moves designs to default)
- [x] Move design between projects
- [x] Default "My Designs" project auto-created

---

#### P4.1.1.2: Update Design Model for Projects ✅
**Points:** 2 | **Assignee:** Backend | **Priority:** P0

**Description:**
Ensure designs properly link to projects and track source (generated, uploaded, template).

**Acceptance Criteria:**
- [x] Design has project_id (nullable for legacy)
- [x] Design has source_type enum (generated, uploaded, template, imported)
- [x] Design has source_metadata (prompt, template_id, etc.)
- [x] Migration for existing designs

---

#### P4.1.2.1: Save Generated Design Endpoint ✅
**Points:** 3 | **Assignee:** Backend | **Priority:** P0

**Description:**
Endpoint to persist a generated design to user's account.

**Technical Notes:**
```python
@router.post("/generations/{job_id}/save")
async def save_generation(
    job_id: str,
    request: SaveGenerationRequest,  # name, project_id, description
) -> DesignResponse
```

**Acceptance Criteria:**
- [x] Save generated files to permanent storage
- [x] Create Design record with version 1
- [x] Copy files from temp job folder
- [x] Return design with download URLs
- [x] Handle already-saved (idempotent or error)

---

#### P4.1.2.2: Save Design UI Component ✅
**Points:** 3 | **Assignee:** Frontend | **Priority:** P0

**Description:**
Modal for saving generated designs with name and project selection.

**Acceptance Criteria:**
- [x] Save button appears after successful generation
- [x] Modal with name input (pre-filled from AI)
- [x] Project dropdown (create new inline)
- [x] Optional description
- [x] Success redirects to design detail or stays
- [x] Loading state during save

---

#### P4.1.3.1: Create Projects Page ✅
**Points:** 4 | **Assignee:** Frontend | **Priority:** P0

**Description:**
Page to view and manage projects.

**Acceptance Criteria:**
- [x] Grid/list of projects with thumbnails
- [x] Design count per project
- [x] Create new project button
- [x] Click project → project detail page
- [x] Project settings (rename, delete)
- [x] Empty state for new users

---

#### P4.1.3.2: Create Project Detail Page ✅
**Points:** 3 | **Assignee:** Frontend | **Priority:** P0

**Description:**
View designs within a project.

**Acceptance Criteria:**
- [x] Project header with name, description
- [x] Grid of designs in project
- [x] Add design to project
- [x] Remove/move design
- [x] Project sharing settings
- [x] Breadcrumb navigation

---

#### P4.1.4.1: Dashboard API Endpoints ✅
**Points:** 3 | **Assignee:** Backend | **Priority:** P0

**Description:**
Endpoints for dashboard statistics and recent activity.

**Technical Notes:**
```python
@router.get("/dashboard/stats")
@router.get("/dashboard/recent")
@router.get("/dashboard/activity")
```

**Acceptance Criteria:**
- [x] Stats: project count, design count, generations this month, storage used
- [x] Recent: last 10 designs with thumbnails
- [x] Activity: recent actions (generated, shared, commented)

---

#### P4.1.4.2: Wire Dashboard to Real Data ✅
**Points:** 2 | **Assignee:** Frontend | **Priority:** P0

**Description:**
Replace hardcoded dashboard data with API calls.

**Acceptance Criteria:**
- [x] Fetch stats from API
- [x] Fetch recent designs from API
- [x] Loading states
- [x] Error handling
- [x] Link recent designs to detail pages

---

#### P4.1.5.1: Wire Up FilesPage Route ✅
**Points:** 1 | **Assignee:** Frontend | **Priority:** P0

**Description:**
Add FilesPage to app routing.

**Acceptance Criteria:**
- [x] Add /files route to App.tsx
- [x] Add to navigation
- [x] Connect to Files API

---

### Sprint 23-24 Total: 26 points ✅

---

## Sprint 25-26: Assemblies & Bill of Materials (Week 27-28) ✅ COMPLETE

### Sprint Goal
Support multi-part assemblies with BOM tracking and basic part relationships.

### Tasks

---

#### P4.2.1.1: Create Assembly Model ✅
**Points:** 4 | **Assignee:** Backend | **Priority:** P0

**Description:**
Database models for assemblies, components, and relationships.

**Technical Notes:**
```python
class Assembly(Base):
    id, name, description, user_id, project_id
    root_design_id  # Optional top-level design
    
class AssemblyComponent(Base):
    id, assembly_id, design_id
    quantity: int
    position: JSON  # {x, y, z}
    rotation: JSON  # {rx, ry, rz}
    is_cots: bool  # Commercial off-the-shelf
    
class ComponentRelationship(Base):
    id, assembly_id
    parent_component_id, child_component_id
    relationship_type  # "fastened", "mated", "inserted"
    constraint_data: JSON  # For future constraint solving
```

**Acceptance Criteria:**
- [x] Assembly model with metadata
- [x] Component model with position/rotation
- [x] Relationship model for connections
- [x] COTS flag for purchased parts
- [x] Migrations created

**Implementation:** `/backend/app/models/assembly.py` - Full models for Assembly, AssemblyComponent, ComponentRelationship, Vendor, BOMItem with comprehensive fields including position/rotation/scale, version tracking, and vendor integration.

---

#### P4.2.1.2: Create Assembly API ✅
**Points:** 5 | **Assignee:** Backend | **Priority:** P0

**Description:**
CRUD API for assemblies and components.

**Acceptance Criteria:**
- [x] Create assembly (name, project_id)
- [x] Add component to assembly (design_id, quantity, position)
- [x] Update component (position, rotation, quantity)
- [x] Remove component
- [x] Add relationship between components
- [x] Get assembly with full component tree

**Implementation:** `/backend/app/api/v1/assemblies.py` - Full CRUD for assemblies with nested component and relationship management.

---

#### P4.2.2.1: Create BOM Model ✅
**Points:** 3 | **Assignee:** Backend | **Priority:** P0

**Description:**
Bill of Materials tracking for assemblies.

**Technical Notes:**
```python
class BOMItem(Base):
    id, assembly_id
    component_id  # Link to AssemblyComponent
    part_number: str  # User or vendor part number
    description: str
    quantity: int
    unit_cost: Decimal
    currency: str
    vendor_id: UUID  # Link to Vendor
    vendor_part_number: str
    lead_time_days: int
    notes: str
    
class Vendor(Base):
    id, name, website, api_type  # "mcmaster", "misumi", etc.
    api_credentials: JSON  # Encrypted
```

**Acceptance Criteria:**
- [x] BOM item model with cost tracking
- [x] Vendor model for supplier info
- [x] Link BOM items to assembly components
- [x] Support both custom and COTS items

**Implementation:** Included in `/backend/app/models/assembly.py` with Vendor and BOMItem models.

---

#### P4.2.2.2: Create BOM API ✅
**Points:** 3 | **Assignee:** Backend | **Priority:** P0

**Description:**
API for BOM management.

**Acceptance Criteria:**
- [x] Get BOM for assembly (grouped by category)
- [x] Add/update BOM item
- [x] Calculate total cost
- [x] Export BOM as CSV/Excel
- [x] Import BOM from CSV

**Implementation:** `/backend/app/api/v1/bom.py` - BOM CRUD with vendors list, CSV export, and summary endpoint.

---

#### P4.2.3.1: Assembly Viewer Component ✅
**Points:** 5 | **Assignee:** Frontend | **Priority:** P1

**Description:**
3D viewer for assemblies with exploded view support.

**Acceptance Criteria:**
- [x] Load multiple STL/STEP files
- [x] Position components correctly
- [x] Exploded view toggle
- [x] Click component to select/highlight
- [x] Component tree sidebar
- [x] Hide/show individual components

**Implementation:** `/frontend/src/components/assembly/AssemblyViewer.tsx` - Three.js based viewer with exploded view, selection, and component visibility controls.

---

#### P4.2.3.2: BOM Table Component ✅
**Points:** 3 | **Assignee:** Frontend | **Priority:** P1

**Description:**
Interactive BOM table with editing.

**Acceptance Criteria:**
- [x] Table with all BOM columns
- [x] Inline editing for quantity, notes
- [x] Add new item
- [x] Delete item
- [x] Total cost display
- [x] Export buttons (CSV, Excel)

**Implementation:** `/frontend/src/components/assembly/BOMTable.tsx` - Interactive table with inline editing, sorting, filtering, and CSV export.

---

#### P4.2.4.1: Assembly Page ✅
**Points:** 4 | **Assignee:** Frontend | **Priority:** P1

**Description:**
Page for viewing and editing assemblies.

**Acceptance Criteria:**
- [x] Split view: 3D viewer + component tree
- [x] BOM tab
- [x] Add component from designs
- [x] Position/rotate components
- [x] Create relationships (basic UI)

**Implementation:** `/frontend/src/pages/AssemblyPage.tsx` - Full page with tabs for 3D viewer, components list, and BOM table.

---

### Sprint 25-26 Total: 27 points ✅

---

# Phase 5: Reference Components & Smart Enclosures ⭐ NEW

This phase enables users to upload reference components (datasheets, CAD files) and have the AI automatically generate enclosures with proper mounting, cutouts, and spacing.

---

## Sprint 27-28: Reference Component Infrastructure (Week 29-30) ✅ COMPLETE

### Sprint Goal
Build the foundation for uploading and storing reference components with dimension extraction.

### Tasks

---

#### P5.1.1.1: Reference Component Model ✅
**Points:** 4 | **Assignee:** Backend | **Priority:** P0

**Description:**
Database models for reference components and their extracted specifications.

**Implementation:** `/backend/app/models/reference_component.py` - ReferenceComponent, ComponentLibrary, ComponentExtractionJob, UserComponent models with full specification fields.
    source_type: str  # "uploaded", "library", "community"
    
    # Source files
    datasheet_file_id: UUID  # Link to File (PDF)
    cad_file_id: UUID  # Link to File (STEP/STL)
    
    # Extracted specifications
    dimensions: JSON  # {length, width, height, unit}
    mounting_holes: JSON  # [{x, y, diameter, thread_size}]
    connectors: JSON  # [{name, type, position, cutout_dimensions}]
    clearance_zones: JSON  # [{name, type, bounds, description}]
    thermal_properties: JSON  # {max_temp, heat_dissipation, requires_venting}
    
    # Metadata
    is_verified: bool  # Admin-verified specifications
    confidence_score: float  # AI extraction confidence
    extraction_status: str  # "pending", "complete", "failed", "manual"
    
class ComponentLibrary(Base):
    """Curated library of popular components."""
    id: UUID
    component_id: UUID  # Link to ReferenceComponent
    category: str
    subcategory: str
    manufacturer: str
    model_number: str
    popularity_score: int
    tags: JSON  # ["raspberry_pi", "sbc", "arm64"]
```

**Acceptance Criteria:**
- [x] ReferenceComponent model with full specification fields
- [x] ComponentLibrary model for curated components
- [x] Support for both user-uploaded and library components
- [x] JSON fields for flexible specification storage
- [x] Migrations created and tested

---

#### P5.1.1.2: Reference Component API - CRUD ✅
**Points:** 4 | **Assignee:** Backend | **Priority:** P0

**Description:**
API endpoints for managing reference components.

**Implementation:** `/backend/app/api/v1/components.py` - Full CRUD for components with library browse/search, extraction triggering.

**Acceptance Criteria:**
- [x] Create component with file upload
- [x] List components with filtering
- [x] Get component with full specifications
- [x] Update specifications manually
- [x] Delete component (soft delete)
- [x] Trigger extraction job
- [x] Browse/search component library

---

#### P5.1.1.3: Reference Component File Storage ✅
**Points:** 2 | **Assignee:** Backend | **Priority:** P0

**Description:**
Storage and retrieval for component source files (PDFs, CAD).

**Implementation:** `/backend/app/services/component_storage.py` - ComponentFileStorage service for PDFs, CAD files, thumbnails.

**Acceptance Criteria:**
- [x] Store PDF datasheets
- [x] Store STEP/STL CAD files
- [x] Generate thumbnails for components
- [x] Link files to component records
- [x] Cleanup orphaned files

---

#### P5.1.2.1: PDF Datasheet Parser Service ✅
**Points:** 5 | **Assignee:** Backend | **Priority:** P0

**Description:**
Service to extract mechanical specifications from PDF datasheets using AI vision.

**Implementation:** `/backend/app/services/datasheet_parser.py` - DatasheetParserService using GPT-4V for dimension extraction.

**Acceptance Criteria:**
- [x] Convert PDF to images for GPT-4V
- [x] Extract overall dimensions (L × W × H)
- [x] Identify mechanical drawing pages
- [x] Extract mounting hole positions and sizes
- [x] Detect connector positions and types
- [x] Parse dimension tables
- [x] Handle multiple units (mm, inches)
- [x] Return confidence scores

---

#### P5.1.2.2: CAD File Dimension Extractor ✅
**Points:** 4 | **Assignee:** Backend | **Priority:** P0

**Description:**
Extract dimensions and features from STEP/STL files.

**Implementation:** `/backend/app/services/cad_extractor.py` - CADDimensionExtractor with STEP and STL support.

**Acceptance Criteria:**
- [x] STEP file bounding box extraction
- [x] STEP hole detection (position, diameter)
- [x] STL bounding box extraction
- [x] STL mesh analysis for features
- [x] Return structured CADExtraction result
- [x] Error handling for corrupt files

---

#### P5.1.3.1: Component Specifications Schema ✅
**Points:** 2 | **Assignee:** Backend | **Priority:** P0

**Description:**
Define Pydantic schemas for component specifications.

**Implementation:** `/backend/app/schemas/component_specs.py` - Full schemas for Dimensions, MountingHole, Connector, ClearanceZone, ThermalProperties, ComponentSpecifications.

**Acceptance Criteria:**
- [x] Dimension schema with units
- [x] Mounting hole schema with position
- [x] Connector schema with cutout requirements
- [x] Clearance zone schema
- [x] Thermal properties schema
- [x] Validation for all schemas

---

### Sprint 27-28 Total: 21 points ✅

---

## Sprint 29-30: Component Library & UI (Week 31-32)

### Sprint Goal
Build the component library with popular hardware and create the UI for managing reference components.

### Tasks

---

#### P5.2.1.1: Seed Popular Components
**Points:** 4 | **Assignee:** Backend | **Priority:** P0

**Description:**
Create seed data for popular components in the library.

**Components to include:**
- **Single Board Computers:** Raspberry Pi 5, Pi 4, Pi Zero 2W, Arduino Uno, Mega, Nano, ESP32
- **Displays:** Common LCD sizes (16x2, 20x4), OLED (0.96", 1.3"), TFT (2.4", 3.5")
- **Input:** Tactile buttons (6x6, 12x12), rotary encoders, joysticks
- **Connectors:** USB-A, USB-C, Barrel jacks, Headers, SD card slots
- **Sensors:** PIR, ultrasonic, DHT22, BME280

**Acceptance Criteria:**
- [ ] 25+ components with verified dimensions
- [ ] Accurate mounting hole positions
- [ ] Connector positions and cutout sizes
- [ ] Thumbnail images for each
- [ ] Proper categorization

---

#### P5.2.1.2: Component Library Search
**Points:** 3 | **Assignee:** Backend | **Priority:** P0

**Description:**
Full-text search and filtering for component library.

**Acceptance Criteria:**
- [ ] Search by name, model number
- [ ] Filter by category
- [ ] Filter by manufacturer
- [ ] Sort by popularity
- [ ] Pagination support

---

#### P5.2.2.1: Component Upload Page
**Points:** 4 | **Assignee:** Frontend | **Priority:** P0

**Description:**
Page for uploading and managing reference components.

**Acceptance Criteria:**
- [ ] File upload for PDF/STEP/STL
- [ ] Component metadata form
- [ ] Progress indicator for extraction
- [ ] Display extracted specifications
- [ ] Edit specifications manually
- [ ] Save component to user library

---

#### P5.2.2.2: Component Library Browser
**Points:** 4 | **Assignee:** Frontend | **Priority:** P0

**Description:**
UI for browsing and selecting from the component library.

**Acceptance Criteria:**
- [ ] Category sidebar navigation
- [ ] Component grid with thumbnails
- [ ] Search bar with auto-complete
- [ ] Component detail modal
- [ ] "Add to project" action
- [ ] Preview 3D model (if available)

---

#### P5.2.2.3: Component Specifications Viewer
**Points:** 3 | **Assignee:** Frontend | **Priority:** P1

**Description:**
Component displaying extracted specifications.

**Acceptance Criteria:**
- [ ] Dimensions display with units
- [ ] Mounting hole diagram
- [ ] Connector list with positions
- [ ] Clearance zones visualization
- [ ] Edit mode for corrections
- [ ] Confidence indicators

---

#### P5.2.3.1: Project Components List
**Points:** 3 | **Assignee:** Frontend | **Priority:** P0

**Description:**
Show reference components attached to a design project.

**Acceptance Criteria:**
- [ ] List of components in project sidebar
- [ ] Add from library button
- [ ] Upload new component button
- [ ] Remove component from project
- [ ] Quantity selector
- [ ] Reorder components

---

### Sprint 29-30 Total: 21 points

---

## Sprint 31-32: Smart Enclosure Generation (Week 33-34) ✅ COMPLETE

### Sprint Goal
AI generates enclosures around reference components with proper mounting and cutouts.

### Tasks

---

#### P5.3.1.1: Enclosure Generation Prompt Engineering ✅
**Points:** 4 | **Assignee:** Backend | **Priority:** P0 | **Status:** DONE

**Description:**
Develop AI prompts for enclosure generation based on component specifications.

**Technical Notes:**
```python
ENCLOSURE_SYSTEM_PROMPT = """
You are a CAD enclosure designer. Given component specifications,
generate CadQuery code for an enclosure that:
1. Fits all components with proper clearance
2. Has mounting standoffs at correct positions
3. Includes cutouts for connectors
4. Provides ventilation where needed
5. Has a removable lid

Component specifications will be provided in JSON format.
Output valid CadQuery Python code.
"""

def build_enclosure_prompt(
    components: list[ComponentSpecifications],
    layout: SpatialLayout,
    style: EnclosureStyle,
) -> str:
    """Build the complete prompt with component data."""
```

**Acceptance Criteria:**
- [x] System prompt for enclosure generation
- [x] Component specifications serialization
- [x] Layout data integration
- [x] Style parameters (wall thickness, corner radius, etc.)
- [x] Test with various component combinations

---

#### P5.3.1.2: Enclosure Generation Service ✅
**Points:** 5 | **Assignee:** Backend | **Priority:** P0 | **Status:** DONE

**Description:**
Service to generate enclosure CAD based on components.

**Technical Notes:**
```python
class EnclosureGenerationService:
    async def generate_enclosure(
        self,
        components: list[ProjectComponent],
        layout: SpatialLayout | None,
        style: EnclosureStyle,
        options: EnclosureOptions,
    ) -> GenerationResult:
        """
        1. Calculate required internal dimensions
        2. Add clearance margins
        3. Position components (auto-layout or user-specified)
        4. Generate AI prompt
        5. Execute CadQuery code
        6. Verify mounting holes and cutouts
        7. Return enclosure with components
        """
        
    def calculate_internal_dimensions(
        self,
        components: list[ProjectComponent],
        layout: SpatialLayout,
    ) -> Dimensions:
        """Calculate minimum internal dimensions."""
        
    def position_mounting_standoffs(
        self,
        component: ProjectComponent,
        position: Position,
    ) -> list[Standoff]:
        """Generate standoff positions for a component."""
```

**Acceptance Criteria:**
- [x] Calculate enclosure size from components
- [x] Generate mounting standoffs at correct positions
- [x] Create connector cutouts on correct faces
- [x] Add ventilation slots if thermal properties warrant
- [x] Generate lid with closure mechanism
- [x] Return full CAD model with component positioning

---

#### P5.3.1.3: Mounting Standoff Generation ✅
**Points:** 3 | **Assignee:** Backend | **Priority:** P0 | **Status:** DONE

**Description:**
Generate mounting standoffs based on component specifications.

**Technical Notes:**
```python
class StandoffGenerator:
    def generate_standoffs(
        self,
        holes: list[MountingHole],
        component_position: Position,
        options: StandoffOptions,
    ) -> cq.Workplane:
        """
        Generate standoffs for each mounting hole.
        Options: height, outer_diameter, thread_type, boss_type
        """
        
    def generate_heat_set_insert_boss(
        self,
        hole: MountingHole,
        insert_spec: InsertSpec,
    ) -> cq.Workplane:
        """Generate boss for heat-set inserts."""
```

**Acceptance Criteria:**
- [x] Standard M2, M2.5, M3 standoffs
- [x] Configurable height
- [x] Hollow for threading or heat-set inserts
- [x] Boss style options
- [x] Position relative to component

---

#### P5.3.1.4: Connector Cutout Generation ✅
**Points:** 3 | **Assignee:** Backend | **Priority:** P0 | **Status:** DONE

**Description:**
Generate cutouts for connectors on enclosure walls.

**Technical Notes:**
```python
class CutoutGenerator:
    def generate_cutout(
        self,
        connector: Connector,
        wall_face: Face,
        wall_thickness: float,
    ) -> cq.Workplane:
        """
        Generate cutout for a connector.
        Handles: USB, HDMI, barrel jack, GPIO, SD card, etc.
        """
        
    def get_cutout_profile(
        self,
        connector_type: str,
    ) -> CutoutProfile:
        """Get standard cutout profile for connector type."""
```

**Acceptance Criteria:**
- [x] Standard cutout profiles for common connectors
- [x] USB-A, USB-C, Micro-USB cutouts
- [x] HDMI, Mini-HDMI cutouts
- [x] GPIO header slot
- [x] Barrel jack opening
- [x] SD card slot
- [x] Custom rectangular cutout

---

#### P5.3.2.1: Enclosure Generation API ✅
**Points:** 3 | **Assignee:** Backend | **Priority:** P0 | **Status:** DONE

**Description:**
API endpoint to generate enclosure for project components.

**Technical Notes:**
```python
@router.post("/projects/{project_id}/generate-enclosure")
async def generate_enclosure(
    project_id: UUID,
    request: EnclosureRequest,
) -> GenerationJobResponse:
    """
    Request body:
    - layout: Optional spatial layout
    - style: EnclosureStyle
    - options: EnclosureOptions (wall thickness, corner radius, etc.)
    - components: Optional override of component positions
    """
```

**Acceptance Criteria:**
- [x] Queue enclosure generation job
- [x] Return job ID for status polling
- [x] Support custom layout or auto-layout
- [x] Accept style/options parameters
- [x] Validate component specifications

---

#### P5.3.2.2: Enclosure Style Templates ✅
**Points:** 3 | **Assignee:** Backend | **Priority:** P1 | **Status:** DONE

**Description:**
Pre-defined enclosure style templates.

**Styles:**
- **Minimal:** Thin walls, tight fit, snap-fit lid
- **Rugged:** Thick walls, rounded corners, screwed lid
- **Vented:** Standard walls, ventilation slots, snap-fit
- **Stackable:** Interlocking edges, modular design
- **Desktop:** Angled front, display-friendly, premium feel

**Acceptance Criteria:**
- [x] 5 style templates with parameters
- [x] Wall thickness per style
- [x] Corner radius per style
- [x] Lid closure type per style
- [x] Ventilation pattern per style

---

### Sprint 31-32 Total: 21 points ✅ ALL COMPLETE

---

## Sprint 33-34: Spatial Layout & UI (Week 35-36)

### Sprint Goal
Visual layout tool for positioning components and enclosure customization UI.

### Tasks

---

#### P5.4.1.1: Spatial Layout Model
**Points:** 3 | **Assignee:** Backend | **Priority:** P0

**Description:**
Data model for component spatial arrangement.

**Technical Notes:**
```python
class SpatialLayout(Base):
    id: UUID
    project_id: UUID
    name: str  # "Layout v1", "Compact", etc.
    
    # Internal dimensions (calculated or specified)
    internal_width: float
    internal_depth: float
    internal_height: float
    
class ComponentPlacement(Base):
    id: UUID
    layout_id: UUID
    component_id: UUID  # Link to ReferenceComponent
    
    # Position within enclosure (bottom-left origin)
    x: float
    y: float
    z: float  # Height above floor
    
    # Rotation
    rotation_z: float  # 0, 90, 180, 270 degrees
    
    # Constraints
    face_direction: str  # Which face of enclosure component faces
    locked: bool  # User locked position
```

**Acceptance Criteria:**
- [ ] Layout model with internal dimensions
- [ ] ComponentPlacement with position/rotation
- [ ] Support multiple layouts per project
- [ ] Face direction for connector cutout placement

---

#### P5.4.1.2: Spatial Layout API
**Points:** 3 | **Assignee:** Backend | **Priority:** P0

**Description:**
API for managing spatial layouts.

**Acceptance Criteria:**
- [ ] Create layout for project
- [ ] Add/update component placement
- [ ] Remove component from layout
- [ ] Auto-layout algorithm
- [ ] Validate layout (no collisions)

---

#### P5.4.1.3: Auto-Layout Algorithm
**Points:** 4 | **Assignee:** Backend | **Priority:** P1

**Description:**
Automatically arrange components within enclosure.

**Algorithm considerations:**
- Components shouldn't overlap
- Connectors should face accessible edges
- Cable routing space between components
- Thermal considerations (heat sources spread out)

**Acceptance Criteria:**
- [ ] Pack components efficiently
- [ ] Align connectors to edges
- [ ] Maintain minimum clearance
- [ ] Consider thermal placement
- [ ] Multiple layout suggestions

---

#### P5.4.2.1: 2D Layout Editor Component
**Points:** 5 | **Assignee:** Frontend | **Priority:** P0

**Description:**
Interactive 2D canvas for arranging components.

**Acceptance Criteria:**
- [ ] Canvas showing enclosure footprint
- [ ] Component shapes as draggable items
- [ ] Snap to grid
- [ ] Alignment guides
- [ ] Collision detection (visual warning)
- [ ] Rotate component (90° increments)
- [ ] Zoom/pan canvas
- [ ] Show connector positions on components

---

#### P5.4.2.2: 3D Layout Preview
**Points:** 4 | **Assignee:** Frontend | **Priority:** P1

**Description:**
3D preview of component layout within enclosure.

**Acceptance Criteria:**
- [ ] Load component 3D models
- [ ] Position per layout
- [ ] Show enclosure walls (transparent)
- [ ] Click component to select
- [ ] Sync selection with 2D editor
- [ ] Show mounting standoffs

---

#### P5.4.3.1: Enclosure Generation UI
**Points:** 4 | **Assignee:** Frontend | **Priority:** P0

**Description:**
UI for configuring and generating enclosure.

**Acceptance Criteria:**
- [ ] Select components from project
- [ ] Choose layout (auto or manual)
- [ ] Select style template
- [ ] Customize parameters (wall thickness, corner radius)
- [ ] Generate button with progress
- [ ] Preview result
- [ ] Save to project

---

#### P5.4.3.2: Enclosure Options Panel
**Points:** 3 | **Assignee:** Frontend | **Priority:** P1

**Description:**
Panel for customizing enclosure options.

**Acceptance Criteria:**
- [ ] Wall thickness slider
- [ ] Corner radius slider
- [ ] Lid type selection
- [ ] Ventilation toggle
- [ ] Mounting options (standoff type)
- [ ] Cable gland positions
- [ ] Label text (optional)

---

### Sprint 33-34 Total: 26 points

---

## Phase 5 Summary

| Sprint | Focus | Points | Status |
|--------|-------|--------|--------|
| 27-28 | Reference Component Infrastructure | 21 | Ready |
| 29-30 | Component Library & UI | 21 | Ready |
| 31-32 | Smart Enclosure Generation | 21 | Ready |
| 33-34 | Spatial Layout & UI | 26 | Ready |
| **Total** | | **89** | |

---

# Phase 6: COTS & Supplier Integration

---

## Sprint 35-36: Hardware Sourcing & McMaster Integration (Week 37-38)

### Sprint Goal
AI recognizes hardware needs, queries McMaster-Carr, imports STEP files, tracks in BOM.

### Tasks

---

#### P6.1.1.1: Supplier Adapter Framework
**Points:** 4 | **Assignee:** Backend | **Priority:** P0

**Description:**
Generic adapter pattern for supplier integrations.

**Technical Notes:**
```python
class SupplierAdapter(ABC):
    @abstractmethod
    async def search(self, query: str, category: str) -> list[SupplierPart]
    
    @abstractmethod
    async def get_part(self, part_number: str) -> SupplierPart
    
    @abstractmethod
    async def download_cad(self, part_number: str, format: str) -> bytes
    
    @abstractmethod
    async def add_to_cart(self, items: list[CartItem], user_token: str) -> CartResult

class SupplierPart(BaseModel):
    part_number: str
    description: str
    price: Decimal
    currency: str
    cad_available: bool
    cad_formats: list[str]
    specifications: dict
    image_url: str
    product_url: str
```

**Acceptance Criteria:**
- [ ] Abstract base class for suppliers
- [ ] Standard part/search response models
- [ ] Error handling for API failures
- [ ] Rate limiting support
- [ ] Caching layer for part lookups

---

#### P5.1.1.2: McMaster-Carr Adapter
**Points:** 5 | **Assignee:** Backend | **Priority:** P0

**Description:**
Implement McMaster-Carr supplier adapter.

**Technical Notes:**
McMaster uses a web-based API. May need to:
- Parse HTML responses or use unofficial API
- Handle authentication for CAD downloads
- Respect rate limits

**Acceptance Criteria:**
- [ ] Search parts by keyword/category
- [ ] Get part details by part number
- [ ] Download STEP files
- [ ] Handle pricing (may need auth)
- [ ] Category mapping (fasteners, seals, etc.)
- [ ] Error handling for unavailable parts

---

#### P5.1.2.1: Hardware Categories & Mapping
**Points:** 3 | **Assignee:** Backend | **Priority:** P0

**Description:**
Define hardware categories and standard specifications.

**Technical Notes:**
```python
HARDWARE_CATEGORIES = {
    "fasteners": {
        "screw": ["thread_size", "length", "head_type", "drive_type", "material"],
        "bolt": ["thread_size", "length", "head_type", "material", "grade"],
        "nut": ["thread_size", "type", "material"],
        "washer": ["size", "type", "material"],
    },
    "inserts": {
        "threaded_insert": ["thread_size", "install_type", "material", "length"],
        "heat_set_insert": ["thread_size", "length", "material"],
    },
    "seals": {
        "o_ring": ["id", "od", "cross_section", "material"],
        "gasket": ["type", "size", "material", "thickness"],
    },
    ...
}
```

**Acceptance Criteria:**
- [ ] Category taxonomy defined
- [ ] Standard specifications per category
- [ ] Units normalization (imperial/metric)
- [ ] Material mapping (steel, aluminum, nylon, etc.)

---

#### P5.1.2.2: AI Hardware Recognition Prompts
**Points:** 4 | **Assignee:** Backend | **Priority:** P0

**Description:**
Enhance AI prompts to recognize when COTS hardware is needed.

**Technical Notes:**
```python
HARDWARE_RECOGNITION_PROMPT = """
When analyzing the design request, identify any standard hardware components that should be sourced rather than custom-manufactured:
- Fasteners (screws, bolts, nuts, washers)
- Inserts (threaded inserts, heat-set inserts)
- Seals (O-rings, gaskets)
- Bearings (ball bearings, bushings)
- Springs
- Hinges, latches, handles
- Electrical components (standoffs, cable glands)

For each hardware item, specify:
1. Category and type
2. Critical dimensions
3. Material requirements
4. Quantity needed
5. Search terms for supplier lookup
"""
```

**Acceptance Criteria:**
- [ ] AI identifies hardware in descriptions
- [ ] Structured output for hardware specs
- [ ] Default to COTS over custom
- [ ] Handle "custom" when no COTS match exists

---

#### P5.1.3.1: Hardware Search API
**Points:** 3 | **Assignee:** Backend | **Priority:** P0

**Description:**
API to search suppliers for hardware.

**Acceptance Criteria:**
- [ ] Search by category + specifications
- [ ] Return matching parts from suppliers
- [ ] Include pricing, availability
- [ ] Pagination for large results
- [ ] Filter by supplier

---

#### P5.1.3.2: Import Hardware to Assembly
**Points:** 4 | **Assignee:** Backend | **Priority:** P0

**Description:**
Download STEP and add to assembly as component.

**Acceptance Criteria:**
- [ ] Download STEP file from supplier
- [ ] Store in file system
- [ ] Create Design record (marked as COTS)
- [ ] Add to assembly as component
- [ ] Create BOM item with vendor info
- [ ] Track part number and source

---

#### P5.1.4.1: Hardware Search UI
**Points:** 4 | **Assignee:** Frontend | **Priority:** P1

**Description:**
UI for searching and adding hardware to assemblies.

**Acceptance Criteria:**
- [ ] Search input with category filter
- [ ] Results grid with images
- [ ] Part details modal
- [ ] Add to assembly button
- [ ] Quantity input
- [ ] Show price and availability

---

### Sprint 35-36 Total: 27 points

---

## Sprint 37-38: Order Flow & Cart Integration (Week 39-40)

### Sprint Goal
Push BOM hardware to supplier cart for ordering.

### Tasks

---

#### P5.2.1.1: Cart Integration API
**Points:** 4 | **Assignee:** Backend | **Priority:** P0

**Description:**
API to push BOM items to supplier carts.

**Technical Notes:**
```python
@router.post("/assemblies/{id}/order-hardware")
async def order_hardware(
    assembly_id: UUID,
    request: OrderRequest,  # supplier_id, items filter
) -> OrderResponse:
    # Group items by supplier
    # Call supplier.add_to_cart()
    # Return cart URLs
```

**Acceptance Criteria:**
- [ ] Group BOM items by supplier
- [ ] Push items to supplier cart
- [ ] Return cart URL for checkout
- [ ] Handle partial failures (some items fail)
- [ ] Track order in history

---

#### P5.2.1.2: McMaster Cart Push
**Points:** 3 | **Assignee:** Backend | **Priority:** P0

**Description:**
Implement cart push for McMaster-Carr.

**Acceptance Criteria:**
- [ ] Add multiple items to cart
- [ ] Handle quantity
- [ ] Return cart URL
- [ ] Error handling for out-of-stock

---

#### P5.2.2.1: Order Hardware UI
**Points:** 4 | **Assignee:** Frontend | **Priority:** P0

**Description:**
UI for ordering hardware from BOM.

**Acceptance Criteria:**
- [ ] "Order Hardware" button on BOM
- [ ] Supplier selection (if multiple)
- [ ] Review items before ordering
- [ ] Checkbox to select/deselect items
- [ ] Opens supplier cart in new tab
- [ ] Success confirmation

---

#### P5.2.2.2: Order History
**Points:** 3 | **Assignee:** Frontend | **Priority:** P1

**Description:**
Track past hardware orders.

**Acceptance Criteria:**
- [ ] Order history page
- [ ] Link to supplier orders
- [ ] Items ordered per order
- [ ] Re-order button

---

#### P5.2.3.1: Supplier Account Linking
**Points:** 3 | **Assignee:** Backend | **Priority:** P1

**Description:**
Allow users to link supplier accounts for seamless ordering.

**Acceptance Criteria:**
- [ ] Store encrypted supplier credentials
- [ ] OAuth where supported
- [ ] Test connection
- [ ] Use linked account for cart push

---

#### P5.2.3.2: Supplier Settings UI
**Points:** 2 | **Assignee:** Frontend | **Priority:** P1

**Description:**
UI for managing supplier connections.

**Acceptance Criteria:**
- [ ] List connected suppliers
- [ ] Connect new supplier
- [ ] Disconnect supplier
- [ ] Set default supplier

---

### Sprint 37-38 Total: 19 points

---

# Phase 7: Monetization & Organizations

---

## Sprint 39-40: Credits, Tiers & Quotas (Week 41-42)

### Sprint Goal
Implement credit system, subscription tiers, and usage enforcement.

### Tasks

---

#### P6.1.1.1: Subscription Tier Model
**Points:** 3 | **Assignee:** Backend | **Priority:** P0

**Description:**
Database models for subscription tiers and user subscriptions.

**Technical Notes:**
```python
class SubscriptionTier(Base):
    id, name, slug  # "free", "pro", "enterprise"
    monthly_credits: int
    max_concurrent_jobs: int
    max_storage_gb: int
    features: JSON  # Feature flags
    price_monthly: Decimal
    price_yearly: Decimal
    
class UserSubscription(Base):
    id, user_id, tier_id
    status  # "active", "canceled", "past_due"
    current_period_start, current_period_end
    cancel_at_period_end: bool
```

**Acceptance Criteria:**
- [ ] Tier model with limits and features
- [ ] User subscription model
- [ ] Default free tier on registration
- [ ] Tier feature flags

---

#### P6.1.1.2: Credit System Model
**Points:** 3 | **Assignee:** Backend | **Priority:** P0

**Description:**
Credit balance and transaction tracking.

**Technical Notes:**
```python
class CreditBalance(Base):
    id, user_id
    balance: int
    last_refill_at: datetime
    
class CreditTransaction(Base):
    id, user_id
    amount: int  # Positive = add, negative = spend
    transaction_type  # "refill", "generation", "purchase", "refund"
    description: str
    reference_id: UUID  # Job ID, etc.
    created_at: datetime
```

**Acceptance Criteria:**
- [ ] Credit balance per user
- [ ] Transaction history
- [ ] Automatic monthly refill
- [ ] Purchase credits endpoint

---

#### P6.1.2.1: Credit Enforcement Middleware
**Points:** 4 | **Assignee:** Backend | **Priority:** P0

**Description:**
Middleware to check and deduct credits for operations.

**Technical Notes:**
```python
OPERATION_COSTS = {
    "generation": 1,
    "refine": 1,
    "export_2d": 2,
    "hardware_search": 0,  # Free
}

async def check_credits(
    operation: str,
    user: User,
    db: AsyncSession,
) -> bool:
    cost = OPERATION_COSTS.get(operation, 0)
    balance = await get_credit_balance(user.id, db)
    return balance >= cost
```

**Acceptance Criteria:**
- [ ] Define operation costs
- [ ] Check balance before operation
- [ ] Deduct on success
- [ ] Return friendly error when insufficient
- [ ] Dependency injection for endpoints

---

#### P6.1.2.2: Concurrency Limit Enforcement
**Points:** 3 | **Assignee:** Backend | **Priority:** P0

**Description:**
Limit concurrent jobs based on tier.

**Acceptance Criteria:**
- [ ] Track active jobs per user
- [ ] Check limit before job creation
- [ ] Return queue position if over limit
- [ ] Auto-start queued jobs when slots free

---

#### P6.1.3.1: Usage Dashboard API
**Points:** 2 | **Assignee:** Backend | **Priority:** P1

**Description:**
API for usage statistics.

**Acceptance Criteria:**
- [ ] Current credit balance
- [ ] Credits used this period
- [ ] Breakdown by operation type
- [ ] Storage used
- [ ] Active jobs count

---

#### P6.1.3.2: Usage & Billing UI
**Points:** 4 | **Assignee:** Frontend | **Priority:** P1

**Description:**
User interface for viewing usage and managing subscription.

**Acceptance Criteria:**
- [ ] Usage dashboard with charts
- [ ] Credit balance display
- [ ] Transaction history
- [ ] Current plan display
- [ ] Upgrade/downgrade buttons
- [ ] Purchase credits button

---

### Sprint 39-40 Total: 19 points

---

## Sprint 41-42: Organizations & Teams (Week 43-44)

### Sprint Goal
Multi-user organizations with roles, shared resources, and org billing.

### Tasks

---

#### P6.2.1.1: Organization Model
**Points:** 4 | **Assignee:** Backend | **Priority:** P0

**Description:**
Database models for organizations and membership.

**Technical Notes:**
```python
class Organization(Base):
    id, name, slug
    owner_id: UUID  # Creator/primary admin
    settings: JSON
    
class OrganizationMember(Base):
    id, org_id, user_id
    role  # "owner", "admin", "member", "viewer"
    invited_by_id: UUID
    invited_at, joined_at
    
class OrganizationInvite(Base):
    id, org_id, email
    role, token
    expires_at
    accepted_at
```

**Acceptance Criteria:**
- [ ] Organization model
- [ ] Membership with roles
- [ ] Invite system
- [ ] Org owns projects (optional)
- [ ] User can be in multiple orgs

---

#### P6.2.1.2: Organization API
**Points:** 5 | **Assignee:** Backend | **Priority:** P0

**Description:**
API for organization management.

**Acceptance Criteria:**
- [ ] Create organization
- [ ] Invite member by email
- [ ] Accept/decline invite
- [ ] Remove member
- [ ] Change member role
- [ ] Transfer ownership
- [ ] Delete organization

---

#### P6.2.2.1: Org Resource Ownership
**Points:** 4 | **Assignee:** Backend | **Priority:** P0

**Description:**
Projects and designs can be owned by org instead of user.

**Acceptance Criteria:**
- [ ] Add org_id to Project model
- [ ] Permission checks for org resources
- [ ] List org's projects
- [ ] Move project between personal/org
- [ ] Org members can access based on role

---

#### P6.2.2.2: Org Billing
**Points:** 3 | **Assignee:** Backend | **Priority:** P1

**Description:**
Organization-level subscriptions and credits.

**Acceptance Criteria:**
- [ ] Org has subscription tier
- [ ] Org has credit pool
- [ ] Member actions deduct from org
- [ ] Per-seat pricing support
- [ ] Billing admin role

---

#### P6.2.3.1: Organization Settings Page
**Points:** 4 | **Assignee:** Frontend | **Priority:** P0

**Description:**
UI for managing organization.

**Acceptance Criteria:**
- [ ] Org profile settings
- [ ] Member list with roles
- [ ] Invite new members
- [ ] Remove/change role
- [ ] Pending invites

---

#### P6.2.3.2: Org Switcher Component
**Points:** 2 | **Assignee:** Frontend | **Priority:** P0

**Description:**
Switch between personal and org contexts.

**Acceptance Criteria:**
- [ ] Dropdown in header
- [ ] List personal + orgs
- [ ] Visual indicator of current context
- [ ] Context affects project list

---

#### P6.2.4.1: SSO Integration (SAML/OIDC)
**Points:** 5 | **Assignee:** Backend | **Priority:** P2

**Description:**
Enterprise SSO support for organizations.

**Acceptance Criteria:**
- [ ] SAML 2.0 support
- [ ] OIDC support
- [ ] Org-level SSO configuration
- [ ] Auto-provision users
- [ ] Enforce SSO for org members

---

### Sprint 41-42 Total: 27 points

---

# Phase 8: Advanced Features

---

## Sprint 43-44: Advanced CAD Viewer (Week 45-46)

### Sprint Goal
Full-featured CAD viewer with measurements, cross-sections, annotations.

### Tasks

---

#### P7.1.1.1: Measurement Tool
**Points:** 5 | **Assignee:** Frontend | **Priority:** P0

**Description:**
Measure distances, angles, and dimensions in 3D viewer.

**Technical Notes:**
Use Three.js raycasting to pick points on geometry. Calculate:
- Point-to-point distance
- Edge length
- Face area
- Angles between faces

**Acceptance Criteria:**
- [ ] Click two points to measure distance
- [ ] Click edge to show length
- [ ] Angle measurement mode
- [ ] Dimension labels in 3D space
- [ ] Clear measurements button
- [ ] Export measurements list

---

#### P7.1.1.2: Cross-Section Tool
**Points:** 4 | **Assignee:** Frontend | **Priority:** P0

**Description:**
Cut plane to view internal geometry.

**Acceptance Criteria:**
- [ ] Toggle cross-section mode
- [ ] Adjustable cut plane (X, Y, Z axis)
- [ ] Slider to move plane position
- [ ] Multiple cut planes
- [ ] Cross-section fill color

---

#### P7.1.1.3: Render Modes
**Points:** 3 | **Assignee:** Frontend | **Priority:** P1

**Description:**
Different visualization modes for the 3D model.

**Acceptance Criteria:**
- [ ] Shaded (default)
- [ ] Wireframe
- [ ] Shaded + edges
- [ ] Transparent/X-ray
- [ ] Hidden line
- [ ] Material colors

---

#### P7.1.2.1: 3D Annotations Model
**Points:** 3 | **Assignee:** Backend | **Priority:** P0

**Description:**
Store annotations pinned to 3D coordinates.

**Technical Notes:**
```python
class DesignAnnotation(Base):
    id, design_id, user_id
    position: JSON  # {x, y, z}
    normal: JSON  # Surface normal for orientation
    content: str  # Markdown
    annotation_type  # "note", "question", "issue", "approval"
    resolved: bool
    parent_id: UUID  # For threading
```

**Acceptance Criteria:**
- [ ] Annotation model with 3D position
- [ ] Thread replies
- [ ] Resolution status
- [ ] Annotation types

---

#### P7.1.2.2: 3D Annotations UI
**Points:** 5 | **Assignee:** Frontend | **Priority:** P0

**Description:**
Click on model to add annotations, view annotation markers.

**Acceptance Criteria:**
- [ ] Click point on model to add annotation
- [ ] Annotation markers visible in 3D
- [ ] Click marker to view/edit
- [ ] Annotation list panel
- [ ] Filter by type/status
- [ ] Reply to annotation

---

#### P7.1.3.1: Screenshot & Export
**Points:** 2 | **Assignee:** Frontend | **Priority:** P1

**Description:**
Capture current view as image.

**Acceptance Criteria:**
- [ ] Screenshot button
- [ ] Choose resolution
- [ ] Include/exclude annotations
- [ ] Transparent background option
- [ ] Download as PNG/JPG

---

### Sprint 43-44 Total: 22 points

---

## Sprint 45-46: Collaboration & Notifications (Week 47-48)

### Sprint Goal
Complete collaboration features: sharing, comments, and notification system.

### Tasks

---

#### P7.2.1.1: Sharing API
**Points:** 4 | **Assignee:** Backend | **Priority:** P0

**Description:**
API for sharing designs and projects.

**Technical Notes:**
DesignShare model already exists. Need endpoints:
```python
@router.post("/designs/{id}/share")
@router.get("/shared-with-me")
@router.delete("/shares/{id}")
@router.post("/designs/{id}/share-link")
```

**Acceptance Criteria:**
- [ ] Share with user by email
- [ ] Permission levels (view, comment, edit)
- [ ] List designs shared with me
- [ ] Revoke share
- [ ] Share link generation
- [ ] Password-protected links
- [ ] Expiring links

---

#### P7.2.1.2: Comment Model & API
**Points:** 4 | **Assignee:** Backend | **Priority:** P0

**Description:**
Threaded comments on designs.

**Technical Notes:**
```python
class DesignComment(Base):
    id, design_id, user_id
    content: str  # Markdown
    parent_id: UUID  # For threading
    mentions: JSON  # User IDs mentioned
    edited_at: datetime
    deleted_at: datetime
```

**Acceptance Criteria:**
- [ ] Add comment to design
- [ ] Reply to comment
- [ ] Edit own comment
- [ ] Delete own comment
- [ ] Mention users with @username
- [ ] List comments with threading

---

#### P7.2.2.1: Notification Model & Service
**Points:** 4 | **Assignee:** Backend | **Priority:** P0

**Description:**
In-app and email notifications.

**Technical Notes:**
```python
class Notification(Base):
    id, user_id
    type  # "share", "comment", "mention", "job_complete"
    title, message
    action_url: str
    read_at: datetime
    
class NotificationPreference(Base):
    user_id
    type, email_enabled, in_app_enabled
```

**Acceptance Criteria:**
- [ ] Notification model
- [ ] Preference model per type
- [ ] Create notification service
- [ ] Trigger on events (share, comment, etc.)
- [ ] Email sending integration

---

#### P7.2.2.2: Notification API
**Points:** 2 | **Assignee:** Backend | **Priority:** P0

**Description:**
API for retrieving and managing notifications.

**Acceptance Criteria:**
- [ ] List notifications (unread first)
- [ ] Mark as read (single, all)
- [ ] Delete notification
- [ ] Unread count
- [ ] Preferences CRUD

---

#### P7.2.3.1: Sharing UI
**Points:** 3 | **Assignee:** Frontend | **Priority:** P0

**Description:**
Share dialog and shared-with-me page.

**Acceptance Criteria:**
- [ ] Share button on design
- [ ] Share dialog with email input
- [ ] Permission dropdown
- [ ] Current shares list
- [ ] Generate share link
- [ ] "Shared with me" page

---

#### P7.2.3.2: Comments UI
**Points:** 4 | **Assignee:** Frontend | **Priority:** P0

**Description:**
Comments panel for designs.

**Acceptance Criteria:**
- [ ] Comments tab/panel
- [ ] Add comment with markdown
- [ ] Threaded replies
- [ ] Edit/delete own
- [ ] @mention autocomplete
- [ ] Link 3D annotations to comments

---

#### P7.2.3.3: Notification Center UI
**Points:** 3 | **Assignee:** Frontend | **Priority:** P0

**Description:**
Bell icon with notification dropdown.

**Acceptance Criteria:**
- [ ] Bell icon in header
- [ ] Unread count badge
- [ ] Dropdown with recent notifications
- [ ] Mark as read
- [ ] Link to full notification page
- [ ] Click to navigate to action

---

### Sprint 45-46 Total: 24 points

---

## Sprint 47-48: Design Iteration & 2D Drawings (Week 49-50)

### Sprint Goal
Refine mode for AI iteration, 2D drawing generation.

### Tasks

---

#### P7.3.1.1: Design Context Model
**Points:** 3 | **Assignee:** Backend | **Priority:** P0

**Description:**
Track conversation context for design iteration.

**Technical Notes:**
```python
class DesignContext(Base):
    id, design_id
    messages: JSON  # Conversation history
    parameters: JSON  # Current parameters
    iteration_count: int
```

**Acceptance Criteria:**
- [ ] Store conversation history
- [ ] Track parameter changes
- [ ] Link to design versions

---

#### P7.3.1.2: Refine Endpoint
**Points:** 4 | **Assignee:** Backend | **Priority:** P0

**Description:**
API to refine existing design with follow-up instructions.

**Technical Notes:**
```python
@router.post("/designs/{id}/refine")
async def refine_design(
    design_id: UUID,
    request: RefineRequest,  # instruction, apply_immediately
) -> RefineResponse:
    # Load context
    # Add user instruction to conversation
    # AI understands current state + changes
    # Generate modified CAD
    # Save as new version
```

**Acceptance Criteria:**
- [ ] Load existing design context
- [ ] Accept natural language instruction
- [ ] AI understands "make it taller"
- [ ] Generate modified geometry
- [ ] Create new version
- [ ] Preserve conversation history

---

#### P7.3.1.3: Refine Mode UI
**Points:** 4 | **Assignee:** Frontend | **Priority:** P0

**Description:**
Chat-like interface for design refinement.

**Acceptance Criteria:**
- [ ] Chat panel on design detail
- [ ] Show conversation history
- [ ] Input for follow-up instruction
- [ ] Loading state during refinement
- [ ] Preview changes before applying
- [ ] Version comparison

---

#### P7.3.2.1: 2D Drawing Generator
**Points:** 5 | **Assignee:** Backend | **Priority:** P0

**Description:**
Generate 2D engineering drawings from 3D models.

**Technical Notes:**
Use CadQuery/OCP projection capabilities:
- Orthographic views (front, top, side)
- Section views
- Auto-dimensioning
- Export to DXF/PDF

**Acceptance Criteria:**
- [ ] Generate orthographic projections
- [ ] Standard drawing layouts (A4, Letter, etc.)
- [ ] Section views
- [ ] Basic auto-dimensioning
- [ ] Title block
- [ ] Export PDF and DXF

---

#### P7.3.2.2: Drawing Customization
**Points:** 3 | **Assignee:** Backend | **Priority:** P1

**Description:**
Customize 2D drawing output.

**Acceptance Criteria:**
- [ ] Choose which views
- [ ] Adjust scale
- [ ] Add/remove dimensions
- [ ] Custom title block
- [ ] Drawing standards (ISO, ASME)

---

#### P7.3.2.3: 2D Drawing UI
**Points:** 3 | **Assignee:** Frontend | **Priority:** P0

**Description:**
UI for generating and customizing 2D drawings.

**Acceptance Criteria:**
- [ ] "Create Drawing" button on design
- [ ] Preview drawing
- [ ] View/scale selection
- [ ] Download PDF/DXF
- [ ] Save drawing to design

---

### Sprint 47-48 Total: 22 points

---

# Full Roadmap Summary

## Phase 1-2 (Complete): Foundation, Auth, Templates, Generation
| Sprint | Focus | Points | Status |
|--------|-------|--------|--------|
| 1-2 | Foundation & AI POC | ~20 | ✅ Complete |
| 3-4 | Authentication | ~20 | ✅ Complete |
| 5-6 | Templates | ~20 | ✅ Complete |
| 7-8 | NL Generation | ~20 | ✅ Complete |
| 9-10 | File Upload & Processing | ~20 | ✅ Complete |
| 11-12 | CAD Modification & Versioning | 19 | ✅ Complete |
| 13-14 | Content Moderation & Disaster Recovery | 19 | ✅ Complete |

## Phase 3: Quality & Production
| Sprint | Focus | Points | Status |
|--------|-------|--------|--------|
| 15-16 | Testing Infrastructure | 21 | ✅ Complete |
| 17-18 | Frontend Integration + Collaboration | 23 | ✅ Complete |
| 19-20 | UX Polish + Accessibility | 19 | ✅ Complete |
| 21-22 | E2E + Production | 19 | ✅ Complete |

## Phase 4: Core Functionality
| Sprint | Focus | Points | Status |
|--------|-------|--------|--------|
| 23-24 | Projects, Save Flow & Dashboard | 26 | Ready |
| 25-26 | Assemblies & BOM | 27 | Ready |

## Phase 5: Reference Components & Smart Enclosures ⭐ NEW
| Sprint | Focus | Points | Status |
|--------|-------|--------|--------|
| 27-28 | Reference Component Infrastructure | 21 | Ready |
| 29-30 | Component Library & UI | 21 | Ready |
| 31-32 | Smart Enclosure Generation | 21 | Ready |
| 33-34 | Spatial Layout & UI | 26 | Ready |

## Phase 6: COTS & Suppliers
| Sprint | Focus | Points | Status |
|--------|-------|--------|--------|
| 35-36 | Hardware Sourcing & McMaster | 27 | Ready |
| 37-38 | Order Flow & Cart Integration | 19 | Ready |

## Phase 7: Monetization & Organizations
| Sprint | Focus | Points | Status |
|--------|-------|--------|--------|
| 39-40 | Credits, Tiers & Quotas | 19 | Ready |
| 41-42 | Organizations & Teams | 27 | Ready |

## Phase 8: Advanced Features
| Sprint | Focus | Points | Status |
|--------|-------|--------|--------|
| 43-44 | Advanced CAD Viewer | 22 | Ready |
| 45-46 | Collaboration & Notifications | 24 | Ready |
| 47-48 | Design Iteration & 2D Drawings | 22 | Ready |

---

**Total Remaining: 384 story points across 34 sprints (17 sprint pairs)**

---

## Dependency Graph

```
Sprint 1 (Foundation)
    ├── P0.1.1.* (CAD POC) ──────────────────┐
    │                                         │
    └── P0.2.1.* (Repo/Docker) ──────────────┼─── Sprint 2 (AI POC)
                                              │         │
Sprint 2 (AI POC)                             │         │
    ├── P0.1.2.* (AI Integration) ────────────┘         │
    │                                                   │
    └── P0.2.2.* (CI/CD) ───────────────────────────────┼─── Sprint 3-4 (Auth)
                                                        │         │
Sprint 3-4 (Auth)                                       │         │
    ├── P1.1.1.* (Registration) ────────────────────────┘         │
    │                                                             │
    ├── P1.1.2.* (Login) ─────────────────────────────────────────┼─── Sprint 5-6 (Templates)
    │                                                             │
    └── P1.1.3.* (Password Reset) ────────────────────────────────┘

Sprint 5-6 (Templates)
    ├── P1.2.1.* (Template Catalog)
    │
    ├── P1.2.3.* (Template Implementations)
    │
    └── P1.4.2.* (3D Viewer) ────────────────────────────── Sprint 7-8 (NL Generation)

... continues through Phase 3
```

---

## Definition of Done (Global)

All tasks must meet these criteria:

### Code Quality
- [ ] Code follows project style guide
- [ ] No linter warnings
- [ ] Type hints (Python) / TypeScript types
- [ ] Meaningful variable/function names
- [ ] Comments for complex logic

### Testing
- [ ] Unit tests written
- [ ] Tests pass locally
- [ ] Tests pass in CI
- [ ] Coverage meets threshold (80%)

### Documentation
- [ ] API endpoints documented in OpenAPI
- [ ] Complex functions have docstrings
- [ ] README updated if needed

### Review
- [ ] Pull request created
- [ ] Code review approved
- [ ] CI checks pass
- [ ] Merged to main

---

*Ready for Sprint Planning*
