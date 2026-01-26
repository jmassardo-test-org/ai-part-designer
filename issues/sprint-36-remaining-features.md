# Sprint 36: Remaining Features & Polish

## Sprint Overview
**Duration:** 2 weeks  
**Goal:** Complete remaining user story gaps and polish core features  
**Points:** 34 total

---

## Epic 1: File Alignment & CAD Combination (13 points)

### 1.1 File Alignment API (5 points)
**Priority:** High  
**Description:** Enable users to align and combine multiple uploaded CAD files

**Tasks:**
- [ ] Create `AlignmentService` with alignment operations:
  - Align by face (coplanar surfaces)
  - Align by edge (parallel/coincident)
  - Align by center (bounding box centers)
  - Align by origin
- [ ] Add `/api/v1/cad/align` endpoint
- [ ] Support alignment between 2+ STEP/STL files
- [ ] Return combined assembly as single STEP file

**Acceptance Criteria:**
- User can upload 2 files and specify alignment method
- Preview alignment before committing
- Export combined result

---

### 1.2 File Alignment UI (5 points)
**Priority:** High  
**Description:** Frontend interface for aligning files

**Tasks:**
- [ ] Create `AlignmentEditor` component with 3D preview
- [ ] Add alignment controls (translate, rotate, snap)
- [ ] Implement drag handles for manual positioning
- [ ] Add alignment presets (center, stack, side-by-side)
- [ ] Show bounding boxes and reference points

**Acceptance Criteria:**
- Visual 3D editor for positioning
- Real-time preview of alignment
- One-click presets for common alignments

---

### 1.3 Assembly from Multiple Files (3 points)
**Priority:** Medium  
**Description:** Save aligned files as reusable assemblies

**Tasks:**
- [ ] Store alignment transformations in Assembly model
- [ ] Allow editing assembly component positions
- [ ] Export full assembly as STEP/STL

---

## Epic 2: Enhanced AI Extraction (8 points)

### 2.1 GPT-4 Vision PDF Analysis (5 points)
**Priority:** High  
**Description:** Use GPT-4 Vision to extract dimensions from mechanical drawings in PDFs

**Tasks:**
- [ ] Integrate GPT-4 Vision API for image analysis
- [ ] Convert PDF pages to images for vision analysis
- [ ] Extract dimension annotations from drawings
- [ ] Parse mounting hole patterns from images
- [ ] Identify connector locations and cutout shapes

**Acceptance Criteria:**
- Upload PDF with mechanical drawing
- AI identifies dimensions with confidence scores
- User can verify/correct extractions

---

### 2.2 Improved Dimension Extraction UI (3 points)
**Priority:** Medium  
**Description:** Better UI for reviewing and correcting AI extractions

**Tasks:**
- [ ] Show PDF page with overlay annotations
- [ ] Highlight extracted dimensions on image
- [ ] Click-to-edit extracted values
- [ ] Side-by-side comparison view

---

## Epic 3: Advanced Mounting Options (8 points)

### 3.1 Additional Mounting Types (5 points)
**Priority:** Medium  
**Description:** Expand mounting options beyond standoffs

**Tasks:**
- [ ] **Snap-fit clips** - Tool-less assembly clips
- [ ] **DIN rail mounts** - Industrial 35mm rail brackets
- [ ] **Wall mount brackets** - Keyhole and screw patterns
- [ ] **Adhesive pads** - 3M VHB tape mounting points
- [ ] **Cable tie anchors** - For wire management

**Implementation:**
- Add `MountingType` enum with new options
- Create CadQuery generators for each type
- Update enclosure generation to use selected mount types

**Acceptance Criteria:**
- User can select mounting type per component
- Generated enclosure includes correct mounting features

---

### 3.2 Heat-Set Insert Support (3 points)
**Priority:** Low  
**Description:** Add heat-set insert options for 3D printed enclosures

**Tasks:**
- [ ] Add insert hole generators (M2, M2.5, M3, M4)
- [ ] Include proper undersized holes for insert press-fit
- [ ] Add boss/pillar around insert locations
- [ ] Document insert specifications in export

---

## Epic 4: Enclosure Style Templates (5 points)

### 4.1 Additional Style Templates (3 points)
**Priority:** Medium  
**Description:** Add more enclosure style presets

**New Templates:**
- [ ] **Rugged** - Thick walls, rounded corners, IP65-ready
- [ ] **Stackable** - Interlocking features for vertical stacking
- [ ] **Industrial** - DIN rail compatible, terminal blocks
- [ ] **Desktop** - Angled front, anti-slip feet
- [ ] **Handheld** - Ergonomic curves, battery compartment

**Tasks:**
- Add template definitions with parameters
- Create preview thumbnails
- Apply style to enclosure generation

---

### 4.2 Style Customization UI (2 points)
**Priority:** Low  
**Description:** Allow users to customize style parameters

**Tasks:**
- [ ] Style parameter sliders (wall thickness, corner radius)
- [ ] Preview changes in real-time
- [ ] Save custom styles to user library

---

## Sprint Schedule

### Week 1
| Day | Focus |
|-----|-------|
| Mon-Tue | Epic 1.1 - File Alignment API |
| Wed-Thu | Epic 1.2 - File Alignment UI |
| Fri | Epic 1.3 - Assembly from Multiple Files |

### Week 2
| Day | Focus |
|-----|-------|
| Mon-Tue | Epic 2.1 - GPT-4 Vision PDF Analysis |
| Wed | Epic 2.2 - Dimension Extraction UI |
| Thu | Epic 3.1 - Additional Mounting Types |
| Fri | Epic 4.1 - Style Templates + Polish |

---

## Dependencies

- OpenAI API access for GPT-4 Vision (Epic 2)
- PDF-to-image conversion library (pdf2image/Pillow)
- Three.js transform controls (Epic 1.2)

---

## Out of Scope (Future Sprints)

- Community component contributions
- Cable routing channel generation
- Label/branding placement tools
- Mobile-responsive layout editor

---

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Unit tests for new services
- [ ] API endpoints documented
- [ ] UI components accessible (keyboard nav, screen reader)
- [ ] No TypeScript/Python type errors
- [ ] Code reviewed and merged
