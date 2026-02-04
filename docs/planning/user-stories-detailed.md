# Detailed User Stories
# AI Part Designer

**Version:** 1.0  
**Date:** 2026-01-24  
**Status:** Draft  

---

## Table of Contents
1. [User Authentication & Account Management](#1-user-authentication--account-management)
2. [Part Design & Generation](#2-part-design--generation)
3. [File Management](#3-file-management)
4. [Queue & Job Processing](#4-queue--job-processing)
5. [Dashboard & Projects](#5-dashboard--projects)
6. [Subscription & Billing](#6-subscription--billing)
7. [Collaboration & Sharing](#7-collaboration--sharing)
8. [Administration](#8-administration)

---

## Story Format

Each user story follows the INVEST criteria and includes:
- **ID**: Unique identifier
- **Title**: Brief description
- **Story**: As a [role], I want [capability], so that [benefit]
- **Acceptance Criteria**: Given-When-Then format
- **Priority**: Must Have | Should Have | Could Have
- **Story Points**: Relative effort estimate (1, 2, 3, 5, 8, 13)
- **Dependencies**: Related stories

---

## 1. User Authentication & Account Management

### US-101: User Registration
| Attribute | Value |
|-----------|-------|
| **ID** | US-101 |
| **Title** | User Registration |
| **Priority** | Must Have |
| **Story Points** | 5 |
| **Dependencies** | None |

**Story:**  
As a **new visitor**, I want to **create an account with my email and password**, so that **I can save my designs and access them later**.

**Acceptance Criteria:**

```gherkin
Scenario: Successful registration
  Given I am on the registration page
  When I enter a valid email "user@example.com"
  And I enter a password meeting complexity requirements
  And I enter a display name
  And I accept the Terms of Service
  And I click "Create Account"
  Then my account is created with "pending" status
  And I receive a verification email within 60 seconds
  And I am redirected to a "check your email" page

Scenario: Registration with existing email
  Given I am on the registration page
  And an account exists with email "existing@example.com"
  When I enter email "existing@example.com"
  And I complete the form and submit
  Then I see an error "An account with this email already exists"
  And no new account is created

Scenario: Registration with weak password
  Given I am on the registration page
  When I enter a password "weak"
  Then I see password requirements displayed
  And the submit button is disabled until requirements are met

Scenario: Email verification
  Given I have registered and received verification email
  When I click the verification link within 24 hours
  Then my account status changes to "active"
  And I am redirected to the onboarding flow
```

---

### US-102: User Login
| Attribute | Value |
|-----------|-------|
| **ID** | US-102 |
| **Title** | User Login |
| **Priority** | Must Have |
| **Story Points** | 3 |
| **Dependencies** | US-101 |

**Story:**  
As a **registered user**, I want to **log in with my email and password**, so that **I can access my account and designs**.

**Acceptance Criteria:**

```gherkin
Scenario: Successful login
  Given I have an active account with email "user@example.com"
  And I am on the login page
  When I enter my correct email and password
  And I click "Log In"
  Then I am authenticated
  And I am redirected to my dashboard
  And I see a welcome message with my display name

Scenario: Login with incorrect password
  Given I am on the login page
  When I enter a valid email but incorrect password
  Then I see a generic error "Invalid email or password"
  And I am not authenticated
  And failed attempt is logged

Scenario: Login with unverified account
  Given I have an account with "pending" status
  When I attempt to log in
  Then I see a message "Please verify your email first"
  And I am offered an option to resend verification email

Scenario: Login with suspended account
  Given my account has been suspended
  When I attempt to log in
  Then I see a message explaining the suspension
  And I am provided contact information for support

Scenario: Remember me functionality
  Given I am on the login page
  When I check "Remember me" and log in
  Then my session persists for 30 days instead of 7 days
```

---

### US-103: Password Reset
| Attribute | Value |
|-----------|-------|
| **ID** | US-103 |
| **Title** | Password Reset |
| **Priority** | Must Have |
| **Story Points** | 3 |
| **Dependencies** | US-101 |

**Story:**  
As a **user who forgot my password**, I want to **reset my password via email**, so that **I can regain access to my account**.

**Acceptance Criteria:**

```gherkin
Scenario: Request password reset
  Given I am on the login page
  When I click "Forgot password?"
  And I enter my registered email
  And I click "Send Reset Link"
  Then I see "If an account exists, you will receive an email"
  And if the email exists, a reset email is sent within 60 seconds

Scenario: Reset password with valid token
  Given I have requested a password reset
  And I received the reset email
  When I click the reset link within 1 hour
  And I enter a new password meeting requirements
  And I confirm the new password
  And I click "Reset Password"
  Then my password is updated
  And I am logged in automatically
  And I receive a confirmation email

Scenario: Reset password with expired token
  Given I have a reset token that is more than 1 hour old
  When I click the reset link
  Then I see "This reset link has expired"
  And I am prompted to request a new reset

Scenario: Prevent email enumeration
  Given an email "nonexistent@example.com" has no account
  When I request a password reset for that email
  Then I see the same success message as for existing accounts
  And no email is sent
```

---

### US-104: User Profile Management
| Attribute | Value |
|-----------|-------|
| **ID** | US-104 |
| **Title** | Profile Management |
| **Priority** | Should Have |
| **Story Points** | 3 |
| **Dependencies** | US-102 |

**Story:**  
As a **logged-in user**, I want to **update my profile information**, so that **my account reflects my current preferences**.

**Acceptance Criteria:**

```gherkin
Scenario: Update display name
  Given I am logged in and on my profile page
  When I change my display name to "New Name"
  And I click "Save"
  Then my display name is updated
  And I see a success confirmation

Scenario: Update email address
  Given I am logged in and on my profile page
  When I change my email to "newemail@example.com"
  And I enter my current password for verification
  And I click "Save"
  Then a verification email is sent to the new address
  And my email is updated after verification

Scenario: Change password
  Given I am logged in and on my profile page
  When I enter my current password
  And I enter a new password meeting requirements
  And I confirm the new password
  And I click "Update Password"
  Then my password is updated
  And other active sessions are invalidated
  And I receive a confirmation email

Scenario: Update notification preferences
  Given I am logged in and on my profile page
  When I toggle "Email me when jobs complete" to off
  And I click "Save"
  Then my preference is saved
  And I will not receive job completion emails
```

---

### US-105: Account Deletion
| Attribute | Value |
|-----------|-------|
| **ID** | US-105 |
| **Title** | Account Deletion |
| **Priority** | Should Have |
| **Story Points** | 3 |
| **Dependencies** | US-102 |

**Story:**  
As a **user**, I want to **delete my account**, so that **my data is removed from the platform**.

**Acceptance Criteria:**

```gherkin
Scenario: Request account deletion
  Given I am logged in and on my account settings
  When I click "Delete Account"
  Then I see a warning about data loss
  And I am asked to type "DELETE" to confirm
  And I must enter my password

Scenario: Confirm account deletion
  Given I have initiated account deletion
  When I type "DELETE" and enter my password
  And I click "Permanently Delete Account"
  Then my account is scheduled for deletion in 30 days
  And I am logged out
  And I receive a confirmation email with cancellation option

Scenario: Cancel account deletion
  Given my account is scheduled for deletion
  When I log in within 30 days
  Then I see a banner "Your account is scheduled for deletion"
  And I can click "Cancel Deletion" to restore my account
```

---

## 2. Part Design & Generation

### US-201: Generate Part from Natural Language
| Attribute | Value |
|-----------|-------|
| **ID** | US-201 |
| **Title** | Natural Language Part Generation |
| **Priority** | Must Have |
| **Story Points** | 13 |
| **Dependencies** | US-102 |

**Story:**  
As a **user**, I want to **describe a part in plain English and have the AI generate a 3D model**, so that **I can create parts without CAD expertise**.

**Acceptance Criteria:**

```gherkin
Scenario: Generate simple part from description
  Given I am logged in and on the design page
  When I enter "Create a rectangular box 100mm x 50mm x 30mm with rounded corners"
  And I click "Generate"
  Then a job is submitted to the queue
  And I see the job status updating
  And within 120 seconds, a 3D preview is displayed
  And the dimensions match my request within 5% tolerance

Scenario: Generate part with complex features
  Given I am logged in and on the design page
  When I enter "Create a project box with screw posts in corners, ventilation slots on sides, and a snap-fit lid"
  And I click "Generate"
  Then the AI generates a part with the specified features
  And I can inspect each feature in the 3D preview

Scenario: Handle ambiguous description
  Given I enter a vague description "make me a bracket"
  When I click "Generate"
  Then the AI either:
    - Asks clarifying questions about dimensions and mounting
    - Or generates a reasonable default with explanation
  And I can refine the result with follow-up modifications

Scenario: Reject prohibited content
  Given I enter a description for a weapon component
  When I click "Generate"
  Then the request is rejected
  And I see a message about prohibited content
  And the attempt is logged for review

Scenario: Handle generation failure
  Given I enter a valid but very complex description
  When generation fails
  Then I see a clear error message
  And I am offered suggestions to simplify the request
  And the job is not counted against my quota
```

---

### US-202: Browse Template Library
| Attribute | Value |
|-----------|-------|
| **ID** | US-202 |
| **Title** | Browse Template Library |
| **Priority** | Must Have |
| **Story Points** | 5 |
| **Dependencies** | US-102 |

**Story:**  
As a **user**, I want to **browse a library of pre-built templates**, so that **I can quickly start with common part types**.

**Acceptance Criteria:**

```gherkin
Scenario: View template categories
  Given I am on the template library page
  Then I see templates organized by category:
    | Category      | Example Templates                    |
    | Enclosures    | Project Box, Electronics Enclosure   |
    | Brackets      | L-Bracket, Corner Bracket            |
    | Mechanical    | Gear, Pulley, Bearing Mount          |
    | Fasteners     | Knob, Handle, Standoff               |
    | Organization  | Drawer Divider, Pegboard Hook        |

Scenario: Preview template
  Given I am browsing templates
  When I hover over a template card
  Then I see a 3D preview thumbnail
  And I see the template name and brief description

Scenario: View template details
  Given I am browsing templates
  When I click on a template
  Then I see an interactive 3D preview
  And I see the list of customizable parameters
  And I see the template's tier requirement (Free/Pro)

Scenario: Filter templates by tier
  Given I am a free tier user
  When I filter by "Available to me"
  Then I see only free tier templates
  And Pro templates are shown grayed out with upgrade prompt
```

---

### US-203: Customize Template Parameters
| Attribute | Value |
|-----------|-------|
| **ID** | US-203 |
| **Title** | Template Customization |
| **Priority** | Must Have |
| **Story Points** | 8 |
| **Dependencies** | US-202 |

**Story:**  
As a **user**, I want to **customize template parameters**, so that **the generated part fits my specific needs**.

**Acceptance Criteria:**

```gherkin
Scenario: Adjust dimensions
  Given I have selected the "Project Box" template
  When I change the width from 100mm to 150mm using the slider
  Then the 3D preview updates in real-time
  And dependent parameters (like screw post positions) adjust automatically

Scenario: Add optional features
  Given I have selected a template with optional features
  When I enable "Add ventilation slots"
  And I set slot width to 2mm and spacing to 5mm
  Then the preview shows the ventilation slots
  And I can adjust slot parameters

Scenario: Parameter validation
  Given I am customizing a template
  When I enter a wall thickness of 0.2mm (below minimum)
  Then I see a validation error "Minimum wall thickness is 0.8mm"
  And the preview does not update until a valid value is entered

Scenario: Reset to defaults
  Given I have modified multiple parameters
  When I click "Reset to Defaults"
  Then all parameters return to their default values
  And the preview updates accordingly

Scenario: Save customized template (Pro)
  Given I am a Pro user
  And I have customized a template
  When I click "Save as Template"
  And I enter a name "My Custom Box"
  Then the template is saved to my personal template library
  And I can reuse it for future designs
```

---

### US-204: Receive AI Optimization Suggestions
| Attribute | Value |
|-----------|-------|
| **ID** | US-204 |
| **Title** | AI Optimization Suggestions |
| **Priority** | Should Have |
| **Story Points** | 8 |
| **Dependencies** | US-201, US-203 |

**Story:**  
As a **user**, I want to **receive AI suggestions to improve my design**, so that **my parts are more printable and structurally sound**.

**Acceptance Criteria:**

```gherkin
Scenario: Receive printability suggestions
  Given I have generated a part with steep overhangs
  When generation completes
  Then I see a suggestion panel with:
    | Type | Message | Location |
    | Warning | "Overhang at 55° may require supports" | Highlighted in preview |
  And I can click to zoom to the problem area

Scenario: Receive structural suggestions
  Given I have generated a part with thin walls
  When generation completes
  Then I see suggestions like:
    - "Wall thickness of 0.9mm may be fragile for PLA"
    - "Consider increasing to 1.2mm for better strength"
  And I can click "Apply" to automatically adjust

Scenario: Apply suggestion
  Given I see an optimization suggestion
  When I click "Apply Suggestion"
  Then the design is modified accordingly
  And a new version is created
  And I can compare before/after

Scenario: Dismiss suggestion
  Given I see a suggestion I don't want
  When I click "Dismiss"
  Then the suggestion is hidden
  And I can proceed with export
```

---

### US-205: Modify Design with Natural Language
| Attribute | Value |
|-----------|-------|
| **ID** | US-205 |
| **Title** | Natural Language Design Modification |
| **Priority** | Must Have |
| **Story Points** | 8 |
| **Dependencies** | US-201 |

**Story:**  
As a **user**, I want to **modify my design using natural language commands**, so that **I can iterate without manual CAD work**.

**Acceptance Criteria:**

```gherkin
Scenario: Resize design
  Given I have a generated design
  When I enter "Make it 20% larger"
  And I click "Apply"
  Then the design scales uniformly by 20%
  And I can see the new dimensions

Scenario: Add feature
  Given I have a generated box design
  When I enter "Add a hole for M5 bolt on the top face, centered"
  And I click "Apply"
  Then a 5.5mm hole is added to the top face
  And the hole is centered

Scenario: Remove feature
  Given I have a design with mounting tabs
  When I enter "Remove the tabs on the sides"
  And I click "Apply"
  Then the tabs are removed
  And I see before/after comparison

Scenario: Combine designs
  Given I have two designs in my project
  When I enter "Attach design B to the right side of design A"
  And I select the designs
  And I click "Apply"
  Then the designs are combined
  And I can adjust the attachment position

Scenario: Undo modification
  Given I have applied a modification
  When I click "Undo"
  Then the design reverts to the previous version
  And the modification command is still visible in history
```

---

## 3. File Management

### US-301: Upload STEP/CAD File
| Attribute | Value |
|-----------|-------|
| **ID** | US-301 |
| **Title** | File Upload |
| **Priority** | Must Have |
| **Story Points** | 5 |
| **Dependencies** | US-102 |

**Story:**  
As a **user**, I want to **upload my existing STEP or CAD files**, so that **I can view and modify them in the platform**.

**Acceptance Criteria:**

```gherkin
Scenario: Upload valid STEP file
  Given I am on the upload page
  When I drag and drop a valid .step file under 100MB
  Then I see an upload progress indicator
  And the file is uploaded successfully
  And a 3D preview is generated within 30 seconds

Scenario: Upload via file browser
  Given I am on the upload page
  When I click "Browse Files"
  And I select a .stp file from my computer
  Then the file uploads and is processed

Scenario: Upload invalid file type
  Given I am on the upload page
  When I attempt to upload a .pdf file
  Then I see an error "Unsupported file format. Supported: STEP, STL, OBJ, 3MF"

Scenario: Upload oversized file
  Given I am on the upload page
  When I attempt to upload a 150MB STEP file
  Then I see an error "File exceeds maximum size of 100MB"

Scenario: Handle corrupted file
  Given I upload a STEP file with invalid geometry
  When processing fails
  Then I see an error "Could not parse file. Please check the file is valid."
  And the file is not added to my projects
```

---

### US-302: Preview 3D Models
| Attribute | Value |
|-----------|-------|
| **ID** | US-302 |
| **Title** | 3D Model Preview |
| **Priority** | Must Have |
| **Story Points** | 5 |
| **Dependencies** | US-301, US-201 |

**Story:**  
As a **user**, I want to **interactively preview my 3D models**, so that **I can inspect them from all angles**.

**Acceptance Criteria:**

```gherkin
Scenario: Orbit view
  Given I am viewing a 3D model
  When I click and drag on the model
  Then the view rotates around the model

Scenario: Pan view
  Given I am viewing a 3D model
  When I hold shift and drag
  Then the view pans left/right/up/down

Scenario: Zoom view
  Given I am viewing a 3D model
  When I scroll the mouse wheel
  Then the view zooms in/out

Scenario: Standard views
  Given I am viewing a 3D model
  When I click the view cube or select from menu:
    | View | Camera Position |
    | Front | Looking at front face |
    | Back | Looking at back face |
    | Top | Looking down |
    | Isometric | 45° angle |
  Then the view snaps to that position

Scenario: Render modes
  Given I am viewing a 3D model
  When I toggle render mode:
    | Mode | Appearance |
    | Solid | Opaque surfaces |
    | Wireframe | Edges only |
    | Transparent | Semi-transparent surfaces |
  Then the display updates accordingly

Scenario: Measure distance
  Given I am viewing a 3D model
  When I activate the measure tool
  And I click on two points on the model
  Then the distance between them is displayed in mm
```

---

### US-303: Export Designs
| Attribute | Value |
|-----------|-------|
| **ID** | US-303 |
| **Title** | Export Designs |
| **Priority** | Must Have |
| **Story Points** | 5 |
| **Dependencies** | US-201, US-301 |

**Story:**  
As a **user**, I want to **export my designs in multiple formats**, so that **I can use them in other software or 3D print them**.

**Acceptance Criteria:**

```gherkin
Scenario: Export as STL
  Given I have a completed design
  When I click "Export"
  And I select "STL" format
  And I choose "High" quality
  Then the file is generated and downloaded
  And the file is valid STL with correct geometry

Scenario: Export options
  Given I am on the export dialog
  Then I see options for:
    | Format | Options |
    | STL | Quality (Low/Medium/High), Binary/ASCII |
    | STEP | AP203/AP214 |
    | OBJ | Include materials, Coordinate system |
    | 3MF | Include print settings |

Scenario: Export with unit conversion
  Given my design is in millimeters
  When I export and select "Inches" as output unit
  Then the exported file dimensions are converted to inches

Scenario: Batch export
  Given I have multiple designs in a project
  When I select multiple designs
  And I click "Export Selected"
  Then I can export all as a ZIP file
```

---

### US-304: Version History
| Attribute | Value |
|-----------|-------|
| **ID** | US-304 |
| **Title** | Design Version History |
| **Priority** | Should Have |
| **Story Points** | 5 |
| **Dependencies** | US-205 |

**Story:**  
As a **user**, I want to **access previous versions of my design**, so that **I can revert changes if needed**.

**Acceptance Criteria:**

```gherkin
Scenario: View version history
  Given I have a design with multiple versions
  When I click "Version History"
  Then I see a list of versions with:
    - Version number
    - Timestamp
    - Change description
    - Thumbnail

Scenario: Preview previous version
  Given I am viewing version history
  When I click on a previous version
  Then I see a 3D preview of that version
  And the current version remains unchanged

Scenario: Restore previous version
  Given I am viewing a previous version
  When I click "Restore This Version"
  Then a new version is created matching the old one
  And this becomes the current version
  And the previous version is preserved

Scenario: Compare versions
  Given I have multiple versions
  When I select two versions to compare
  Then I see side-by-side 3D previews
  And differences are highlighted if possible
```

---

### US-305: Trash Bin
| Attribute | Value |
|-----------|-------|
| **ID** | US-305 |
| **Title** | Trash Bin |
| **Priority** | Should Have |
| **Story Points** | 3 |
| **Dependencies** | US-102 |

**Story:**  
As a **user**, I want to **recover accidentally deleted designs from trash**, so that **I don't lose work due to mistakes**.

**Acceptance Criteria:**

```gherkin
Scenario: Delete design to trash
  Given I have a design I want to delete
  When I click "Delete"
  Then the design is moved to Trash
  And I see confirmation "Moved to Trash"
  And I can undo immediately

Scenario: View trash
  Given I have deleted designs
  When I navigate to Trash
  Then I see all deleted items with:
    - Name
    - Deleted date
    - Days until permanent deletion

Scenario: Restore from trash
  Given I have a design in Trash
  When I click "Restore"
  Then the design is moved back to its original project
  And I can access it normally

Scenario: Permanent delete
  Given I have a design in Trash
  When I click "Delete Permanently"
  And I confirm the action
  Then the design is permanently removed
  And it cannot be recovered

Scenario: Automatic cleanup
  Given a design has been in Trash for 30 days (Pro) or 14 days (Free)
  When the retention period expires
  Then the design is permanently deleted
  And I receive an email notification 3 days before
```

---

## 4. Queue & Job Processing

### US-401: Submit Generation Job
| Attribute | Value |
|-----------|-------|
| **ID** | US-401 |
| **Title** | Job Submission |
| **Priority** | Must Have |
| **Story Points** | 5 |
| **Dependencies** | US-201 |

**Story:**  
As a **user**, I want to **submit design jobs to a queue**, so that **my requests are processed asynchronously**.

**Acceptance Criteria:**

```gherkin
Scenario: Submit job successfully
  Given I have entered a design description
  When I click "Generate"
  Then a job is created and added to the queue
  And I receive a job ID
  And I see my queue position

Scenario: Job queued notification
  Given my job is in the queue
  Then I see estimated wait time
  And I can continue using the application

Scenario: Reject job when at limit
  Given I am a free user with 3 jobs already queued
  When I try to submit another job
  Then I see "Queue limit reached. Please wait for jobs to complete."
  And I am not charged for the rejected job
```

---

### US-402: Track Job Status
| Attribute | Value |
|-----------|-------|
| **ID** | US-402 |
| **Title** | Job Status Tracking |
| **Priority** | Must Have |
| **Story Points** | 5 |
| **Dependencies** | US-401 |

**Story:**  
As a **user**, I want to **track the status of my generation jobs**, so that **I know when they will complete**.

**Acceptance Criteria:**

```gherkin
Scenario: View job status
  Given I have submitted a job
  When I view my active jobs
  Then I see:
    | Status | Information Shown |
    | Queued | Queue position, estimated wait |
    | Processing | Progress percentage, ETA |
    | Completed | Preview, duration |
    | Failed | Error message, retry option |

Scenario: Real-time updates
  Given I am viewing a job in progress
  Then the status updates without page refresh
  And progress updates at least every 5 seconds

Scenario: Email notification
  Given I have enabled email notifications
  And my job completes
  Then I receive an email with:
    - Job completion status
    - Link to view result
    - Preview thumbnail
```

---

### US-403: Priority Queue
| Attribute | Value |
|-----------|-------|
| **ID** | US-403 |
| **Title** | Priority Queue for Paid Users |
| **Priority** | Must Have |
| **Story Points** | 5 |
| **Dependencies** | US-401 |

**Story:**  
As a **Pro subscriber**, I want my **jobs to be processed with priority**, so that **I get faster results than free users**.

**Acceptance Criteria:**

```gherkin
Scenario: Pro user queue priority
  Given I am a Pro subscriber
  When I submit a job
  Then my job is placed in the priority queue
  And I see "Priority" badge on my job

Scenario: Priority queue processing
  Given the queue has:
    - 10 free tier jobs
    - 2 Pro tier jobs
  When a worker becomes available
  Then the Pro tier job is processed first

Scenario: Display tier benefits
  Given I am a free user viewing queue position
  Then I see a message "Upgrade to Pro for priority processing"
  And I see estimated time savings
```

---

### US-404: Cancel Job
| Attribute | Value |
|-----------|-------|
| **ID** | US-404 |
| **Title** | Cancel Queued Job |
| **Priority** | Should Have |
| **Story Points** | 2 |
| **Dependencies** | US-401 |

**Story:**  
As a **user**, I want to **cancel a queued job**, so that **I can free up my queue slot**.

**Acceptance Criteria:**

```gherkin
Scenario: Cancel queued job
  Given I have a job in "Queued" status
  When I click "Cancel"
  Then the job is removed from the queue
  And my queue slot is freed
  And the job is not counted against my quota

Scenario: Cannot cancel processing job
  Given my job is in "Processing" status
  Then the cancel button is disabled
  And I see "Cannot cancel jobs in progress"
```

---

## 5. Dashboard & Projects

### US-501: View Dashboard
| Attribute | Value |
|-----------|-------|
| **ID** | US-501 |
| **Title** | User Dashboard |
| **Priority** | Must Have |
| **Story Points** | 5 |
| **Dependencies** | US-102 |

**Story:**  
As a **logged-in user**, I want to **see a personalized dashboard**, so that **I can quickly access my work and status**.

**Acceptance Criteria:**

```gherkin
Scenario: View dashboard sections
  Given I am logged in
  When I navigate to the dashboard
  Then I see:
    - Quick actions (New design, Upload, Templates)
    - Recent projects (last 10)
    - Active jobs with status
    - Usage statistics

Scenario: Quick actions
  Given I am on the dashboard
  When I click "New Design"
  Then I am taken to the design creation page

Scenario: Recent projects
  Given I have created designs
  When I view the dashboard
  Then I see my 10 most recent projects
  With thumbnail, name, last modified date
  And I can click to open any project

Scenario: Empty state
  Given I am a new user with no designs
  When I view the dashboard
  Then I see a welcome message
  And suggestions to get started
```

---

### US-502: Organize Projects
| Attribute | Value |
|-----------|-------|
| **ID** | US-502 |
| **Title** | Project Organization |
| **Priority** | Should Have |
| **Story Points** | 5 |
| **Dependencies** | US-501 |

**Story:**  
As a **user**, I want to **organize my designs into projects/folders**, so that **I can manage my work efficiently**.

**Acceptance Criteria:**

```gherkin
Scenario: Create project
  Given I am on the projects page
  When I click "New Project"
  And I enter name "Electronics Enclosures"
  Then the project is created
  And I can add designs to it

Scenario: Move design to project
  Given I have a design in "My Designs"
  When I drag the design to a project folder
  Or right-click and select "Move to" > "Electronics Enclosures"
  Then the design is moved to that project

Scenario: Rename project
  Given I have a project
  When I right-click and select "Rename"
  And I enter a new name
  Then the project is renamed

Scenario: Delete empty project
  Given I have an empty project
  When I delete it
  Then the project is removed

Scenario: Delete project with designs
  Given I have a project containing designs
  When I delete the project
  Then I am asked what to do with designs:
    - Move to "My Designs"
    - Delete all designs
```

---

### US-503: Search Designs
| Attribute | Value |
|-----------|-------|
| **ID** | US-503 |
| **Title** | Search Designs |
| **Priority** | Should Have |
| **Story Points** | 3 |
| **Dependencies** | US-501 |

**Story:**  
As a **user with many designs**, I want to **search for specific designs**, so that **I can find them quickly**.

**Acceptance Criteria:**

```gherkin
Scenario: Search by name
  Given I have many designs
  When I type "bracket" in the search box
  Then I see all designs with "bracket" in the name

Scenario: Search by description
  Given I have designs with descriptions
  When I search for "M5 bolt"
  Then I see designs where description contains "M5 bolt"

Scenario: Filter results
  Given I have search results
  When I filter by:
    - Date range
    - Project
    - Source (generated/uploaded)
  Then results are filtered accordingly

Scenario: No results
  Given I search for "xyz123nonexistent"
  Then I see "No designs found"
  And suggestions to create a new design
```

---

## 6. Subscription & Billing

### US-601: View Subscription Tiers
| Attribute | Value |
|-----------|-------|
| **ID** | US-601 |
| **Title** | View Subscription Options |
| **Priority** | Must Have |
| **Story Points** | 2 |
| **Dependencies** | None |

**Story:**  
As a **visitor or user**, I want to **see the available subscription tiers and their features**, so that **I can choose the right plan**.

**Acceptance Criteria:**

```gherkin
Scenario: View pricing page
  Given I am on the pricing page
  Then I see comparison of tiers:
    | Feature | Free | Pro ($19/mo) | Enterprise |
    | Generations/month | 10 | Unlimited | Unlimited |
    | Queue priority | Standard | Priority | Highest |
    | Templates | Basic | All | All + Custom |
    | Storage | 500MB | 10GB | Unlimited |
    | Support | Community | Email | Dedicated |

Scenario: Current plan indicator
  Given I am a Pro subscriber
  When I view pricing
  Then the Pro tier is highlighted as "Current Plan"
```

---

### US-602: Upgrade Subscription
| Attribute | Value |
|-----------|-------|
| **ID** | US-602 |
| **Title** | Upgrade Subscription |
| **Priority** | Must Have |
| **Story Points** | 5 |
| **Dependencies** | US-601 |

**Story:**  
As a **free user**, I want to **upgrade to a paid subscription**, so that **I can access more features**.

**Acceptance Criteria:**

```gherkin
Scenario: Upgrade to Pro
  Given I am a free user
  When I click "Upgrade to Pro"
  And I enter my payment information
  And I confirm the purchase
  Then my subscription is upgraded immediately
  And I receive a confirmation email
  And Pro features are available

Scenario: Secure payment
  Given I am on the checkout page
  Then payment is processed via secure gateway (Stripe)
  And I see security badges
  And my card is not stored unless I opt in

Scenario: Proration
  Given I am upgrading mid-billing cycle
  Then I am charged a prorated amount
  And I see the calculation explained
```

---

### US-603: Manage Subscription
| Attribute | Value |
|-----------|-------|
| **ID** | US-603 |
| **Title** | Manage Subscription |
| **Priority** | Must Have |
| **Story Points** | 3 |
| **Dependencies** | US-602 |

**Story:**  
As a **paying subscriber**, I want to **manage my subscription**, so that **I can update payment method or cancel**.

**Acceptance Criteria:**

```gherkin
Scenario: Update payment method
  Given I have an active subscription
  When I go to billing settings
  And I add a new card
  Then the new card becomes the default payment method

Scenario: View billing history
  Given I have an active subscription
  When I view billing history
  Then I see all past invoices
  And I can download each as PDF

Scenario: Cancel subscription
  Given I have an active subscription
  When I click "Cancel Subscription"
  Then I see what I'll lose (features, queue priority)
  And I can confirm cancellation
  And subscription remains active until end of billing period

Scenario: Reactivate subscription
  Given I have a cancelled subscription still in active period
  When I click "Reactivate"
  Then my subscription continues without interruption
```

---

## 7. Collaboration & Sharing

### US-701: Share Design
| Attribute | Value |
|-----------|-------|
| **ID** | US-701 |
| **Title** | Share Design |
| **Priority** | Should Have |
| **Story Points** | 5 |
| **Dependencies** | US-201 |

**Story:**  
As a **user**, I want to **share my design with others**, so that **they can view or collaborate on it**.

**Acceptance Criteria:**

```gherkin
Scenario: Generate share link
  Given I have a design
  When I click "Share"
  And I select "Anyone with link can view"
  Then a shareable URL is generated
  And I can copy it to clipboard

Scenario: Share with specific user
  Given I have a design
  When I click "Share"
  And I enter an email address
  And I select permission level (View/Edit)
  Then that user receives an email invitation
  And they can access the design with appropriate permissions

Scenario: View shared designs
  Given someone has shared a design with me
  When I go to "Shared with Me"
  Then I see the design with the sharer's name
  And I can access it according to my permissions

Scenario: Revoke access
  Given I have shared a design
  When I go to sharing settings
  And I remove a user or disable link sharing
  Then that access is revoked immediately
```

---

### US-702: Comment on Designs
| Attribute | Value |
|-----------|-------|
| **ID** | US-702 |
| **Title** | Design Comments |
| **Priority** | Could Have |
| **Story Points** | 5 |
| **Dependencies** | US-701 |

**Story:**  
As a **collaborator**, I want to **leave comments on a design**, so that **we can discuss changes**.

**Acceptance Criteria:**

```gherkin
Scenario: Add comment
  Given I have access to a shared design
  When I click on the design preview
  And I type a comment
  And I click "Post"
  Then the comment is attached to that location
  And other collaborators can see it

Scenario: Reply to comment
  Given there is a comment on a design
  When I click "Reply"
  And I type my response
  Then the reply is threaded under the original comment

Scenario: Resolve comment
  Given there is a comment thread
  When I click "Resolve"
  Then the comment is marked as resolved
  And it can be hidden from view
```

---

## 8. Administration

### US-801: Admin Dashboard
| Attribute | Value |
|-----------|-------|
| **ID** | US-801 |
| **Title** | Admin Dashboard |
| **Priority** | Should Have |
| **Story Points** | 5 |
| **Dependencies** | US-102 |

**Story:**  
As an **admin**, I want to **view platform statistics and health**, so that **I can monitor the system**.

**Acceptance Criteria:**

```gherkin
Scenario: View platform metrics
  Given I am logged in as admin
  When I access the admin dashboard
  Then I see:
    - Total users (active, new today)
    - Jobs processed (today, this week)
    - Queue status (length, wait times)
    - System health indicators

Scenario: View charts
  Given I am on the admin dashboard
  Then I see trend charts for:
    - User signups over time
    - Job volume over time
    - Revenue (if applicable)
```

---

### US-802: Moderate Flagged Content
| Attribute | Value |
|-----------|-------|
| **ID** | US-802 |
| **Title** | Content Moderation |
| **Priority** | Must Have |
| **Story Points** | 5 |
| **Dependencies** | US-601 |

**Story:**  
As an **admin**, I want to **review flagged content**, so that **I can enforce platform policies**.

**Acceptance Criteria:**

```gherkin
Scenario: View moderation queue
  Given there are flagged items
  When I access the moderation queue
  Then I see items sorted by severity
  With flag reason, user info, content preview

Scenario: Approve content
  Given I am reviewing a flagged item
  When I determine it's acceptable
  And I click "Approve"
  Then the item is released
  And the user is notified if applicable
  And ML model is updated

Scenario: Reject content
  Given I am reviewing a flagged item
  When I determine it violates policies
  And I click "Reject"
  And I select a reason
  Then the content is deleted
  And the user receives a warning

Scenario: Suspend user
  Given a user has multiple violations
  When I click "Suspend User"
  And I enter the suspension reason and duration
  Then the user's account is suspended
  And they receive notification
  And they cannot log in
```

---

### US-803: Manage Users
| Attribute | Value |
|-----------|-------|
| **ID** | US-803 |
| **Title** | User Management |
| **Priority** | Should Have |
| **Story Points** | 5 |
| **Dependencies** | US-801 |

**Story:**  
As an **admin**, I want to **manage user accounts**, so that **I can provide support and enforce policies**.

**Acceptance Criteria:**

```gherkin
Scenario: Search users
  Given I am in user management
  When I search for "john@example.com"
  Then I see the user's account details

Scenario: View user details
  Given I have found a user
  Then I see:
    - Account info
    - Subscription status
    - Usage statistics
    - Activity history
    - Violation history

Scenario: Impersonate user (for support)
  Given I need to troubleshoot a user's issue
  When I click "Impersonate" with approval
  Then I see the platform as that user
  And all actions are logged
  And I can exit impersonation anytime

Scenario: Adjust subscription
  Given I need to apply a credit or adjustment
  When I modify the user's subscription
  Then the change is applied
  And it's logged with reason
```

---

## Story Summary by Epic

| Epic | Must Have | Should Have | Could Have | Total |
|------|-----------|-------------|------------|-------|
| Authentication | 4 | 2 | 0 | 6 |
| Part Design | 4 | 1 | 0 | 5 |
| File Management | 3 | 2 | 0 | 5 |
| Queue & Jobs | 3 | 1 | 0 | 4 |
| Dashboard | 1 | 2 | 0 | 3 |
| Subscription | 3 | 0 | 0 | 3 |
| Collaboration | 0 | 1 | 1 | 2 |
| Administration | 1 | 2 | 0 | 3 |
| **Total** | **19** | **11** | **1** | **31** |

---

## Appendix: Story Dependencies Graph

```
US-101 (Registration)
    ├── US-102 (Login)
    │       ├── US-104 (Profile)
    │       ├── US-105 (Delete Account)
    │       ├── US-201 (NL Generation)
    │       │       ├── US-204 (Suggestions)
    │       │       ├── US-205 (Modifications)
    │       │       ├── US-401 (Job Submit)
    │       │       │       ├── US-402 (Job Status)
    │       │       │       ├── US-403 (Priority Queue)
    │       │       │       └── US-404 (Cancel Job)
    │       │       └── US-303 (Export)
    │       ├── US-202 (Templates)
    │       │       └── US-203 (Customize)
    │       ├── US-301 (Upload)
    │       │       └── US-302 (Preview)
    │       ├── US-304 (Versions)
    │       ├── US-305 (Trash)
    │       ├── US-501 (Dashboard)
    │       │       ├── US-502 (Projects)
    │       │       └── US-503 (Search)
    │       ├── US-602 (Upgrade)
    │       │       └── US-603 (Manage Sub)
    │       ├── US-701 (Share)
    │       │       └── US-702 (Comments)
    │       └── US-801 (Admin Dashboard)
    │               ├── US-802 (Moderation)
    │               └── US-803 (User Mgmt)
    └── US-103 (Password Reset)
```

---

*End of Document*
