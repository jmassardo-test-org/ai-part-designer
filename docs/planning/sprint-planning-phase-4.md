# Sprint Planning: Phase 4 - Feature Completion

**Date:** January 25, 2026  
**Author:** Development Team  
**Status:** Planning  
**Duration:** 9 weeks (Sprints 36-43)  

---

## Overview

This document provides detailed sprint planning for completing the remaining features identified in the product gap analysis. Each sprint includes specific tasks, acceptance criteria, and implementation guidance.

**🔴 IMPORTANT:** Sprint 36 is dedicated to critical bug fixes that are blocking users. These must be completed before any new feature work.

---

## Sprint 36: Critical Bug Fixes & Core Functionality 🔴 BLOCKER

**Duration:** 1 week  
**Goal:** Fix all broken dashboard links, templates, and core user workflows  
**Total Points:** 44  
**Priority:** 🔴 MUST COMPLETE BEFORE OTHER WORK  

---

### Epic: Dashboard Fixes (13 points)

#### Task 36.1: Fix Recent Designs on Dashboard (5 points)
**Priority:** P0 - Blocker  
**Assignee:** Frontend Developer  

**Problem:**  
Dashboard "Recent Designs" shows static/mock data instead of user's actual designs, causing errors.

**File:** `frontend/src/pages/DashboardPage.tsx` (or similar)

**Fix Required:**
```typescript
// Replace static data with API call
const { data: designs, isLoading, error } = useQuery({
  queryKey: ['designs', 'recent'],
  queryFn: () => designsApi.getRecent({ limit: 6 }),
});

// Handle loading and empty states
if (isLoading) return <DesignsSkeleton />;
if (!designs?.length) return <EmptyDesignsState />;
```

**Acceptance Criteria:**
- [ ] Dashboard fetches actual user designs from API
- [ ] Shows loading skeleton while fetching
- [ ] Shows empty state if no designs exist
- [ ] Each design card links to correct design detail page
- [ ] No console errors

---

#### Task 36.2: Fix Projects Page Filter Error (3 points)
**Priority:** P0 - Blocker  
**Assignee:** Frontend Developer  

**Problem:**  
`TypeError: projects.filter is not a function` - The API returns data in unexpected format or projects state is not initialized as array.

**File:** `frontend/src/pages/ProjectsPage.tsx`

**Fix Required:**
```typescript
// Ensure projects is always an array
const [projects, setProjects] = useState<Project[]>([]);

// When fetching, handle response structure
const response = await projectsApi.list();
const projectsList = Array.isArray(response) ? response : response.data ?? [];
setProjects(projectsList);

// Or use optional chaining with fallback
const filteredProjects = (projects ?? []).filter(p => ...);
```

**Acceptance Criteria:**
- [ ] Projects page loads without errors
- [ ] Projects list displays correctly (or empty state)
- [ ] Filtering works when projects exist
- [ ] API response format documented

---

#### Task 36.3: Fix File Upload Functionality (5 points)
**Priority:** P0 - Blocker  
**Assignee:** Full Stack Developer  

**Problem:**  
File upload doesn't work - need to investigate if frontend, backend, or storage issue.

**Investigation Steps:**
1. Check browser network tab for API errors
2. Verify backend `/api/v1/files/upload` endpoint works
3. Check MinIO/S3 storage connection
4. Verify file size limits and CORS settings

**Fix Required:**
```typescript
// Ensure proper FormData and headers
const uploadFile = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post('/files/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => setProgress(e.progress ?? 0),
  });
  return response.data;
};
```

**Acceptance Criteria:**
- [ ] Can upload STEP files
- [ ] Can upload STL files
- [ ] Can upload PDF files
- [ ] Upload progress indicator works
- [ ] Error messages shown on failure
- [ ] Uploaded files appear in file list

---

### Epic: Template System (13 points)

#### Task 36.4: Create Seed Templates (3 points)
**Priority:** P0 - Blocker  
**Assignee:** Backend Developer  

**Problem:**  
No templates available for users to browse.

**Solution:**  
Create seed data with starter templates.

**File:** `backend/app/seeds/templates.py`

```python
SEED_TEMPLATES = [
    {
        "name": "Simple Box",
        "description": "Basic rectangular enclosure with lid",
        "category": "enclosures",
        "parameters": {
            "length": {"type": "number", "default": 100, "min": 20, "max": 500},
            "width": {"type": "number", "default": 80, "min": 20, "max": 500},
            "height": {"type": "number", "default": 40, "min": 10, "max": 300},
            "wall_thickness": {"type": "number", "default": 2, "min": 1, "max": 10},
        },
        "is_public": True,
        "is_system": True,
    },
    {
        "name": "Raspberry Pi 4 Case",
        "description": "Enclosure sized for Raspberry Pi 4",
        "category": "electronics",
        # ... more templates
    },
    # Add 8-10 starter templates
]
```

**Acceptance Criteria:**
- [ ] At least 10 seed templates created
- [ ] Templates cover common use cases (boxes, brackets, mounts)
- [ ] Seed script runs on database migration
- [ ] Templates visible in template browser

---

#### Task 36.5: Implement "Save as Template" (5 points)
**Priority:** P0 - Blocker  
**Assignee:** Full Stack Developer  

**Problem:**  
No way for users to create their own templates from designs.

**Backend Endpoint:**
```python
@router.post("/templates/from-design/{design_id}")
async def create_template_from_design(
    design_id: UUID,
    name: str = Body(...),
    description: str = Body(""),
    category: str = Body("custom"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a template from an existing design."""
    design = await get_design_or_404(db, design_id, current_user)
    
    template = Template(
        name=name,
        description=description,
        category=category,
        user_id=current_user.id,
        base_design_id=design.id,
        parameters=extract_parameters(design),
        is_public=False,
    )
    db.add(template)
    await db.commit()
    return template
```

**Frontend:**
```typescript
// Add to design actions menu
<DropdownMenuItem onClick={() => setShowTemplateDialog(true)}>
  <Template className="mr-2 h-4 w-4" />
  Save as Template
</DropdownMenuItem>

// Template creation dialog
<SaveAsTemplateDialog
  designId={design.id}
  onSave={handleSaveTemplate}
/>
```

**Acceptance Criteria:**
- [ ] "Save as Template" option in design menu
- [ ] Dialog to enter template name/description
- [ ] Template appears in user's template library
- [ ] Template can be used to create new designs

---

#### Task 36.6: Template Creation UI in Dashboard (5 points)
**Priority:** P0 - Blocker  
**Assignee:** Frontend Developer  

**Problem:**  
Templates section in dashboard doesn't work; needs proper UI.

**File:** `frontend/src/pages/TemplatesPage.tsx`

**Implementation:**
```typescript
export function TemplatesPage() {
  const { data: templates, isLoading } = useQuery({
    queryKey: ['templates'],
    queryFn: templatesApi.list,
  });
  
  const systemTemplates = templates?.filter(t => t.is_system) ?? [];
  const userTemplates = templates?.filter(t => !t.is_system) ?? [];
  
  return (
    <div className="space-y-8">
      <section>
        <h2>Starter Templates</h2>
        <TemplateGrid templates={systemTemplates} />
      </section>
      
      <section>
        <h2>My Templates</h2>
        {userTemplates.length === 0 ? (
          <EmptyState message="Create templates from your designs" />
        ) : (
          <TemplateGrid templates={userTemplates} />
        )}
      </section>
    </div>
  );
}
```

**Acceptance Criteria:**
- [ ] Templates page loads without errors
- [ ] System templates shown in separate section
- [ ] User templates shown (or empty state)
- [ ] Each template card shows preview and "Use Template" action
- [ ] Create template button for users with existing designs

---

### Epic: Chat Save Functionality (8 points)

#### Task 36.7: Add Save Button to Chat Interface (3 points)
**Priority:** P0 - Blocker  
**Assignee:** Frontend Developer  

**Problem:**  
Users can only download designs from chat, not save them to their library.

**File:** `frontend/src/components/generation/ChatMessageBubble.tsx`

**Implementation:**
```typescript
// In the assistant message with generated design
{message.generationId && (
  <div className="flex gap-2 mt-3">
    <Button
      variant="primary"
      onClick={() => handleSaveDesign(message.generationId)}
    >
      <Save className="mr-2 h-4 w-4" />
      Save to My Designs
    </Button>
    <Button
      variant="outline"
      onClick={() => handleDownload(message.generationId)}
    >
      <Download className="mr-2 h-4 w-4" />
      Download
    </Button>
  </div>
)}
```

**Acceptance Criteria:**
- [ ] "Save to My Designs" button visible after generation
- [ ] Button is prominent (primary styling)
- [ ] Download button still available as secondary option

---

#### Task 36.8: Implement Save Design API Integration (5 points)
**Priority:** P0 - Blocker  
**Assignee:** Full Stack Developer  

**Problem:**  
Generated designs need to be saved to user's design library.

**Backend Endpoint (if needed):**
```python
@router.post("/designs/{design_id}/save")
async def save_design_to_library(
    design_id: UUID,
    name: Optional[str] = Body(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save a generated design to user's library."""
    design = await get_design_or_404(db, design_id)
    
    # If design is temporary/session-based, make it permanent
    design.is_saved = True
    design.user_id = current_user.id
    design.name = name or design.name or f"Design {design.id[:8]}"
    design.saved_at = datetime.utcnow()
    
    await db.commit()
    return {"message": "Design saved", "design_id": str(design.id)}
```

**Frontend Integration:**
```typescript
const handleSaveDesign = async (designId: string) => {
  try {
    const name = await promptForName(); // Optional name dialog
    await designsApi.save(designId, { name });
    toast.success('Design saved to your library!');
  } catch (error) {
    toast.error('Failed to save design');
  }
};
```

**Acceptance Criteria:**
- [ ] Clicking "Save" persists design to user's library
- [ ] Optional: Prompt for design name before saving
- [ ] Success toast shown
- [ ] Design appears in "My Designs" / "Recent Designs"
- [ ] Saved design can be found and opened later

---

### Epic: Sharing Page (10 points)

#### Task 36.9: Implement Basic Sharing UI (5 points)
**Priority:** P1  
**Assignee:** Frontend Developer  

**Problem:**  
Sharing page has no implementation.

**File:** `frontend/src/pages/SharingPage.tsx`

**Implementation:**
```typescript
export function SharingPage() {
  const { data: sharedDesigns } = useQuery({
    queryKey: ['shared-designs'],
    queryFn: sharingApi.getSharedWithMe,
  });
  
  const { data: myShares } = useQuery({
    queryKey: ['my-shares'],
    queryFn: sharingApi.getMyShares,
  });
  
  return (
    <div className="space-y-8">
      <section>
        <h2>Shared With Me</h2>
        {sharedDesigns?.length === 0 ? (
          <EmptyState message="No designs have been shared with you yet" />
        ) : (
          <DesignGrid designs={sharedDesigns} />
        )}
      </section>
      
      <section>
        <h2>My Shared Designs</h2>
        {myShares?.length === 0 ? (
          <EmptyState message="You haven't shared any designs" />
        ) : (
          <SharedDesignsList shares={myShares} />
        )}
      </section>
    </div>
  );
}
```

**Acceptance Criteria:**
- [ ] Sharing page loads without errors
- [ ] "Shared With Me" section shows designs others shared
- [ ] "My Shares" section shows designs user has shared
- [ ] Empty states for both sections

---

#### Task 36.10: Connect Sharing UI to Backend APIs (5 points)
**Priority:** P1  
**Assignee:** Full Stack Developer  

**Problem:**  
Sharing backend APIs exist but aren't connected to UI.

**API Integration:**
```typescript
// frontend/src/api/sharing.ts
export const sharingApi = {
  getSharedWithMe: () => 
    api.get('/shares/with-me').then(r => r.data),
    
  getMyShares: () => 
    api.get('/shares/my-shares').then(r => r.data),
    
  shareDesign: (designId: string, email: string, permission: 'view' | 'edit') =>
    api.post(`/designs/${designId}/share`, { email, permission }),
    
  revokeShare: (shareId: string) =>
    api.delete(`/shares/${shareId}`),
};
```

**Add share dialog to design page:**
```typescript
<ShareDesignDialog
  designId={design.id}
  onShare={handleShare}
/>
```

**Acceptance Criteria:**
- [ ] Can share design via email
- [ ] Shared users appear in share list
- [ ] Can revoke shares
- [ ] Permission levels (view/edit) work

---

## Sprint 37-38: Chat UI Foundation & Component Management

**Duration:** 2 weeks  
**Goal:** Establish chat-style generation UI pattern and enable component refinement  
**Total Points:** 45  

---

### Epic 0: Chat-Style Generation UI (8 points) ⭐ FOUNDATION

> **Why First?** This epic establishes the conversational UI pattern that will be reused across many other features (component refinement, enclosure customization, AI extraction review). Building it first creates a foundation for iterative user interactions.

#### Task 0.1: Prompt History & Chat Interface (5 points)
**Priority:** P0 - Launch Blocker  
**Assignee:** Frontend Developer  

**Description:**  
After the first generation, transform the UI from static example prompts to a chat-like interface with scrollable prompt/response history.

**File:** `frontend/src/components/generation/GenerationChat.tsx`

```typescript
import { useState, useRef, useEffect } from 'react';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  generationId?: string; // Links to generated design
  thumbnailUrl?: string;
}

export function GenerationChat({ designId }: { designId: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [prompt, setPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const hasGenerated = messages.length > 0;

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async () => {
    if (!prompt.trim() || isGenerating) return;
    
    // Add user message
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: prompt,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);
    setPrompt('');
    setIsGenerating(true);
    
    try {
      const result = await generateDesign(designId, prompt);
      
      // Add assistant response
      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `Generated design based on: "${prompt}"`,
        timestamp: new Date(),
        generationId: result.id,
        thumbnailUrl: result.thumbnailUrl,
      };
      setMessages(prev => [...prev, assistantMessage]);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Scrollable message history */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!hasGenerated && <ExamplePrompts onSelect={setPrompt} />}
        
        {messages.map(msg => (
          <ChatMessageBubble key={msg.id} message={msg} />
        ))}
        
        {isGenerating && <GeneratingIndicator />}
        <div ref={messagesEndRef} />
      </div>
      
      {/* Fixed input at bottom */}
      <div className="border-t p-4">
        <div className="flex gap-2">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={hasGenerated 
              ? "Describe changes to your design..." 
              : "Describe what you want to create..."
            }
            className="flex-1 resize-none rounded-lg border p-3"
            rows={2}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
          />
          <button
            onClick={handleSubmit}
            disabled={!prompt.trim() || isGenerating}
            className="px-6 py-2 bg-primary text-white rounded-lg"
          >
            {hasGenerated ? 'Regenerate' : 'Generate'}
          </button>
        </div>
      </div>
    </div>
  );
}
```

**Acceptance Criteria:**
- [ ] Example prompts visible before first generation
- [ ] Example prompts hidden after first generation
- [ ] Chat messages appear with user/assistant styling
- [ ] Messages scroll automatically to show newest
- [ ] Button text changes from "Generate" to "Regenerate"
- [ ] Input placeholder changes after first generation
- [ ] Keyboard shortcut (Enter) submits prompt

---

#### Task 0.2: Example Prompts Component (2 points)
**Priority:** P0  
**Assignee:** Frontend Developer  

**Description:**  
Show example prompts only before first generation, then hide them.

**File:** `frontend/src/components/generation/ExamplePrompts.tsx`

```typescript
interface ExamplePromptsProps {
  onSelect: (prompt: string) => void;
}

const EXAMPLE_PROMPTS = [
  "Create a simple enclosure for a Raspberry Pi 4",
  "Design a wall-mountable box for an Arduino with an LCD screen",
  "Generate a ventilated case for a 3D printer control board",
  "Make a rugged enclosure for outdoor electronics",
];

export function ExamplePrompts({ onSelect }: ExamplePromptsProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-gray-700">
        Not sure where to start? Try one of these:
      </h3>
      <div className="grid gap-3">
        {EXAMPLE_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            onClick={() => onSelect(prompt)}
            className="text-left p-4 rounded-lg border hover:border-primary
                       hover:bg-primary/5 transition-colors"
          >
            "{prompt}"
          </button>
        ))}
      </div>
    </div>
  );
}
```

---

#### Task 0.3: Chat Message Bubble & Thumbnails (1 point)
**Priority:** P0  
**Assignee:** Frontend Developer  

**File:** `frontend/src/components/generation/ChatMessageBubble.tsx`

```typescript
export function ChatMessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-lg p-4 ${
          isUser
            ? 'bg-primary text-white'
            : 'bg-gray-100 text-gray-900'
        }`}
      >
        <p>{message.content}</p>
        
        {message.thumbnailUrl && (
          <img
            src={message.thumbnailUrl}
            alt="Generated design"
            className="mt-3 rounded-lg max-w-full"
          />
        )}
        
        {message.generationId && (
          <Link
            to={`/designs/${message.generationId}`}
            className="mt-2 text-sm underline block"
          >
            View full design →
          </Link>
        )}
        
        <span className="text-xs opacity-70 mt-2 block">
          {format(message.timestamp, 'h:mm a')}
        </span>
      </div>
    </div>
  );
}
```

---

### Epic 1: Component CAD File Updates (11 points)

#### Task 1.1: Component File Replacement API (5 points)
**Priority:** P0 - Launch Blocker  
**Assignee:** Backend Developer  

**Description:**  
Add endpoint to replace the CAD/datasheet files attached to an existing reference component without creating a new component.

**Implementation:**

```python
# backend/app/api/v1/components.py

@router.put("/{component_id}/files")
async def replace_component_files(
    component_id: UUID,
    cad_file: Optional[UploadFile] = File(None),
    datasheet_file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Replace CAD or datasheet files for an existing component."""
    # 1. Verify component ownership
    # 2. Validate uploaded files
    # 3. Store new files, archive old ones
    # 4. Update component record with new file references
    # 5. Optionally trigger re-extraction
```

**API Contract:**
```
PUT /api/v1/components/{component_id}/files
Content-Type: multipart/form-data

Form Fields:
- cad_file: (optional) New STEP/STL file
- datasheet_file: (optional) New PDF datasheet
- trigger_extraction: boolean (default: true)

Response: ComponentResponse with updated file URLs
```

**Acceptance Criteria:**
- [ ] Can upload new CAD file for existing component
- [ ] Can upload new datasheet for existing component
- [ ] Old files are archived (not deleted) for version history
- [ ] File validation (type, size) applied
- [ ] Returns updated component with new file URLs
- [ ] Audit log entry created

**Test Cases:**
```python
async def test_replace_cad_file():
    # Create component with initial CAD file
    # Upload replacement CAD file
    # Verify old file archived
    # Verify new file accessible
    # Verify component references updated

async def test_replace_datasheet_triggers_extraction():
    # Create component
    # Replace datasheet with trigger_extraction=true
    # Verify extraction job created
```

---

#### Task 1.2: Re-trigger Extraction on File Update (3 points)
**Priority:** P0  
**Assignee:** Backend Developer  

**Description:**  
When a CAD or datasheet file is updated, optionally re-run the AI dimension extraction.

**Implementation:**
- Modify `ComponentStorageService.update_files()` to accept `trigger_extraction` flag
- Queue new extraction job if flag is true
- Update component `extraction_status` to "pending"

**Acceptance Criteria:**
- [ ] Extraction can be triggered on file update
- [ ] Previous extraction results preserved until new extraction completes
- [ ] User notified when extraction completes

---

#### Task 1.3: Component File History UI (3 points)
**Priority:** P1  
**Assignee:** Frontend Developer  

**Description:**  
Add UI to view file history and upload replacement files.

**UI Components:**
- "Update Files" button on component detail page
- File upload modal with drag-drop
- File history accordion showing previous versions
- "Restore" button to revert to previous version

**Acceptance Criteria:**
- [ ] Can access file update from component detail page
- [ ] Drag-drop file upload works
- [ ] File history shows timestamps and file names
- [ ] Can restore previous file version

---

### Epic 2: File Alignment & CAD Combination (21 points)

#### Task 2.1: Alignment Service (8 points)
**Priority:** P1  
**Assignee:** Backend Developer  

**Description:**  
Create service to align multiple CAD files relative to each other.

**File:** `backend/app/cad/alignment.py`

```python
from enum import Enum
from dataclasses import dataclass
import cadquery as cq

class AlignmentMode(str, Enum):
    FACE_COPLANAR = "face"      # Align faces to be coplanar
    EDGE_PARALLEL = "edge"       # Align edges to be parallel
    CENTER_ALIGN = "center"      # Align bounding box centers
    ORIGIN_ALIGN = "origin"      # Align origins

@dataclass
class AlignmentConfig:
    mode: AlignmentMode
    source_file_id: UUID
    target_file_id: UUID
    source_reference: Optional[str] = None  # Face/edge selector
    target_reference: Optional[str] = None
    offset: tuple[float, float, float] = (0, 0, 0)

class CADAlignmentService:
    """Service for aligning multiple CAD files."""
    
    async def align_files(
        self,
        base_shape: cq.Workplane,
        align_shape: cq.Workplane,
        config: AlignmentConfig,
    ) -> cq.Workplane:
        """Align align_shape relative to base_shape."""
        
    async def compute_transformation(
        self,
        config: AlignmentConfig,
    ) -> tuple[tuple, tuple]:
        """Compute translation and rotation for alignment."""
        
    async def preview_alignment(
        self,
        file_ids: list[UUID],
        configs: list[AlignmentConfig],
    ) -> bytes:
        """Generate preview mesh of aligned assembly."""
```

**Alignment Modes:**

| Mode | Description | Use Case |
|------|-------------|----------|
| face | Make two faces coplanar | Mount component to enclosure floor |
| edge | Align edges parallel | Line up connectors |
| center | Align bounding box centers | Center component in enclosure |
| origin | Align coordinate origins | Precise CAD positioning |

**Acceptance Criteria:**
- [ ] All 4 alignment modes implemented
- [ ] Works with STEP and STL files
- [ ] Supports offset after alignment
- [ ] Returns transformation matrix
- [ ] Handles invalid geometry gracefully

---

#### Task 2.2: Alignment API Endpoint (5 points)
**Priority:** P1  
**Assignee:** Backend Developer  

**File:** `backend/app/api/v1/cad_operations.py`

**Endpoints:**
```
POST /api/v1/cad/align
{
    "base_file_id": "uuid",
    "files": [
        {
            "file_id": "uuid",
            "alignment": {
                "mode": "center",
                "offset": [0, 0, 10]
            }
        }
    ],
    "output_format": "step",
    "save_as_assembly": true,
    "assembly_name": "My Assembly"
}

Response:
{
    "assembly_id": "uuid",
    "preview_url": "/api/v1/assemblies/{id}/preview",
    "download_url": "/api/v1/assemblies/{id}/download"
}
```

```
POST /api/v1/cad/align/preview
{
    "base_file_id": "uuid",
    "files": [...],
    "viewport": {"width": 800, "height": 600}
}

Response:
{
    "preview_image": "base64...",
    "bounding_box": {...}
}
```

**Acceptance Criteria:**
- [ ] Align 2+ files with specified configurations
- [ ] Generate preview without saving
- [ ] Save result as assembly or merged file
- [ ] Export aligned result in multiple formats

---

#### Task 2.3: Frontend Alignment Editor (8 points)
**Priority:** P1  
**Assignee:** Frontend Developer  

**File:** `frontend/src/components/alignment/AlignmentEditor.tsx`

**UI Features:**
- Split view: File list + 3D preview
- Drag files from list to 3D scene
- Transform controls (translate, rotate)
- Alignment mode selector
- Snap-to-grid toggle
- Preset buttons (stack, side-by-side, center)

**Component Structure:**
```tsx
<AlignmentEditor
  baseFileId={string}
  availableFiles={FileInfo[]}
  onSave={(config: AlignmentConfig[]) => void}
  onCancel={() => void}
/>
  <AlignmentToolbar />
  <AlignmentFilePicker />
  <AlignmentCanvas3D />
  <AlignmentPropertiesPanel />
</AlignmentEditor>
```

**Three.js Integration:**
- Use TransformControls for manipulation
- Show bounding boxes during drag
- Highlight snap points
- Display dimension overlays

**Acceptance Criteria:**
- [ ] 3D preview updates in real-time
- [ ] Transform controls for translate/rotate
- [ ] Alignment presets work correctly
- [ ] Can save alignment as assembly
- [ ] Keyboard shortcuts (R=rotate, T=translate)

---

### Epic 3: Assembly Management (5 points)

#### Task 3.1: Assembly Model & Storage (3 points)
**Priority:** P2  
**Assignee:** Backend Developer  

**Model:**
```python
# backend/app/models/assembly.py

class Assembly(Base):
    __tablename__ = "assemblies"
    
    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, ForeignKey("users.id"))
    project_id = Column(UUID, ForeignKey("projects.id"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Stored alignment configuration
    components = Column(JSONB, nullable=False)  # List of {file_id, transform}
    
    # Generated outputs
    merged_step_url = Column(String(500), nullable=True)
    merged_stl_url = Column(String(500), nullable=True)
    preview_url = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
```

**Acceptance Criteria:**
- [ ] Store assembly with component transforms
- [ ] Track source files with relationships
- [ ] Support assembly versioning

---

#### Task 3.2: Assembly CRUD API (2 points)
**Priority:** P2  

**Endpoints:**
```
GET    /api/v1/assemblies              # List user's assemblies
POST   /api/v1/assemblies              # Create from alignment result
GET    /api/v1/assemblies/{id}         # Get assembly details
PUT    /api/v1/assemblies/{id}         # Update assembly
DELETE /api/v1/assemblies/{id}         # Delete assembly
GET    /api/v1/assemblies/{id}/export  # Export merged file
```

---

## Sprint 38-39: AI Extraction & Enclosure Enhancements

**Duration:** 2 weeks  
**Goal:** Complete AI vision capabilities and expand enclosure options  
**Total Points:** 39  

---

### Epic 4: GPT-4 Vision PDF Extraction (16 points)

#### Task 4.1: GPT-4 Vision Integration (8 points)
**Priority:** P0 - Launch Blocker  
**Assignee:** AI/ML Developer  

**File:** `backend/app/services/vision_extractor.py`

```python
import base64
from openai import AsyncOpenAI

class VisionExtractionService:
    """Extract dimensions from images using GPT-4 Vision."""
    
    def __init__(self):
        self.client = AsyncOpenAI()
        self.model = "gpt-4-vision-preview"
    
    async def extract_from_image(
        self,
        image_data: bytes,
        context: str = "",
    ) -> ExtractionResult:
        """Extract mechanical dimensions from an image."""
        
        base64_image = base64.standard_b64encode(image_data).decode()
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": DIMENSION_EXTRACTION_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Extract all mechanical dimensions from this technical drawing. {context}",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}",
                                "detail": "high",
                            },
                        },
                    ],
                },
            ],
            max_tokens=4096,
        )
        
        return self._parse_extraction_response(response)

DIMENSION_EXTRACTION_SYSTEM_PROMPT = """
You are an expert mechanical engineer analyzing technical drawings.
Extract ALL dimensional information including:

1. Overall dimensions (length, width, height) in millimeters
2. Mounting hole positions (X, Y coordinates from origin)
3. Mounting hole diameters and thread sizes (M2, M2.5, M3, etc.)
4. Connector/port locations and cutout dimensions
5. Clearance zones and keep-out areas
6. Component thickness

Return structured JSON:
{
    "dimensions": {"length": float, "width": float, "height": float, "unit": "mm"},
    "mounting_holes": [{"x": float, "y": float, "diameter": float, "thread": "M3"}],
    "connectors": [{"name": "USB-C", "x": float, "y": float, "width": float, "height": float}],
    "confidence": float (0-1)
}
"""
```

**Acceptance Criteria:**
- [ ] Extracts overall dimensions with >90% accuracy on clear drawings
- [ ] Identifies mounting holes with positions
- [ ] Detects connector locations
- [ ] Returns confidence scores
- [ ] Handles multi-page PDFs

---

#### Task 4.2: PDF to Image Pipeline (3 points)
**Priority:** P0  
**Assignee:** Backend Developer  

**Dependencies:** `pdf2image`, `Pillow`

```python
# backend/app/services/pdf_processor.py

from pdf2image import convert_from_bytes
from PIL import Image

class PDFProcessor:
    """Convert PDF pages to images for vision analysis."""
    
    async def convert_pdf_to_images(
        self,
        pdf_bytes: bytes,
        dpi: int = 300,
        max_pages: int = 10,
    ) -> list[bytes]:
        """Convert PDF to list of PNG images."""
        
        images = convert_from_bytes(
            pdf_bytes,
            dpi=dpi,
            first_page=1,
            last_page=max_pages,
        )
        
        result = []
        for img in images:
            buffer = io.BytesIO()
            img.save(buffer, format="PNG", optimize=True)
            result.append(buffer.getvalue())
        
        return result
    
    async def find_mechanical_drawing_pages(
        self,
        pdf_bytes: bytes,
    ) -> list[int]:
        """Identify which pages contain mechanical drawings."""
        # Heuristics: look for dimension lines, technical formatting
```

**Acceptance Criteria:**
- [ ] Converts PDF pages to high-resolution PNGs
- [ ] Handles multi-page PDFs
- [ ] Identifies mechanical drawing pages
- [ ] Optimizes image size for API limits

---

#### Task 4.3: Extraction Review UI (5 points)
**Priority:** P1  
**Assignee:** Frontend Developer  

**File:** `frontend/src/components/extraction/ExtractionReview.tsx`

**UI Features:**
- PDF page viewer with zoom/pan
- Overlay showing extracted dimensions as annotations
- Click-to-edit for extracted values
- Confidence indicator per extraction
- "Re-analyze" button for specific regions
- Side-by-side comparison with component specs

**Acceptance Criteria:**
- [ ] Shows PDF with dimension overlays
- [ ] Can edit extracted values inline
- [ ] Confidence scores displayed
- [ ] Can mark extractions as verified
- [ ] Saves corrections back to component

---

### Epic 5: Enclosure Style Templates (14 points)

#### Task 5.1: Additional Style Implementations (8 points)
**Priority:** P1  
**Assignee:** CAD Developer  

**File:** `backend/app/cad/enclosure_styles.py`

**New Styles:**

```python
class EnclosureStyleTemplate(str, Enum):
    MINIMAL = "minimal"      # Existing: thin walls, simple box
    TOP_LID = "top_lid"      # Existing: standard lid on top
    CLAMSHELL = "clamshell"  # Existing: two halves
    
    # NEW STYLES
    RUGGED = "rugged"        # Thick walls, rounded corners, gasket groove
    STACKABLE = "stackable"  # Interlocking edges, alignment pins
    INDUSTRIAL = "industrial"  # DIN rail compatible, terminal cutouts
    DESKTOP = "desktop"      # Angled front panel, anti-slip feet
    HANDHELD = "handheld"    # Ergonomic curves, battery compartment

@dataclass
class RuggedStyleConfig:
    wall_thickness: float = 4.0  # Thicker walls
    corner_radius: float = 8.0   # Rounded corners
    gasket_groove: bool = True
    ip_rating: str = "IP65"
    screw_size: str = "M4"       # Larger screws

@dataclass  
class StackableStyleConfig:
    interlock_depth: float = 3.0
    alignment_pin_diameter: float = 4.0
    max_stack: int = 5

@dataclass
class IndustrialStyleConfig:
    din_rail_width: int = 35     # Standard DIN rail
    terminal_cutouts: int = 4
    cable_gland_size: str = "PG9"
```

**Acceptance Criteria:**
- [ ] 5 new style templates implemented
- [ ] Each style has configurable parameters
- [ ] Styles generate valid, printable geometry
- [ ] Preview images for style selection

---

#### Task 5.2: Style Selection UI (3 points)
**Priority:** P1  
**Assignee:** Frontend Developer  

**File:** `frontend/src/components/enclosure/StyleSelector.tsx`

- Grid of style cards with preview images
- Hover shows style description
- Click selects and shows parameter form
- Live 3D preview updates with style change

---

#### Task 5.3: Style Parameter Customization (3 points)
**Priority:** P2  
**Assignee:** Frontend Developer  

- Slider controls for numeric parameters
- Toggle switches for boolean options
- Real-time preview updates
- "Save as Custom Style" for Pro users

---

### Epic 6: Mounting Type Expansion (9 points)

#### Task 6.1: Additional Mounting Generators (6 points)
**Priority:** P1  
**Assignee:** CAD Developer  

**File:** `backend/app/cad/mounting.py`

```python
class MountingType(str, Enum):
    STANDOFF = "standoff"        # Existing
    SCREW_BOSS = "screw_boss"    # Existing
    
    # NEW
    SNAP_FIT = "snap_fit"        # Tool-less clips
    DIN_RAIL = "din_rail"        # 35mm industrial rail
    WALL_BRACKET = "wall_bracket"  # Keyhole slots
    ADHESIVE_PAD = "adhesive_pad"  # 3M VHB mounting
    CABLE_TIE = "cable_tie"      # Wire management anchors
    HEAT_SET = "heat_set"        # Heat-set insert holes

class MountingGenerator:
    def generate_snap_fit(
        self,
        wall: cq.Workplane,
        position: tuple[float, float],
        clip_height: float = 5.0,
        deflection: float = 1.5,
    ) -> cq.Workplane:
        """Generate snap-fit clip on wall."""
        
    def generate_din_rail_mount(
        self,
        base: cq.Workplane,
        rail_width: int = 35,
    ) -> cq.Workplane:
        """Generate DIN rail mounting bracket."""
        
    def generate_heat_set_boss(
        self,
        base: cq.Workplane,
        position: tuple[float, float],
        insert_size: str = "M3",  # M2, M2.5, M3, M4
    ) -> cq.Workplane:
        """Generate boss for heat-set insert."""
```

**Heat-Set Insert Dimensions:**
| Insert | Hole Diameter | Boss OD | Depth |
|--------|--------------|---------|-------|
| M2 | 3.2mm | 5.5mm | 4.0mm |
| M2.5 | 3.8mm | 6.0mm | 5.0mm |
| M3 | 4.5mm | 7.0mm | 5.5mm |
| M4 | 5.6mm | 9.0mm | 7.0mm |

**Acceptance Criteria:**
- [ ] All 6 new mounting types implemented
- [ ] Parameters configurable per mount
- [ ] Geometry is printable (no overhangs >45°)
- [ ] Mounting features integrate with enclosure walls

---

#### Task 6.2: Mounting Selection UI (3 points)
**Priority:** P1  
**Assignee:** Frontend Developer  

- Per-component mounting type dropdown
- Visual preview of mounting options
- Parameter form based on selected type

---

## Sprint 40-41: Monetization & Authentication

**Duration:** 2 weeks  
**Goal:** Enable revenue generation and expand authentication options  
**Total Points:** 46  

---

### Epic 7: Stripe Payment Integration (28 points)

#### Task 7.1: Stripe SDK Setup (5 points)
**Priority:** P0 - Launch Blocker  
**Assignee:** Backend Developer  

**Dependencies:** `stripe`

**File:** `backend/app/services/payments.py`

```python
import stripe
from app.core.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

class PaymentService:
    """Handle Stripe payment operations."""
    
    async def create_customer(self, user: User) -> str:
        """Create Stripe customer for user."""
        customer = stripe.Customer.create(
            email=user.email,
            name=user.display_name,
            metadata={"user_id": str(user.id)},
        )
        return customer.id
    
    async def create_checkout_session(
        self,
        user: User,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Create Stripe Checkout session."""
        session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return session.url
    
    async def handle_webhook(self, payload: bytes, signature: str):
        """Process Stripe webhook events."""
        event = stripe.Webhook.construct_event(
            payload, signature, settings.STRIPE_WEBHOOK_SECRET
        )
        
        if event.type == "checkout.session.completed":
            await self._handle_checkout_complete(event.data.object)
        elif event.type == "customer.subscription.updated":
            await self._handle_subscription_update(event.data.object)
        elif event.type == "customer.subscription.deleted":
            await self._handle_subscription_cancel(event.data.object)
```

**Environment Variables:**
```
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PRO_MONTHLY=price_...
STRIPE_PRICE_PRO_YEARLY=price_...
STRIPE_PRICE_ENTERPRISE_MONTHLY=price_...
```

**Acceptance Criteria:**
- [ ] Stripe SDK configured with test keys
- [ ] Customer creation on user signup
- [ ] Webhook endpoint receiving events
- [ ] Event signature verification

---

#### Task 7.2: Subscription Models (5 points)
**Priority:** P0  
**Assignee:** Backend Developer  

**File:** `backend/app/models/subscription.py`

```python
class SubscriptionTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, ForeignKey("users.id"), unique=True)
    
    tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.FREE)
    stripe_subscription_id = Column(String(100), nullable=True)
    stripe_customer_id = Column(String(100), nullable=True)
    
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    
    status = Column(String(50), default="active")  # active, past_due, canceled
```

**Tier Limits:**
```python
TIER_LIMITS = {
    SubscriptionTier.FREE: {
        "generations_per_month": 10,
        "storage_mb": 100,
        "max_components": 5,
        "priority_queue": False,
        "api_access": False,
        "export_formats": ["stl"],
    },
    SubscriptionTier.PRO: {
        "generations_per_month": 100,
        "storage_mb": 5000,
        "max_components": 50,
        "priority_queue": True,
        "api_access": False,
        "export_formats": ["stl", "step", "3mf"],
    },
    SubscriptionTier.ENTERPRISE: {
        "generations_per_month": -1,  # Unlimited
        "storage_mb": 50000,
        "max_components": -1,
        "priority_queue": True,
        "api_access": True,
        "export_formats": ["stl", "step", "3mf", "obj"],
    },
}
```

---

#### Task 7.3: Checkout & Upgrade Flow UI (8 points)
**Priority:** P0  
**Assignee:** Frontend Developer  

**Files:**
- `frontend/src/pages/PricingPage.tsx`
- `frontend/src/components/billing/UpgradeModal.tsx`
- `frontend/src/components/billing/PlanCard.tsx`

**Pricing Page Features:**
- Tier comparison table
- Monthly/yearly toggle (yearly = 2 months free)
- Feature checkmarks per tier
- "Current Plan" indicator
- "Upgrade" / "Downgrade" buttons
- FAQ section

**Upgrade Modal:**
- Selected plan summary
- Payment method selection
- Proration preview
- Terms acceptance checkbox
- Stripe Elements for card input

**Acceptance Criteria:**
- [ ] Pricing page with 3 tiers displayed
- [ ] Can initiate checkout for Pro/Enterprise
- [ ] Redirects to Stripe Checkout
- [ ] Success/cancel URL handling
- [ ] Shows current subscription status

---

#### Task 7.4: Billing Portal (5 points)
**Priority:** P1  
**Assignee:** Backend + Frontend  

**Backend:**
```python
@router.post("/billing/portal")
async def create_billing_portal_session(
    current_user: User = Depends(get_current_user),
):
    """Create Stripe Customer Portal session."""
    session = stripe.billing_portal.Session.create(
        customer=current_user.stripe_customer_id,
        return_url=f"{settings.FRONTEND_URL}/settings/billing",
    )
    return {"url": session.url}
```

**Frontend:**
- "Manage Billing" button in Settings
- Redirects to Stripe Customer Portal
- Portal handles: update payment, cancel, invoices

---

#### Task 7.5: Tier Enforcement Middleware (5 points)
**Priority:** P0  
**Assignee:** Backend Developer  

**File:** `backend/app/middleware/tier_enforcement.py`

```python
from fastapi import Request, HTTPException
from app.models.subscription import TIER_LIMITS

class TierEnforcementMiddleware:
    """Enforce subscription tier limits on API endpoints."""
    
    async def check_generation_limit(self, user: User) -> bool:
        """Check if user has remaining generations."""
        limit = TIER_LIMITS[user.subscription.tier]["generations_per_month"]
        if limit == -1:
            return True
        
        count = await self._get_monthly_generation_count(user.id)
        return count < limit
    
    async def check_storage_limit(self, user: User, file_size: int) -> bool:
        """Check if user has storage capacity."""
        limit_mb = TIER_LIMITS[user.subscription.tier]["storage_mb"]
        used_mb = await self._get_storage_used(user.id)
        return (used_mb + file_size / 1024 / 1024) <= limit_mb
    
    async def check_feature_access(
        self, user: User, feature: str
    ) -> bool:
        """Check if user's tier includes feature."""
        tier_features = TIER_LIMITS[user.subscription.tier]
        return tier_features.get(feature, False)

# Dependency for protected endpoints
async def require_pro(current_user: User = Depends(get_current_user)):
    if current_user.subscription.tier == SubscriptionTier.FREE:
        raise HTTPException(
            status_code=403,
            detail="This feature requires a Pro subscription",
        )
    return current_user
```

**Acceptance Criteria:**
- [ ] Generation limits enforced
- [ ] Storage limits enforced
- [ ] Export format restrictions work
- [ ] Clear error messages with upgrade CTA
- [ ] Limit warnings before hitting max

---

### Epic 8: OAuth Integration (13 points)

#### Task 8.1: Google OAuth (5 points)
**Priority:** P1  
**Assignee:** Backend Developer  

**Dependencies:** `authlib`

**File:** `backend/app/api/v1/auth_oauth.py`

```python
from authlib.integrations.starlette_client import OAuth

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

@router.get("/auth/google")
async def google_login(request: Request):
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/auth/google/callback")
async def google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo")
    
    # Find or create user
    user = await get_or_create_oauth_user(
        db=db,
        provider="google",
        provider_id=user_info["sub"],
        email=user_info["email"],
        name=user_info.get("name"),
        avatar_url=user_info.get("picture"),
    )
    
    # Generate JWT tokens
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    
    # Redirect to frontend with tokens
    return RedirectResponse(
        f"{settings.FRONTEND_URL}/auth/callback?token={access_token}"
    )
```

**Acceptance Criteria:**
- [ ] "Sign in with Google" button works
- [ ] Creates new user on first OAuth login
- [ ] Links to existing account by email
- [ ] Returns valid JWT tokens
- [ ] Profile picture imported

---

#### Task 8.2: GitHub OAuth (5 points)
**Priority:** P1  
**Assignee:** Backend Developer  

Similar implementation to Google:

```python
oauth.register(
    name="github",
    client_id=settings.GITHUB_CLIENT_ID,
    client_secret=settings.GITHUB_CLIENT_SECRET,
    authorize_url="https://github.com/login/oauth/authorize",
    access_token_url="https://github.com/login/oauth/access_token",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "read:user user:email"},
)
```

---

#### Task 8.3: OAuth UI Buttons (3 points)
**Priority:** P1  
**Assignee:** Frontend Developer  

**File:** `frontend/src/components/auth/SocialLogin.tsx`

```tsx
export function SocialLoginButtons() {
  return (
    <div className="social-login-buttons">
      <Button
        variant="outline"
        onClick={() => window.location.href = '/api/v1/auth/google'}
      >
        <GoogleIcon /> Continue with Google
      </Button>
      
      <Button
        variant="outline"
        onClick={() => window.location.href = '/api/v1/auth/github'}
      >
        <GitHubIcon /> Continue with GitHub
      </Button>
    </div>
  );
}
```

---

## Sprint 42: Real-time & Collaboration Polish

**Duration:** 2 weeks  
**Goal:** Complete real-time features and collaboration UX  
**Total Points:** 46  

---

### Epic 9: WebSocket Real-time Updates (13 points)

#### Task 9.1: WebSocket Connection Manager (5 points)
**Priority:** P1  
**Assignee:** Backend Developer  

**File:** `backend/app/websocket/manager.py`

```python
from fastapi import WebSocket
from typing import Dict, Set
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        self.active_connections[user_id].discard(websocket)
    
    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(message)

manager = ConnectionManager()

@router.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    user = await verify_websocket_token(token)
    await manager.connect(websocket, str(user.id))
    try:
        while True:
            data = await websocket.receive_text()
            # Handle ping/pong, subscription to channels
    except WebSocketDisconnect:
        manager.disconnect(websocket, str(user.id))
```

---

#### Task 9.2: Real-time Job Status (5 points)
**Priority:** P1  
**Assignee:** Backend Developer  

**Integration with Celery:**
```python
# In Celery task
@celery_app.task(bind=True)
def generate_part_task(self, job_id: str, user_id: str, ...):
    # Update progress
    self.update_state(state="PROGRESS", meta={"progress": 25})
    
    # Send WebSocket update
    asyncio.run(manager.send_to_user(user_id, {
        "type": "job_progress",
        "job_id": job_id,
        "progress": 25,
        "status": "processing",
    }))
```

**Frontend Hook:**
```typescript
// frontend/src/hooks/useJobStatus.ts
export function useJobStatus(jobId: string) {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const ws = useWebSocket();
  
  useEffect(() => {
    const handler = (message: any) => {
      if (message.type === 'job_progress' && message.job_id === jobId) {
        setStatus(message);
      }
    };
    ws.subscribe(handler);
    return () => ws.unsubscribe(handler);
  }, [jobId, ws]);
  
  return status;
}
```

---

#### Task 9.3: Real-time Notifications (3 points)
**Priority:** P2  
**Assignee:** Full Stack Developer  

**Notification Types:**
- Job completed
- Job failed
- Design shared with you
- Comment on your design
- Approaching storage limit

---

### Epic 10: Collaboration Features (13 points)

#### Task 10.1: Persist Comments to Database (5 points)
**Priority:** P1  
**Assignee:** Backend Developer  

**File:** `backend/app/models/comment.py`

```python
class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(UUID, primary_key=True)
    design_id = Column(UUID, ForeignKey("designs.id"), nullable=False)
    author_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    parent_id = Column(UUID, ForeignKey("comments.id"), nullable=True)
    
    content = Column(Text, nullable=False)
    
    # 3D annotation position (optional)
    position_x = Column(Float, nullable=True)
    position_y = Column(Float, nullable=True)
    position_z = Column(Float, nullable=True)
    
    is_resolved = Column(Boolean, default=False)
    is_edited = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    author = relationship("User")
    replies = relationship("Comment", backref=backref("parent", remote_side=[id]))
```

**Update comments.py:**
- Replace in-memory `_comments` dict with database queries
- Add proper CRUD operations
- Support threading (parent_id)
- Track mentions

---

#### Task 10.2: Sharing UI Integration (5 points)
**Priority:** P1  
**Assignee:** Frontend Developer  

**Components:**
- Share button in file/design toolbar
- Share modal with email input
- Permission level selector (view/comment/edit)
- Copy link button
- Current shares list with remove option

**File:** `frontend/src/components/sharing/ShareModal.tsx`

---

#### Task 10.3: Share Link Generation (3 points)
**Priority:** P1  
**Assignee:** Full Stack  

**Backend:**
```python
@router.post("/shares/link")
async def create_share_link(
    design_id: UUID,
    permission: str = "view",
    expires_days: Optional[int] = 30,
):
    token = secrets.token_urlsafe(32)
    # Store in database
    return {"link": f"{settings.FRONTEND_URL}/shared/{token}"}
```

---

### Epic 11: Onboarding Integration (7 points)

#### Task 11.1: First Login Detection (3 points)
**Priority:** P1  
**Assignee:** Frontend Developer  

```typescript
// frontend/src/hooks/useOnboarding.ts
export function useOnboarding() {
  const { user } = useAuth();
  const [showOnboarding, setShowOnboarding] = useState(false);
  
  useEffect(() => {
    if (user && !user.onboarding_completed) {
      setShowOnboarding(true);
    }
  }, [user]);
  
  const completeOnboarding = async () => {
    await api.patch('/users/me', { onboarding_completed: true });
    setShowOnboarding(false);
  };
  
  return { showOnboarding, completeOnboarding };
}
```

---

#### Task 11.2: Completion Tracking (2 points)
**Priority:** P1  
**Assignee:** Backend Developer  

Add to User model:
```python
onboarding_completed = Column(Boolean, default=False)
onboarding_completed_at = Column(DateTime, nullable=True)
```

---

#### Task 11.3: Skip/Resume Capability (2 points)
**Priority:** P2  
**Assignee:** Frontend Developer  

- "Skip for now" button
- Resume from settings page
- Track which steps completed

---

### Epic 12: Layout Editor Enhancements (13 points)

#### Task 12.1: Collision Detection (5 points)
**Priority:** P2  
**Assignee:** Frontend Developer  

**File:** `frontend/src/components/layout/CollisionDetector.ts`

```typescript
export function detectCollisions(
  placements: ComponentPlacement[]
): CollisionPair[] {
  const collisions: CollisionPair[] = [];
  
  for (let i = 0; i < placements.length; i++) {
    for (let j = i + 1; j < placements.length; j++) {
      if (boxesIntersect(placements[i], placements[j])) {
        collisions.push({
          component1: placements[i].id,
          component2: placements[j].id,
          overlap: calculateOverlap(placements[i], placements[j]),
        });
      }
    }
  }
  
  return collisions;
}
```

**Visual Feedback:**
- Red highlight on colliding components
- Warning icon in component list
- Collision count in toolbar

---

#### Task 12.2: Clearance Visualization (3 points)
**Priority:** P2  
**Assignee:** Frontend Developer  

- Draw clearance zones around components
- Color-code: green (OK), yellow (tight), red (collision)
- Toggle clearance view on/off

---

#### Task 12.3: Auto-Arrange Algorithm (5 points)
**Priority:** P2  
**Assignee:** Algorithm Developer  

**Algorithms:**
- Grid layout (rows/columns)
- Bin packing (minimize enclosure size)
- Thermal-aware (separate heat sources)

```typescript
export function autoArrange(
  components: ComponentData[],
  enclosureSize: Dimensions,
  algorithm: 'grid' | 'pack' | 'thermal' = 'pack',
): ComponentPlacement[] {
  switch (algorithm) {
    case 'grid':
      return gridLayout(components, enclosureSize);
    case 'pack':
      return binPack(components, enclosureSize);
    case 'thermal':
      return thermalAwareLayout(components, enclosureSize);
  }
}
```

---

## Definition of Done (All Sprints)

- [ ] All acceptance criteria met
- [ ] Unit tests written (>80% coverage for new code)
- [ ] Integration tests for API endpoints
- [ ] API documentation updated (OpenAPI spec)
- [ ] UI components accessible (keyboard nav, ARIA labels)
- [ ] No TypeScript/Python type errors
- [ ] Code reviewed and approved
- [ ] Deployed to staging environment
- [ ] QA sign-off

---

## Appendix: Database Migrations Required

| Sprint | Migration | Description |
|--------|-----------|-------------|
| 36-37 | `add_assembly_table` | Create assemblies table |
| 38-39 | `add_enclosure_style_column` | Add style to enclosures |
| 40-41 | `add_subscription_table` | Create subscriptions table |
| 40-41 | `add_stripe_fields_to_user` | Add stripe_customer_id |
| 40-41 | `add_oauth_fields_to_user` | Add oauth_provider, oauth_id |
| 42 | `add_comments_table` | Create comments table |
| 42 | `add_onboarding_to_user` | Add onboarding_completed |

---

## Appendix: Environment Variables Required

```bash
# Sprint 38-39
OPENAI_API_KEY=sk-...  # Existing, needs GPT-4V access

# Sprint 40-41
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PRO_MONTHLY=price_...
STRIPE_PRICE_PRO_YEARLY=price_...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
```

---

# Phase 5: Enhancement Sprints (45-70)

> **Note:** These sprints represent post-launch enhancement work. See [user-stories-phase-5.md](user-stories-phase-5.md) for detailed user stories.

---

## Sprint 45-46: AI Chat Commands & Intelligence (Weeks 11-12)

**Duration:** 2 weeks  
**Goal:** Enhance AI Assistant with slash commands and improved design understanding  
**Total Points:** 47  

---

### Epic: Slash Commands (14 points)

#### Task 45.1: Command Parser & Router (5 points)
**Priority:** P0  
**Assignee:** Frontend/Backend Developer  

**Description:**  
Implement a slash command parser that detects commands in user input and routes them to appropriate handlers.

**File:** `frontend/src/hooks/useSlashCommands.ts`

```typescript
interface SlashCommand {
  name: string;
  aliases: string[];
  description: string;
  handler: (args: string[], context: CommandContext) => Promise<void>;
}

const commands: SlashCommand[] = [
  { name: 'save', aliases: ['s'], description: 'Save current design', handler: handleSave },
  { name: 'export', aliases: ['e'], description: 'Export design', handler: handleExport },
  { name: 'maketemplate', aliases: ['template', 'mt'], description: 'Save as template', handler: handleMakeTemplate },
  { name: 'help', aliases: ['h', '?'], description: 'Show available commands', handler: handleHelp },
  { name: 'undo', aliases: ['u'], description: 'Undo last change', handler: handleUndo },
];

export function parseCommand(input: string): ParsedCommand | null {
  if (!input.startsWith('/')) return null;
  const [command, ...args] = input.slice(1).split(' ');
  return { command: command.toLowerCase(), args };
}
```

**Acceptance Criteria:**
- [ ] Commands starting with `/` are parsed
- [ ] Unknown commands show helpful error
- [ ] Commands are case-insensitive
- [ ] Arguments are passed to handlers

---

#### Task 45.2: Core Command Implementations (6 points)
**Priority:** P0  
**Assignee:** Backend Developer  

**Commands to implement:**
- `/save` - Triggers design save
- `/export [format]` - Export to STL/STEP/OBJ (default: STL)
- `/maketemplate [name]` - Create template from current design
- `/help` - Show all available commands
- `/undo` - Revert last generation

**Acceptance Criteria:**
- [ ] `/save` triggers save API and confirms in chat
- [ ] `/export stl` downloads STL file
- [ ] `/maketemplate "My Template"` opens template creation dialog
- [ ] `/help` shows formatted command list
- [ ] `/undo` reverts to previous design state

---

#### Task 45.3: Command Autocomplete (3 points)
**Priority:** P1  
**Assignee:** Frontend Developer  

**Description:**  
Show command suggestions when user types `/`.

**File:** `frontend/src/components/generation/CommandAutocomplete.tsx`

**Acceptance Criteria:**
- [ ] Dropdown appears when typing `/`
- [ ] Commands filtered as user types
- [ ] Tab/Enter selects command
- [ ] Escape dismisses dropdown

---

### Epic: AI Intelligence Improvements (33 points)

#### Task 45.4: Gridfinity Pattern Understanding (5 points)
**Priority:** P1  
**Assignee:** AI/Backend Developer  

**Description:**  
Train/prompt AI to understand Gridfinity modular storage system patterns.

**Technical Notes:**
- Add Gridfinity specs to system prompt
- Grid unit: 42mm × 42mm
- Heights: 7mm increments (7, 14, 21, 28, 35, 42mm)
- Base plate compatibility

**Acceptance Criteria:**
- [ ] AI recognizes "Gridfinity" keyword
- [ ] Generates correct grid dimensions
- [ ] Creates base plate compatible bins
- [ ] Supports custom grid counts (2×3, 3×3, etc.)

---

#### Task 45.5: Dovetail Joint Generation (5 points)
**Priority:** P1  
**Assignee:** CAD/Backend Developer  

**Description:**  
Add dovetail joint parametric generation to CAD engine.

**File:** `backend/app/cad/joints.py`

```python
def create_dovetail_joint(
    board_width: float,
    board_thickness: float,
    num_tails: int = 3,
    pin_angle: float = 14.0,  # degrees
    tail_length: Optional[float] = None,
) -> Tuple[cq.Workplane, cq.Workplane]:
    """Returns (tail_board, pin_board) ready for assembly."""
```

**Acceptance Criteria:**
- [ ] AI understands "dovetail joint" requests
- [ ] Configurable number of tails
- [ ] Configurable pin angle (8°-15°)
- [ ] Generates mating parts

---

#### Task 46.1: Clarifying Questions System (8 points)
**Priority:** P0  
**Assignee:** AI/Backend Developer  

**Description:**  
When user input is ambiguous or incomplete, AI asks clarifying questions.

**Implementation:**
```python
class DesignIntent:
    confidence: float  # 0-1
    missing_info: List[str]  # What we need
    clarifying_questions: List[str]  # Questions to ask

async def analyze_intent(prompt: str) -> DesignIntent:
    # Use LLM to determine if we have enough info
    # If confidence < 0.7, generate clarifying questions
```

**Acceptance Criteria:**
- [ ] Ambiguous prompts trigger questions
- [ ] Questions are specific and actionable
- [ ] User answers are incorporated into next attempt
- [ ] Confidence threshold is configurable

---

#### Task 46.2: Multi-step Workflow Support (8 points)
**Priority:** P1  
**Assignee:** AI/Backend Developer  

**Description:**  
Support complex design workflows that require multiple steps.

**Examples:**
- "Create a box, then add a lid, then add hinges"
- "First make the base, then create mounting brackets"

**Acceptance Criteria:**
- [ ] AI understands step sequences
- [ ] Each step builds on previous
- [ ] User can modify individual steps
- [ ] Full workflow saved as history

---

#### Task 46.3: Complex Constraint Understanding (7 points)
**Priority:** P1  
**Assignee:** AI Developer  

**Description:**  
Improve AI's ability to understand complex design constraints.

**Constraint types:**
- Dimensional relationships ("width = 2× height")
- Fit constraints ("must fit inside 100mm cube")
- Functional constraints ("waterproof", "stackable")
- Material constraints ("3mm wall for strength")

**Acceptance Criteria:**
- [ ] AI extracts constraints from natural language
- [ ] Constraints validated before generation
- [ ] Conflicting constraints flagged
- [ ] Constraint summary shown to user

---

## Sprint 47-48: AI Performance & Manufacturing (Weeks 13-14)

**Duration:** 2 weeks  
**Goal:** Optimize response times and add manufacturing awareness  
**Total Points:** 46  

---

### Epic: Performance Optimization (18 points)

#### Task 47.1: Response Time Optimization (8 points)
**Priority:** P0  
**Assignee:** Backend Developer  

**Target:** < 3 seconds average response time

**Optimizations:**
- LLM response caching for similar prompts
- CAD operation parallelization
- Pre-computed common shapes
- Streaming LLM responses

**Acceptance Criteria:**
- [ ] Average response time < 3s for simple designs
- [ ] P95 response time < 8s
- [ ] Cache hit rate > 30% for common designs

---

#### Task 47.2: Streaming Responses (5 points)
**Priority:** P1  
**Assignee:** Backend/Frontend Developer  

**Description:**  
Stream AI responses to show progress during long generations.

**Acceptance Criteria:**
- [ ] Response starts appearing within 1s
- [ ] Progress indicator for CAD generation phase
- [ ] Graceful handling of stream interruptions

---

#### Task 47.3: Model Caching (5 points)
**Priority:** P1  
**Assignee:** Backend Developer  

**Description:**  
Cache generated CAD models for reuse and modification.

**Acceptance Criteria:**
- [ ] Generated models cached by prompt hash
- [ ] Cache invalidation on parameter changes
- [ ] Memory-efficient storage

---

### Epic: Manufacturing Awareness (28 points)

#### Task 47.4: 3D Print Optimization (5 points)
**Priority:** P1  
**Assignee:** CAD Developer  

**Optimizations:**
- Minimize support structures
- Optimal print orientation
- Bridge/overhang limits (45°)
- Layer adhesion considerations

**Acceptance Criteria:**
- [ ] Designs optimized for print orientation
- [ ] Overhangs limited to 45° by default
- [ ] Support minimization for flat surfaces

---

#### Task 47.5: Material Recommendation Engine (5 points)
**Priority:** P1  
**Assignee:** Backend Developer  

**File:** `backend/app/ai/materials.py`

```python
class MaterialRecommendation:
    material: str  # PLA, PETG, ABS, etc.
    confidence: float
    reasoning: str
    properties: Dict[str, Any]  # strength, temp resistance, etc.

async def recommend_material(design: Design, use_case: str) -> List[MaterialRecommendation]:
    # Consider: outdoor use, load-bearing, temperature, flexibility
```

**Acceptance Criteria:**
- [ ] AI suggests appropriate materials
- [ ] Considers use case (outdoor, food-safe, etc.)
- [ ] Explains recommendations

---

#### Task 48.1: Print Settings Suggestions (5 points)
**Priority:** P1  
**Assignee:** Backend Developer  

**Settings to suggest:**
- Layer height (0.1-0.3mm)
- Infill percentage (10-100%)
- Wall count
- Support type
- Print speed

**Acceptance Criteria:**
- [ ] Settings based on design requirements
- [ ] Exportable to slicer profiles
- [ ] Considers print time vs quality tradeoff

---

#### Task 48.2: Manufacturer Constraint Awareness (8 points)
**Priority:** P0  
**Assignee:** AI/CAD Developer  

**Description:**  
AI understands different manufacturing methods and their constraints.

**Manufacturing types:**
- 3D Printing (FDM, SLA, SLS)
- CNC Milling
- Laser Cutting
- Injection Molding

```python
class ManufacturingConstraints:
    method: str
    min_wall_thickness: float
    min_feature_size: float
    max_overhang: float
    requires_support: bool
    material_limitations: List[str]

def validate_for_manufacturing(
    design: Design, 
    method: str
) -> List[ConstraintViolation]:
    # Check design against manufacturing limits
```

**Acceptance Criteria:**
- [ ] User can specify target manufacturing method
- [ ] Design validated against method constraints
- [ ] Violations shown with fix suggestions
- [ ] "This design can be 3D printed but not CNC milled" warnings

---

#### Task 48.3: Printability Warnings (5 points)
**Priority:** P1  
**Assignee:** CAD Developer  

**Warnings:**
- Thin walls (< 0.8mm for FDM)
- Small holes (< 2mm may close)
- Large overhangs
- Unsupported bridges
- Sharp internal corners

**Acceptance Criteria:**
- [ ] Warnings shown in design review
- [ ] Specific location highlighted in 3D view
- [ ] Suggested fixes provided

---

## Sprint 49-50: Design System & Theming (Weeks 15-16)

**Duration:** 2 weeks  
**Goal:** Implement industrial-modern theme with dark/light mode  
**Total Points:** 36  

---

### Epic: Theme System (28 points)

#### Task 49.1: CSS Custom Properties Setup (5 points)
**Priority:** P0  
**Assignee:** Frontend Developer  

**File:** `frontend/src/styles/theme.css`

```css
:root {
  /* Light mode (fallback) */
  --color-bg-primary: #f8fafc;
  --color-bg-surface: #ffffff;
  --color-text-primary: #0f172a;
  --color-text-secondary: #64748b;
  --color-accent-primary: #21C4F3;
  --color-accent-secondary: #1F6FDB;
  --color-border: #e2e8f0;
  --color-success: #2EE6C8;
}

[data-theme="dark"] {
  --color-bg-primary: #0E1A26;
  --color-bg-surface: #123A5F;
  --color-text-primary: #F4F7FA;
  --color-text-secondary: #9FB2C8;
  --color-accent-primary: #21C4F3;
  --color-accent-secondary: #1F6FDB;
  --color-border: #2A3A4A;
  --color-success: #2EE6C8;
}
```

**Acceptance Criteria:**
- [ ] All colors use CSS custom properties
- [ ] Dark mode is default
- [ ] Smooth transition between themes

---

#### Task 49.2: Dark Mode Implementation (5 points)
**Priority:** P0  
**Assignee:** Frontend Developer  

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

**Acceptance Criteria:**
- [ ] All components use dark theme colors
- [ ] High contrast for readability
- [ ] CAD-adjacent, industrial aesthetic
- [ ] No bright/flashy colors

---

#### Task 49.3: Light Mode Implementation (5 points)
**Priority:** P1  
**Assignee:** Frontend Developer  

**Acceptance Criteria:**
- [ ] Light mode alternative available
- [ ] Maintains brand consistency
- [ ] Accessible contrast ratios

---

#### Task 49.4: Theme Toggle & Persistence (2 points)
**Priority:** P1  
**Assignee:** Frontend Developer  

**Acceptance Criteria:**
- [ ] Toggle in settings/header
- [ ] Preference saved to localStorage
- [ ] Synced to user profile when logged in
- [ ] Respects system preference initially

---

### Epic: Navigation Redesign (8 points)

#### Task 50.1: Remove Create Button from Nav (1 point)
**Priority:** P0  
**Assignee:** Frontend Developer  

**Acceptance Criteria:**
- [ ] "Create" button removed from navbar
- [ ] Create action accessible via chat/dashboard

---

#### Task 50.2: Slide-out History Panel (5 points)
**Priority:** P1  
**Assignee:** Frontend Developer  

**File:** `frontend/src/components/layout/HistoryPanel.tsx`

**Acceptance Criteria:**
- [ ] History button on left side of screen
- [ ] Click opens slide-out panel
- [ ] Panel shows past conversations
- [ ] Click conversation to resume
- [ ] Panel closes on outside click

---

#### Task 50.3: Conversation History Redesign (2 points)
**Priority:** P1  
**Assignee:** Frontend Developer  

**Acceptance Criteria:**
- [ ] Conversations grouped by date
- [ ] Search/filter conversations
- [ ] Preview of last message

---

## Sprint 51-52: Chat History & Privacy (Weeks 17-18)

**Duration:** 2 weeks  
**Goal:** Persistent chat history with full privacy controls  
**Total Points:** 30  

---

### Epic: Chat Persistence (13 points)

#### Task 51.1: Conversation Database Model (5 points)
**Priority:** P0  
**Assignee:** Backend Developer  

**File:** `backend/app/models/conversation.py`

```python
class Conversation(Base):
    __tablename__ = "conversations"
    
    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    is_deleted: Mapped[bool] = mapped_column(default=False)

class Message(Base):
    __tablename__ = "messages"
    
    id: Mapped[UUID] = mapped_column(primary_key=True)
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversations.id"))
    role: Mapped[str]  # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text)
    design_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("designs.id"))
    thumbnail_url: Mapped[Optional[str]]
    created_at: Mapped[datetime]
```

**Acceptance Criteria:**
- [ ] Conversations persisted to database
- [ ] Messages linked to conversations
- [ ] Designs linked to messages
- [ ] Soft delete support

---

#### Task 51.2: Conversation List API (3 points)
**Priority:** P0  
**Assignee:** Backend Developer  

**Endpoints:**
- `GET /api/v1/conversations` - List user's conversations
- `GET /api/v1/conversations/{id}` - Get conversation with messages
- `DELETE /api/v1/conversations/{id}` - Soft delete
- `POST /api/v1/conversations` - Create new

---

#### Task 51.3: Search Conversations (3 points)
**Priority:** P1  
**Assignee:** Backend Developer  

**Endpoint:** `GET /api/v1/conversations/search?q=...`

**Acceptance Criteria:**
- [ ] Full-text search in message content
- [ ] Search results grouped by conversation
- [ ] Highlights matching text

---

#### Task 51.4: Export Conversation History (2 points)
**Priority:** P1  
**Assignee:** Backend Developer  

**Formats:** PDF, TXT, JSON

**Endpoint:** `GET /api/v1/conversations/{id}/export?format=pdf`

---

### Epic: Privacy Controls (17 points)

#### Task 52.1: Delete Individual Conversation (3 points)
**Priority:** P0  
**Assignee:** Frontend/Backend Developer  

**Acceptance Criteria:**
- [ ] Delete button on each conversation
- [ ] Confirmation dialog
- [ ] Hard delete with cascading messages

---

#### Task 52.2: Delete All Chat History (3 points)
**Priority:** P0  
**Assignee:** Frontend/Backend Developer  

**Endpoint:** `DELETE /api/v1/conversations/all`

**Acceptance Criteria:**
- [ ] "Delete All" in privacy settings
- [ ] Strong confirmation (type "DELETE")
- [ ] Removes all conversations and messages
- [ ] Sends confirmation email

---

#### Task 52.3: Data Retention Settings (3 points)
**Priority:** P2  
**Assignee:** Backend Developer  

**Options:**
- Keep forever (default)
- Auto-delete after 30/60/90 days
- Delete on account deletion only

---

#### Task 52.4: Privacy Dashboard (5 points)
**Priority:** P1  
**Assignee:** Frontend Developer  

**File:** `frontend/src/pages/settings/PrivacySettings.tsx`

**Features:**
- Data usage summary
- Download my data (GDPR)
- Delete all data
- Retention settings
- Third-party data sharing controls

---

#### Task 52.5: GDPR Data Export (3 points)
**Priority:** P1  
**Assignee:** Backend Developer  

**Endpoint:** `POST /api/v1/users/me/export`

**Acceptance Criteria:**
- [ ] Export all user data as ZIP
- [ ] Includes conversations, designs, profile
- [ ] Sent via email when ready
- [ ] Rate limited (1/day)

---

## Sprint 53-54: Response Rating & Feedback (Weeks 19-20)

**Duration:** 2 weeks  
**Goal:** Enable users to rate and provide feedback on AI responses  
**Total Points:** 28  

---

### Epic: Rating System (17 points)

#### Task 53.1: Response Rating UI (3 points)
**Priority:** P0  
**Assignee:** Frontend Developer  

**File:** `frontend/src/components/generation/ResponseRating.tsx`

```tsx
export function ResponseRating({ messageId, onRate }: Props) {
  return (
    <div className="flex gap-2 mt-2">
      <button onClick={() => onRate('up')} aria-label="Helpful">
        <ThumbsUp size={16} />
      </button>
      <button onClick={() => onRate('down')} aria-label="Not helpful">
        <ThumbsDown size={16} />
      </button>
    </div>
  );
}
```

**Acceptance Criteria:**
- [ ] Thumbs up/down on each AI response
- [ ] Rating saved immediately
- [ ] Visual feedback on selection
- [ ] Can change rating

---

#### Task 53.2: Rating Backend (3 points)
**Priority:** P0  
**Assignee:** Backend Developer  

**Endpoint:** `POST /api/v1/messages/{id}/rating`

```python
class ResponseRating(Base):
    message_id: Mapped[UUID]
    user_id: Mapped[UUID]
    rating: Mapped[str]  # 'up' or 'down'
    feedback_text: Mapped[Optional[str]]
    created_at: Mapped[datetime]
```

---

#### Task 53.3: Optional Feedback Text (3 points)
**Priority:** P1  
**Assignee:** Frontend Developer  

**Acceptance Criteria:**
- [ ] After rating, optional feedback prompt
- [ ] Text area for detailed feedback
- [ ] Categorization (accuracy, speed, style)
- [ ] Skip option

---

#### Task 53.4: Admin Rating Analytics (5 points)
**Priority:** P1  
**Assignee:** Backend/Frontend Developer  

**Dashboard shows:**
- Overall satisfaction rate
- Rating trends over time
- Common feedback themes
- Low-rated prompts for review

---

#### Task 53.5: Detailed Feedback Form (3 points)
**Priority:** P1  
**Assignee:** Frontend Developer  

**Categories:**
- Accuracy (design matched request)
- Speed (response time)
- Clarity (explanation quality)
- Usefulness (solved my problem)

---

### Epic: Favorites System (11 points)

#### Task 54.1: Save Favorite Responses (5 points)
**Priority:** P1  
**Assignee:** Frontend/Backend Developer  

**Acceptance Criteria:**
- [ ] Star/bookmark button on responses
- [ ] Favorites list in sidebar
- [ ] View favorite with context
- [ ] Quick copy/reuse

---

#### Task 54.2: Organize Favorites with Tags (3 points)
**Priority:** P2  
**Assignee:** Frontend Developer  

**Acceptance Criteria:**
- [ ] Add tags to favorites
- [ ] Filter by tag
- [ ] Suggested tags based on content

---

#### Task 54.3: Quick Reference Panel (3 points)
**Priority:** P1  
**Assignee:** Frontend Developer  

**Acceptance Criteria:**
- [ ] Panel showing recent favorites
- [ ] One-click to view full response
- [ ] Copy prompt to current input

---

## Sprint 55-56: AI Personalization (Weeks 21-22)

**Duration:** 2 weeks  
**Goal:** Allow users to customize AI behavior and personality  
**Total Points:** 35  

---

### Epic: AI Naming & Branding (4 points)

#### Task 55.1: Custom AI Name (2 points)
**Priority:** P2  
**Assignee:** Frontend/Backend Developer  

**Default name:** "CADdy" (CAD + buddy)

**Acceptance Criteria:**
- [ ] Default AI name is "CADdy"
- [ ] User can customize in settings
- [ ] Name appears in chat UI
- [ ] Name used in notifications

---

#### Task 55.2: AI Name in UI (2 points)
**Priority:** P2  
**Assignee:** Frontend Developer  

**Acceptance Criteria:**
- [ ] AI messages show name
- [ ] Welcome message uses name
- [ ] Consistent across app

---

### Epic: Response Style (10 points)

#### Task 55.3: Style Presets (5 points)
**Priority:** P1  
**Assignee:** Backend Developer  

**Presets:**
- **Concise:** Short, to-the-point responses
- **Detailed:** Thorough explanations with context
- **Technical:** Engineering-focused, precise terminology
- **Friendly:** Casual, encouraging tone

```python
STYLE_PROMPTS = {
    "concise": "Be brief and direct. No unnecessary words.",
    "detailed": "Provide thorough explanations with context and reasoning.",
    "technical": "Use precise engineering terminology. Be specific about dimensions and tolerances.",
    "friendly": "Be warm and encouraging. Explain things clearly for beginners.",
}
```

---

#### Task 55.4: Custom Personality Instructions (5 points)
**Priority:** P2  
**Assignee:** Backend Developer  

**Acceptance Criteria:**
- [ ] Free-form personality instructions
- [ ] Character limit (500 chars)
- [ ] Preview with sample response
- [ ] Reset to default option

---

### Epic: Voice Interface (21 points)

#### Task 56.1: Voice Output (TTS) (8 points)
**Priority:** P2  
**Assignee:** Frontend Developer  

**Using:** Web Speech API

**Acceptance Criteria:**
- [ ] Read AI responses aloud
- [ ] Toggle voice on/off
- [ ] Adjustable speech rate
- [ ] Stop/pause controls

---

#### Task 56.2: Voice Input (STT) (8 points)
**Priority:** P2  
**Assignee:** Frontend Developer  

**Using:** Web Speech API

**Acceptance Criteria:**
- [ ] Microphone button in input
- [ ] Real-time transcription
- [ ] Visual feedback while listening
- [ ] Handle ambient noise

---

#### Task 56.3: Hands-free Mode (5 points)
**Priority:** P3  
**Assignee:** Frontend Developer  

**Acceptance Criteria:**
- [ ] Toggle hands-free mode
- [ ] Auto-listen after response
- [ ] Wake word detection (optional)
- [ ] Voice commands for navigation

---

## Definition of Done (Enhancement Sprints)

- [ ] All acceptance criteria met
- [ ] Unit tests written (>80% coverage for new code)
- [ ] API documentation updated
- [ ] UI components accessible (keyboard nav, ARIA)
- [ ] Dark mode fully supported
- [ ] Mobile responsive
- [ ] Performance benchmarks met
- [ ] Code reviewed and approved
- [ ] Deployed to staging environment
- [ ] QA sign-off

---

## Appendix: Database Migrations (Enhancement Phases)

| Sprint | Migration | Description |
|--------|-----------|-------------|
| 51-52 | `add_conversations_table` | Create conversations table |
| 51-52 | `add_messages_table` | Create messages table |
| 53-54 | `add_ratings_table` | Create response ratings table |
| 53-54 | `add_favorites_table` | Create favorites table |
| 55-56 | `add_user_preferences` | AI name, style, voice settings |

---

## Appendix: Environment Variables (Enhancement Phases)

```bash
# Sprint 55-56 (Optional - for advanced voice features)
AZURE_SPEECH_KEY=...  # If using Azure instead of Web Speech API
AZURE_SPEECH_REGION=...
```
