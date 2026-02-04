#!/bin/bash
#
# GitHub Issues Creation Script
# Generated from user story markdown files
#
# Prerequisites:
#   - gh CLI installed and authenticated
#   - Run from repository root directory
#

set -e  # Exit on error

REPO='jmassardo/ai-part-designer'
EPIC_PREFIX='EPIC'

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Creating GitHub issues from user stories...${NC}"
echo ""

# Store epic issue numbers
declare -A EPIC_NUMBERS

# Function to create an epic issue
create_epic() {
  local title="$1"
  local description="$2"
  local category_key="$3"
  
  echo -e "${BLUE}Creating epic: $title${NC}"
  
  ISSUE_URL=$(gh issue create \
    --repo "$REPO" \
    --title "[EPIC] $title" \
    --body "$description" \
    --label "epic,planning" | tail -n 1)
  
  ISSUE_NUMBER=$(echo "$ISSUE_URL" | grep -oP '\d+$')
  EPIC_NUMBERS["$category_key"]="$ISSUE_NUMBER"
  
  echo -e "${GREEN}✓ Created epic #$ISSUE_NUMBER${NC}"
  echo ""
}

# Function to create a user story issue
create_user_story() {
  local story_id="$1"
  local title="$2"
  local body="$3"
  local epic_number="$4"
  
  echo -e "Creating user story: $story_id - $title"
  
  # Create the issue
  ISSUE_URL=$(gh issue create \
    --repo "$REPO" \
    --title "[$story_id] $title" \
    --body "$body" | tail -n 1)
  
  ISSUE_NUMBER=$(echo "$ISSUE_URL" | grep -oP '\d+$')
  
  # Link to epic if epic number is provided
  if [ -n "$epic_number" ] && [ "$epic_number" != "0" ]; then
    # Add a comment linking to the epic
    gh issue comment "$ISSUE_NUMBER" \
      --repo "$REPO" \
      --body "Part of epic #$epic_number"
    
    # Add a comment to the epic with the story
    gh issue comment "$epic_number" \
      --repo "$REPO" \
      --body "- #$ISSUE_NUMBER - $story_id: $title"
  fi
  
  echo -e "${GREEN}✓ Created issue #$ISSUE_NUMBER${NC}"
}

##############################################################################
# EPIC ISSUES
##############################################################################

# Epic: AI Dimension Extraction
create_epic \
  "AI Dimension Extraction" \
  "# AI Dimension Extraction

This epic tracks all user stories related to ai dimension extraction.

## User Stories

This epic contains 3 user stories:

- [ ] US-3001
- [ ] US-3002
- [ ] US-3003

## Progress

Track progress as individual user story issues are completed.
" \
  "ai_dimension_extraction"

# Epic: AI Intelligence Improvements
create_epic \
  "AI Intelligence Improvements" \
  "# AI Intelligence Improvements

This epic tracks all user stories related to ai intelligence improvements.

## User Stories

This epic contains 5 user stories:

- [ ] US-14001
- [ ] US-14002
- [ ] US-14003
- [ ] US-14004
- [ ] US-14005

## Progress

Track progress as individual user story issues are completed.
" \
  "ai_intelligence_improvements"

# Epic: AI Performance & Manufacturing
create_epic \
  "AI Performance & Manufacturing" \
  "# AI Performance & Manufacturing

This epic tracks all user stories related to ai performance & manufacturing.

## User Stories

This epic contains 7 user stories:

- [ ] US-15001
- [ ] US-15002
- [ ] US-15003
- [ ] US-15004
- [ ] US-15005
- [ ] US-15006
- [ ] US-15007

## Progress

Track progress as individual user story issues are completed.
" \
  "ai_performance_manufacturing"

# Epic: AI Personalization
create_epic \
  "AI Personalization" \
  "# AI Personalization

This epic tracks all user stories related to ai personalization.

## User Stories

This epic contains 5 user stories:

- [ ] US-19001
- [ ] US-19002
- [ ] US-19003
- [ ] US-19004
- [ ] US-19005

## Progress

Track progress as individual user story issues are completed.
" \
  "ai_personalization"

# Epic: AI Slash Commands
create_epic \
  "AI Slash Commands" \
  "# AI Slash Commands

This epic tracks all user stories related to ai slash commands.

## User Stories

This epic contains 3 user stories:

- [ ] US-13001
- [ ] US-13002
- [ ] US-13003

## Progress

Track progress as individual user story issues are completed.
" \
  "ai_slash_commands"

# Epic: Admin Dashboard
create_epic \
  "Admin Dashboard" \
  "# Admin Dashboard

This epic tracks all user stories related to admin dashboard.

## User Stories

This epic contains 5 user stories:

- [ ] US-20001
- [ ] US-20002
- [ ] US-20003
- [ ] US-20004
- [ ] US-20005

## Progress

Track progress as individual user story issues are completed.
" \
  "admin_dashboard"

# Epic: Administration
create_epic \
  "Administration" \
  "# Administration

This epic tracks all user stories related to administration.

## User Stories

This epic contains 3 user stories:

- [ ] US-801
- [ ] US-802
- [ ] US-803

## Progress

Track progress as individual user story issues are completed.
" \
  "administration"

# Epic: Chat History & Privacy
create_epic \
  "Chat History & Privacy" \
  "# Chat History & Privacy

This epic tracks all user stories related to chat history & privacy.

## User Stories

This epic contains 6 user stories:

- [ ] US-17001
- [ ] US-17002
- [ ] US-17003
- [ ] US-17004
- [ ] US-17005
- [ ] US-17006

## Progress

Track progress as individual user story issues are completed.
" \
  "chat_history_privacy"

# Epic: Chat-Style Generation Experience
create_epic \
  "Chat-Style Generation Experience" \
  "# Chat-Style Generation Experience

This epic tracks all user stories related to chat-style generation experience.

## User Stories

This epic contains 2 user stories:

- [ ] US-1001
- [ ] US-1002

## Progress

Track progress as individual user story issues are completed.
" \
  "chat-style_generation_experience"

# Epic: Collaboration & Sharing
create_epic \
  "Collaboration & Sharing" \
  "# Collaboration & Sharing

This epic tracks all user stories related to collaboration & sharing.

## User Stories

This epic contains 2 user stories:

- [ ] US-701
- [ ] US-702

## Progress

Track progress as individual user story issues are completed.
" \
  "collaboration_sharing"

# Epic: Collaboration Features
create_epic \
  "Collaboration Features" \
  "# Collaboration Features

This epic tracks all user stories related to collaboration features.

## User Stories

This epic contains 3 user stories:

- [ ] US-9001
- [ ] US-9002
- [ ] US-9003

## Progress

Track progress as individual user story issues are completed.
" \
  "collaboration_features"

# Epic: Component File Management
create_epic \
  "Component File Management" \
  "# Component File Management

This epic tracks all user stories related to component file management.

## User Stories

This epic contains 3 user stories:

- [ ] US-2001
- [ ] US-1002
- [ ] US-1003

## Progress

Track progress as individual user story issues are completed.
" \
  "component_file_management"

# Epic: Dashboard & Projects
create_epic \
  "Dashboard & Projects" \
  "# Dashboard & Projects

This epic tracks all user stories related to dashboard & projects.

## User Stories

This epic contains 3 user stories:

- [ ] US-501
- [ ] US-502
- [ ] US-503

## Progress

Track progress as individual user story issues are completed.
" \
  "dashboard_projects"

# Epic: Design System & Theming
create_epic \
  "Design System & Theming" \
  "# Design System & Theming

This epic tracks all user stories related to design system & theming.

## User Stories

This epic contains 5 user stories:

- [ ] US-16001
- [ ] US-16002
- [ ] US-16003
- [ ] US-16004
- [ ] US-16005

## Progress

Track progress as individual user story issues are completed.
" \
  "design_system_theming"

# Epic: Enclosure Style Templates
create_epic \
  "Enclosure Style Templates" \
  "# Enclosure Style Templates

This epic tracks all user stories related to enclosure style templates.

## User Stories

This epic contains 4 user stories:

- [ ] US-4001
- [ ] US-4002
- [ ] US-4003
- [ ] US-4004

## Progress

Track progress as individual user story issues are completed.
" \
  "enclosure_style_templates"

# Epic: File Alignment & CAD Combination
create_epic \
  "File Alignment & CAD Combination" \
  "# File Alignment & CAD Combination

This epic tracks all user stories related to file alignment & cad combination.

## User Stories

This epic contains 3 user stories:

- [ ] US-2001
- [ ] US-2002
- [ ] US-2003

## Progress

Track progress as individual user story issues are completed.
" \
  "file_alignment_cad_combination"

# Epic: File Management
create_epic \
  "File Management" \
  "# File Management

This epic tracks all user stories related to file management.

## User Stories

This epic contains 5 user stories:

- [ ] US-301
- [ ] US-302
- [ ] US-303
- [ ] US-304
- [ ] US-305

## Progress

Track progress as individual user story issues are completed.
" \
  "file_management"

# Epic: Layout Editor Enhancements
create_epic \
  "Layout Editor Enhancements" \
  "# Layout Editor Enhancements

This epic tracks all user stories related to layout editor enhancements.

## User Stories

This epic contains 3 user stories:

- [ ] US-11001
- [ ] US-11002
- [ ] US-11003

## Progress

Track progress as individual user story issues are completed.
" \
  "layout_editor_enhancements"

# Epic: Logging & Audit
create_epic \
  "Logging & Audit" \
  "# Logging & Audit

This epic tracks all user stories related to logging & audit.

## User Stories

This epic contains 4 user stories:

- [ ] US-21001
- [ ] US-21002
- [ ] US-21003
- [ ] US-21004

## Progress

Track progress as individual user story issues are completed.
" \
  "logging_audit"

# Epic: Mobile Application
create_epic \
  "Mobile Application" \
  "# Mobile Application

This epic tracks all user stories related to mobile application.

## User Stories

This epic contains 4 user stories:

- [ ] US-24001
- [ ] US-24002
- [ ] US-24003
- [ ] US-24004

## Progress

Track progress as individual user story issues are completed.
" \
  "mobile_application"

# Epic: Mounting Type Expansion
create_epic \
  "Mounting Type Expansion" \
  "# Mounting Type Expansion

This epic tracks all user stories related to mounting type expansion.

## User Stories

This epic contains 4 user stories:

- [ ] US-5001
- [ ] US-5002
- [ ] US-5003
- [ ] US-5004

## Progress

Track progress as individual user story issues are completed.
" \
  "mounting_type_expansion"

# Epic: Multi-Language Support
create_epic \
  "Multi-Language Support" \
  "# Multi-Language Support

This epic tracks all user stories related to multi-language support.

## User Stories

This epic contains 2 user stories:

- [ ] US-23001
- [ ] US-23002

## Progress

Track progress as individual user story issues are completed.
" \
  "multi-language_support"

# Epic: OAuth Authentication
create_epic \
  "OAuth Authentication" \
  "# OAuth Authentication

This epic tracks all user stories related to oauth authentication.

## User Stories

This epic contains 3 user stories:

- [ ] US-7001
- [ ] US-7002
- [ ] US-7003

## Progress

Track progress as individual user story issues are completed.
" \
  "oauth_authentication"

# Epic: Onboarding Experience
create_epic \
  "Onboarding Experience" \
  "# Onboarding Experience

This epic tracks all user stories related to onboarding experience.

## User Stories

This epic contains 2 user stories:

- [ ] US-10001
- [ ] US-10002

## Progress

Track progress as individual user story issues are completed.
" \
  "onboarding_experience"

# Epic: Part Design & Generation
create_epic \
  "Part Design & Generation" \
  "# Part Design & Generation

This epic tracks all user stories related to part design & generation.

## User Stories

This epic contains 5 user stories:

- [ ] US-201
- [ ] US-202
- [ ] US-203
- [ ] US-204
- [ ] US-205

## Progress

Track progress as individual user story issues are completed.
" \
  "part_design_generation"

# Epic: Payment & Subscription
create_epic \
  "Payment & Subscription" \
  "# Payment & Subscription

This epic tracks all user stories related to payment & subscription.

## User Stories

This epic contains 4 user stories:

- [ ] US-6001
- [ ] US-6002
- [ ] US-6003
- [ ] US-6004

## Progress

Track progress as individual user story issues are completed.
" \
  "payment_subscription"

# Epic: Progressive Web App
create_epic \
  "Progressive Web App" \
  "# Progressive Web App

This epic tracks all user stories related to progressive web app.

## User Stories

This epic contains 3 user stories:

- [ ] US-25001
- [ ] US-25002
- [ ] US-25003

## Progress

Track progress as individual user story issues are completed.
" \
  "progressive_web_app"

# Epic: Queue & Job Processing
create_epic \
  "Queue & Job Processing" \
  "# Queue & Job Processing

This epic tracks all user stories related to queue & job processing.

## User Stories

This epic contains 4 user stories:

- [ ] US-401
- [ ] US-402
- [ ] US-403
- [ ] US-404

## Progress

Track progress as individual user story issues are completed.
" \
  "queue_job_processing"

# Epic: Real-time Updates
create_epic \
  "Real-time Updates" \
  "# Real-time Updates

This epic tracks all user stories related to real-time updates.

## User Stories

This epic contains 2 user stories:

- [ ] US-8001
- [ ] US-8002

## Progress

Track progress as individual user story issues are completed.
" \
  "real-time_updates"

# Epic: Response Rating & Feedback
create_epic \
  "Response Rating & Feedback" \
  "# Response Rating & Feedback

This epic tracks all user stories related to response rating & feedback.

## User Stories

This epic contains 4 user stories:

- [ ] US-18001
- [ ] US-18002
- [ ] US-18003
- [ ] US-18004

## Progress

Track progress as individual user story issues are completed.
" \
  "response_rating_feedback"

# Epic: Sharing & Social
create_epic \
  "Sharing & Social" \
  "# Sharing & Social

This epic tracks all user stories related to sharing & social.

## User Stories

This epic contains 4 user stories:

- [ ] US-22001
- [ ] US-22002
- [ ] US-22003
- [ ] US-22004

## Progress

Track progress as individual user story issues are completed.
" \
  "sharing_social"

# Epic: Subscription & Billing
create_epic \
  "Subscription & Billing" \
  "# Subscription & Billing

This epic tracks all user stories related to subscription & billing.

## User Stories

This epic contains 3 user stories:

- [ ] US-601
- [ ] US-602
- [ ] US-603

## Progress

Track progress as individual user story issues are completed.
" \
  "subscription_billing"

# Epic: User Authentication & Account Management
create_epic \
  "User Authentication & Account Management" \
  "# User Authentication & Account Management

This epic tracks all user stories related to user authentication & account management.

## User Stories

This epic contains 5 user stories:

- [ ] US-101
- [ ] US-102
- [ ] US-103
- [ ] US-104
- [ ] US-105

## Progress

Track progress as individual user story issues are completed.
" \
  "user_authentication_account_management"

##############################################################################
# USER STORY ISSUES
##############################################################################

# US-10001: Complete Onboarding Tutorial
create_user_story \
  "US-10001" \
  "Complete Onboarding Tutorial" \
  "## User Story

As anew user,  
**I want** a guided introduction to the platform,  
**So that** I can quickly learn how to use the key features.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Start onboarding on first login
  Given I just created my account
  When I complete email verification
  And I am redirected to the dashboard
  Then the onboarding overlay appears
  And I see \"Welcome to AI Part Designer!\"

Scenario: Progress through onboarding steps
  Given I am on onboarding step 1
  When I click \"Next\"
  Then I see step 2 with a highlighted UI element
  And the progress indicator shows 2/6

Scenario: Skip onboarding
  Given I am in the onboarding flow
  When I click \"Skip for now\"
  Then onboarding closes
  And I see the regular dashboard
  And \"Resume Tutorial\" appears in help menu

Scenario: Resume onboarding later
  Given I previously skipped onboarding at step 3
  When I click \"Resume Tutorial\" in help menu
  Then onboarding resumes at step 3
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Onboarding Experience

## Labels

\`user-story\`, \`should-have\`, \`onboarding-experience\`
" \
  "${EPIC_NUMBERS[onboarding_experience]}"

# US-10002: Track Onboarding Completion
create_user_story \
  "US-10002" \
  "Track Onboarding Completion" \
  "## User Story

As aplatform operator,  
**I want** to track onboarding completion rates,  
**So that** I can optimize the new user experience.

## Acceptance Criteria

- [ ] User model has \`onboarding_completed\` boolean
- [ ] Timestamp stored when onboarding completed
- [ ] Analytics event fired on each step
- [ ] Drop-off can be analyzed by step

## Details

- **Priority:** Should Have
- **Story Points:** 2
- **Dependencies:** None
- **Category:** Onboarding Experience

## Labels

\`user-story\`, \`should-have\`, \`onboarding-experience\`
" \
  "${EPIC_NUMBERS[onboarding_experience]}"

# US-1001: Iterative Design Chat Interface
create_user_story \
  "US-1001" \
  "Iterative Design Chat Interface" \
  "## User Story

As auser refining my enclosure design,  
**I want** a chat-like interface for iterative generation,  
**So that** I can refine my design through conversation rather than starting over.

## Acceptance Criteria

\`\`\`gherkin
Scenario: First-time generation shows example prompts
  Given I am on the generation page
  And I have not generated any designs yet
  Then I see a list of example prompts
  And I see an input field at the bottom
  And the button says \"Generate\"

Scenario: Example prompts hidden after first generation
  Given I am on the generation page
  When I submit a prompt and generation completes
  Then the example prompts div is hidden
  And I see my prompt in a chat bubble (user style)
  And I see the generation result in a chat bubble (assistant style)

Scenario: Chat interface after generation
  Given I have generated at least one design
  Then I see a scrollable history of prompts and responses
  And the input field is fixed at the bottom
  And the button says \"Regenerate\"
  And the placeholder text says \"Describe changes to your design...\"

Scenario: Submit with keyboard
  Given I am in the chat input field
  When I type a prompt and press Enter
  Then the prompt is submitted
  And Shift+Enter creates a new line instead
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Chat-Style Generation Experience

## Labels

\`user-story\`, \`must-have\`, \`chat-style-generation-experience\`
" \
  "${EPIC_NUMBERS[chat-style_generation_experience]}"

# US-1002: Generation Thumbnails in Chat
create_user_story \
  "US-1002" \
  "Generation Thumbnails in Chat" \
  "## User Story

As auser viewing my generation history,  
**I want** to see thumbnails of each generated design in the chat,  
**So that** I can visually compare iterations.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Thumbnail in response bubble
  Given I have generated a design
  Then the assistant message shows a thumbnail
  And clicking the thumbnail opens the full 3D viewer

Scenario: Multiple iterations visible
  Given I have generated 3 iterations
  Then I can scroll up to see all 3 thumbnails
  And each has a \"View full design\" link
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Chat-Style Generation Experience

## Labels

\`user-story\`, \`must-have\`, \`chat-style-generation-experience\`
" \
  "${EPIC_NUMBERS[chat-style_generation_experience]}"

# US-1002: Replace Datasheet PDF for Component
create_user_story \
  "US-1002" \
  "Replace Datasheet PDF for Component" \
  "## User Story

As amaker who uploaded a PDF datasheet for a component,  
**I want** to upload an updated datasheet,  
**So that** the AI can extract more accurate dimensions from the newer documentation.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Replace datasheet PDF
  Given I am viewing a component with an attached PDF datasheet
  When I click \"Update\" next to the datasheet
  And I upload a new PDF file
  Then the new PDF replaces the old one
  And AI extraction is automatically triggered
  And I see \"Analyzing datasheet...\" status

Scenario: Cancel datasheet replacement
  Given I have started uploading a new datasheet
  When I click \"Cancel\" before upload completes
  Then the original datasheet remains unchanged
  And no extraction job is created
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Component File Management

## Labels

\`user-story\`, \`must-have\`, \`component-file-management\`
" \
  "${EPIC_NUMBERS[component_file_management]}"

# US-1003: Bulk File Update for Multiple Components
create_user_story \
  "US-1003" \
  "Bulk File Update for Multiple Components" \
  "## User Story

As auser with many components in a project,  
**I want** to update files for multiple components at once,  
**So that** I can efficiently refresh my component library after receiving updated specs.

## Acceptance Criteria

- [ ] Select multiple components in list view
- [ ] \"Update Files\" action appears in bulk actions menu
- [ ] Upload dialog allows mapping files to components by name
- [ ] Progress indicator shows update status for each component

## Details

- **Priority:** Could Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Component File Management

## Labels

\`user-story\`, \`could-have\`, \`component-file-management\`
" \
  "${EPIC_NUMBERS[component_file_management]}"

# US-101: User Registration
create_user_story \
  "US-101" \
  "User Registration" \
  "## User Story

As a **new visitor**, I want to **create an account with my email and password**, so that **I can save my designs and access them later**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Successful registration
  Given I am on the registration page
  When I enter a valid email \"user@example.com\"
  And I enter a password meeting complexity requirements
  And I enter a display name
  And I accept the Terms of Service
  And I click \"Create Account\"
  Then my account is created with \"pending\" status
  And I receive a verification email within 60 seconds
  And I am redirected to a \"check your email\" page

Scenario: Registration with existing email
  Given I am on the registration page
  And an account exists with email \"existing@example.com\"
  When I enter email \"existing@example.com\"
  And I complete the form and submit
  Then I see an error \"An account with this email already exists\"
  And no new account is created

Scenario: Registration with weak password
  Given I am on the registration page
  When I enter a password \"weak\"
  Then I see password requirements displayed
  And the submit button is disabled until requirements are met

Scenario: Email verification
  Given I have registered and received verification email
  When I click the verification link within 24 hours
  Then my account status changes to \"active\"
  And I am redirected to the onboarding flow
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** User Authentication & Account Management

## Labels

\`user-story\`, \`must-have\`, \`user-authentication-account-management\`
" \
  "${EPIC_NUMBERS[user_authentication_account_management]}"

# US-102: User Login
create_user_story \
  "US-102" \
  "User Login" \
  "## User Story

As a **registered user**, I want to **log in with my email and password**, so that **I can access my account and designs**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Successful login
  Given I have an active account with email \"user@example.com\"
  And I am on the login page
  When I enter my correct email and password
  And I click \"Log In\"
  Then I am authenticated
  And I am redirected to my dashboard
  And I see a welcome message with my display name

Scenario: Login with incorrect password
  Given I am on the login page
  When I enter a valid email but incorrect password
  Then I see a generic error \"Invalid email or password\"
  And I am not authenticated
  And failed attempt is logged

Scenario: Login with unverified account
  Given I have an account with \"pending\" status
  When I attempt to log in
  Then I see a message \"Please verify your email first\"
  And I am offered an option to resend verification email

Scenario: Login with suspended account
  Given my account has been suspended
  When I attempt to log in
  Then I see a message explaining the suspension
  And I am provided contact information for support

Scenario: Remember me functionality
  Given I am on the login page
  When I check \"Remember me\" and log in
  Then my session persists for 30 days instead of 7 days
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 3
- **Dependencies:** US-101
- **Category:** User Authentication & Account Management

## Labels

\`user-story\`, \`must-have\`, \`user-authentication-account-management\`
" \
  "${EPIC_NUMBERS[user_authentication_account_management]}"

# US-103: Password Reset
create_user_story \
  "US-103" \
  "Password Reset" \
  "## User Story

As a **user who forgot my password**, I want to **reset my password via email**, so that **I can regain access to my account**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Request password reset
  Given I am on the login page
  When I click \"Forgot password?\"
  And I enter my registered email
  And I click \"Send Reset Link\"
  Then I see \"If an account exists, you will receive an email\"
  And if the email exists, a reset email is sent within 60 seconds

Scenario: Reset password with valid token
  Given I have requested a password reset
  And I received the reset email
  When I click the reset link within 1 hour
  And I enter a new password meeting requirements
  And I confirm the new password
  And I click \"Reset Password\"
  Then my password is updated
  And I am logged in automatically
  And I receive a confirmation email

Scenario: Reset password with expired token
  Given I have a reset token that is more than 1 hour old
  When I click the reset link
  Then I see \"This reset link has expired\"
  And I am prompted to request a new reset

Scenario: Prevent email enumeration
  Given an email \"nonexistent@example.com\" has no account
  When I request a password reset for that email
  Then I see the same success message as for existing accounts
  And no email is sent
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 3
- **Dependencies:** US-101
- **Category:** User Authentication & Account Management

## Labels

\`user-story\`, \`must-have\`, \`user-authentication-account-management\`
" \
  "${EPIC_NUMBERS[user_authentication_account_management]}"

# US-104: User Profile Management
create_user_story \
  "US-104" \
  "User Profile Management" \
  "## User Story

As a **logged-in user**, I want to **update my profile information**, so that **my account reflects my current preferences**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Update display name
  Given I am logged in and on my profile page
  When I change my display name to \"New Name\"
  And I click \"Save\"
  Then my display name is updated
  And I see a success confirmation

Scenario: Update email address
  Given I am logged in and on my profile page
  When I change my email to \"newemail@example.com\"
  And I enter my current password for verification
  And I click \"Save\"
  Then a verification email is sent to the new address
  And my email is updated after verification

Scenario: Change password
  Given I am logged in and on my profile page
  When I enter my current password
  And I enter a new password meeting requirements
  And I confirm the new password
  And I click \"Update Password\"
  Then my password is updated
  And other active sessions are invalidated
  And I receive a confirmation email

Scenario: Update notification preferences
  Given I am logged in and on my profile page
  When I toggle \"Email me when jobs complete\" to off
  And I click \"Save\"
  Then my preference is saved
  And I will not receive job completion emails
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 3
- **Dependencies:** US-102
- **Category:** User Authentication & Account Management

## Labels

\`user-story\`, \`should-have\`, \`user-authentication-account-management\`
" \
  "${EPIC_NUMBERS[user_authentication_account_management]}"

# US-105: Account Deletion
create_user_story \
  "US-105" \
  "Account Deletion" \
  "## User Story

As a **user**, I want to **delete my account**, so that **my data is removed from the platform**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Request account deletion
  Given I am logged in and on my account settings
  When I click \"Delete Account\"
  Then I see a warning about data loss
  And I am asked to type \"DELETE\" to confirm
  And I must enter my password

Scenario: Confirm account deletion
  Given I have initiated account deletion
  When I type \"DELETE\" and enter my password
  And I click \"Permanently Delete Account\"
  Then my account is scheduled for deletion in 30 days
  And I am logged out
  And I receive a confirmation email with cancellation option

Scenario: Cancel account deletion
  Given my account is scheduled for deletion
  When I log in within 30 days
  Then I see a banner \"Your account is scheduled for deletion\"
  And I can click \"Cancel Deletion\" to restore my account
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 3
- **Dependencies:** US-102
- **Category:** User Authentication & Account Management

## Labels

\`user-story\`, \`should-have\`, \`user-authentication-account-management\`
" \
  "${EPIC_NUMBERS[user_authentication_account_management]}"

# US-11001: Detect Component Collisions
create_user_story \
  "US-11001" \
  "Detect Component Collisions" \
  "## User Story

As auser arranging components in an enclosure,  
**I want** to see warnings when components overlap,  
**So that** I can fix placement issues before generating.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Visual collision warning
  Given I have two components in the layout
  When I drag one component to overlap with another
  Then both components turn red
  And a warning icon appears in the toolbar
  And I see \"2 components overlapping\"

Scenario: Collision prevents generation
  Given there are overlapping components
  When I click \"Generate Enclosure\"
  Then I see \"Please resolve collisions first\" error
  And the list of colliding components is shown

Scenario: Collision list
  Given there are multiple collisions
  When I click the warning icon
  Then I see a list of all collision pairs
  And clicking a pair selects those components
\`\`\`

## Details

- **Priority:** Could Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Layout Editor Enhancements

## Labels

\`user-story\`, \`could-have\`, \`layout-editor-enhancements\`
" \
  "${EPIC_NUMBERS[layout_editor_enhancements]}"

# US-11002: Visualize Clearance Zones
create_user_story \
  "US-11002" \
  "Visualize Clearance Zones" \
  "## User Story

As auser placing components,  
**I want** to see clearance zones around each component,  
**So that** I ensure proper spacing for airflow and access.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Show clearance zones
  Given I am in the layout editor
  When I toggle \"Show Clearances\" on
  Then translucent zones appear around each component
  And zones are color-coded:
  - Green: Adequate clearance
  - Yellow: Tight clearance
  - Red: Overlapping with another zone

Scenario: Configure clearance per component
  Given I have a heat-generating component selected
  When I open component properties
  And I set \"Required clearance\" to 10mm
  Then the clearance zone expands to 10mm
\`\`\`

## Details

- **Priority:** Could Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Layout Editor Enhancements

## Labels

\`user-story\`, \`could-have\`, \`layout-editor-enhancements\`
" \
  "${EPIC_NUMBERS[layout_editor_enhancements]}"

# US-11003: Auto-Arrange Components
create_user_story \
  "US-11003" \
  "Auto-Arrange Components" \
  "## User Story

As auser who has added many components,  
**I want** the system to automatically arrange them,  
**So that** I get a good starting layout quickly.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Auto-arrange with packing algorithm
  Given I have 6 components in the layout in random positions
  When I click \"Auto-Arrange\" and select \"Pack\"
  Then components are repositioned to minimize footprint
  And no components overlap
  And clearance zones are respected

Scenario: Auto-arrange with thermal awareness
  Given I have 2 heat-generating components and 4 others
  When I click \"Auto-Arrange\" and select \"Thermal\"
  Then heat sources are placed with maximum separation
  And heat sources are near enclosure walls (for venting)

Scenario: Undo auto-arrange
  Given I just ran auto-arrange
  When I click \"Undo\"
  Then components return to their previous positions
\`\`\`

## Details

- **Priority:** Could Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Layout Editor Enhancements

## Labels

\`user-story\`, \`could-have\`, \`layout-editor-enhancements\`
" \
  "${EPIC_NUMBERS[layout_editor_enhancements]}"

# US-13001: Slash Command System
create_user_story \
  "US-13001" \
  "Slash Command System" \
  "## User Story

As apower user,  
**I want** to use slash commands like \`/save\` or \`/export\`,  
**So that** I have quick shortcuts to perform common actions without leaving the chat.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Type slash command
  Given I am in the chat input field
  When I type \"/\"
  Then I see a dropdown with available commands
  And commands are filtered as I continue typing

Scenario: Execute /save command
  Given I have generated a design
  When I type \"/save\" and press Enter
  Then the current design is saved
  And I see confirmation \"Design saved successfully\"

Scenario: Execute /export command with format
  Given I have a design open
  When I type \"/export stl\" and press Enter
  Then an STL file downloads automatically
  And I see \"Exported as STL\" in chat

Scenario: Unknown command shows help
  Given I type an invalid command like \"/invalid\"
  When I press Enter
  Then I see \"Unknown command. Type /help for available commands\"
\`\`\`

**Available Commands:**
| Command | Aliases | Description |
|---------|---------|-------------|
| \`/save\` | \`/s\` | Save current design |
| \`/export [format]\` | \`/e\` | Export design (stl, step, obj) |
| \`/maketemplate [name]\` | \`/mt\`, \`/template\` | Create template from design |
| \`/help\` | \`/h\`, \`/?\` | Show command list |
| \`/undo\` | \`/u\` | Undo last change |
| \`/redo\` | \`/r\` | Redo undone change |
| \`/clear\` | | Clear chat history (not designs) |
| \`/settings\` | | Open settings panel |

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** AI Slash Commands

## Labels

\`user-story\`, \`should-have\`, \`ai-slash-commands\`
" \
  "${EPIC_NUMBERS[ai_slash_commands]}"

# US-13002: Command Autocomplete
create_user_story \
  "US-13002" \
  "Command Autocomplete" \
  "## User Story

As auser learning the commands,  
**I want** autocomplete suggestions when I type \`/\`,  
**So that** I can discover and use commands quickly.

## Acceptance Criteria

- [ ] Dropdown appears when typing \`/\`
- [ ] Commands filtered by typed characters
- [ ] Tab or Enter selects highlighted command
- [ ] Arrow keys navigate options
- [ ] Escape dismisses dropdown
- [ ] Shows command description in dropdown

## Details

- **Priority:** Should Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** AI Slash Commands

## Labels

\`user-story\`, \`should-have\`, \`ai-slash-commands\`
" \
  "${EPIC_NUMBERS[ai_slash_commands]}"

# US-13003: Command Help
create_user_story \
  "US-13003" \
  "Command Help" \
  "## User Story

As auser,  
**I want** a \`/help\` command that shows all available commands,  
**So that** I can learn what shortcuts are available.

## Acceptance Criteria

- [ ] \`/help\` shows formatted command list
- [ ] Each command shows description and usage
- [ ] Links to documentation for advanced usage

## Details

- **Priority:** Must Have
- **Story Points:** 2
- **Dependencies:** None
- **Category:** AI Slash Commands

## Labels

\`user-story\`, \`must-have\`, \`ai-slash-commands\`
" \
  "${EPIC_NUMBERS[ai_slash_commands]}"

# US-14001: Gridfinity Pattern Understanding
create_user_story \
  "US-14001" \
  "Gridfinity Pattern Understanding" \
  "## User Story

As amaker who uses Gridfinity storage systems,  
**I want** the AI to understand Gridfinity specifications,  
**So that** I can create compatible bins and accessories.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Create Gridfinity bin
  Given I am in the design chat
  When I type \"Create a 2x3 Gridfinity bin that is 42mm tall\"
  Then the AI generates a bin with:
    | Dimension | Value |
    | Width | 84mm (2 × 42mm) |
    | Depth | 126mm (3 × 42mm) |
    | Height | 42mm |
  And it includes the standard base grid pattern
  And it fits on a Gridfinity baseplate

Scenario: Create Gridfinity baseplate
  Given I type \"Make a 4x4 Gridfinity baseplate\"
  Then the AI generates a baseplate 168mm × 168mm
  And it includes the magnetic attachment points
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** AI Intelligence Improvements

## Labels

\`user-story\`, \`should-have\`, \`ai-intelligence-improvements\`
" \
  "${EPIC_NUMBERS[ai_intelligence_improvements]}"

# US-14002: Dovetail Joint Generation
create_user_story \
  "US-14002" \
  "Dovetail Joint Generation" \
  "## User Story

As awoodworker or maker,  
**I want** the AI to generate dovetail joints,  
**So that** I can create interlocking parts for strong assemblies.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Create dovetail joint
  Given I type \"Create dovetail joints for a box with 15mm thick sides\"
  Then the AI generates both tail and pin boards
  And the joints interlock correctly
  And I can export both parts separately

Scenario: Customize dovetail parameters
  Given I type \"Make dovetails with 5 tails and 10 degree angle\"
  Then the AI creates exactly 5 tails
  And the pin angle is 10 degrees
\`\`\`

**Parameters:**
- Number of tails (default: auto based on width)
- Pin angle (8°-15°, default: 14°)
- Board thickness
- Tail length (default: 0.8 × thickness)

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** AI Intelligence Improvements

## Labels

\`user-story\`, \`should-have\`, \`ai-intelligence-improvements\`
" \
  "${EPIC_NUMBERS[ai_intelligence_improvements]}"

# US-14003: Clarifying Questions for Ambiguous Input
create_user_story \
  "US-14003" \
  "Clarifying Questions for Ambiguous Input" \
  "## User Story

As auser with a vague design idea,  
**I want** the AI to ask clarifying questions,  
**So that** I get a design that matches my actual needs.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Ambiguous dimensions
  Given I type \"Make me a box\"
  When the AI detects missing critical info
  Then it asks \"What size should the box be? (e.g., 100mm × 100mm × 50mm)\"
  And I can provide dimensions
  And the AI then generates the design

Scenario: Ambiguous purpose
  Given I type \"Create a mount\"
  When the AI detects ambiguity
  Then it asks \"What would you like to mount? Some options:
    - Wall mount for a device
    - Desktop stand
    - Bracket for shelving\"
  And I can select or describe further

Scenario: Provide context to skip questions
  Given I type \"Make a 100×80×40mm box with 2mm walls for a Raspberry Pi\"
  Then the AI has enough context
  And generates immediately without questions
\`\`\`

**Clarification triggers:**
- No dimensions specified
- Ambiguous part type (mount, bracket, holder)
- Unknown use case
- Conflicting requirements

## Details

- **Priority:** Must Have
- **Story Points:** 8
- **Dependencies:** None
- **Category:** AI Intelligence Improvements

## Labels

\`user-story\`, \`must-have\`, \`ai-intelligence-improvements\`
" \
  "${EPIC_NUMBERS[ai_intelligence_improvements]}"

# US-14004: Multi-step Design Workflow
create_user_story \
  "US-14004" \
  "Multi-step Design Workflow" \
  "## User Story

As auser with complex design requirements,  
**I want** to describe a multi-step design process,  
**So that** the AI builds my design incrementally.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Multi-step instructions
  Given I type \"First, create a box 100×80×40mm. Then add a lid with a hinge. Finally, add ventilation holes.\"
  When the AI processes the request
  Then it shows step-by-step progress:
    | Step | Description | Status |
    | 1 | Create base box | ✅ Complete |
    | 2 | Add hinged lid | ✅ Complete |
    | 3 | Add ventilation | ✅ Complete |
  And the final design includes all features

Scenario: Modify specific step
  Given I have completed a multi-step design
  When I say \"Change step 2 to use screws instead of hinges\"
  Then only that step is regenerated
  And subsequent steps are adjusted as needed
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 8
- **Dependencies:** None
- **Category:** AI Intelligence Improvements

## Labels

\`user-story\`, \`should-have\`, \`ai-intelligence-improvements\`
" \
  "${EPIC_NUMBERS[ai_intelligence_improvements]}"

# US-14005: Complex Constraint Understanding
create_user_story \
  "US-14005" \
  "Complex Constraint Understanding" \
  "## User Story

As aengineer with specific requirements,  
**I want** the AI to understand complex constraints,  
**So that** my designs meet all specifications.

## Acceptance Criteria

- [ ] Constraints extracted from natural language
- [ ] Conflicting constraints flagged before generation
- [ ] Constraint summary shown for review
- [ ] Violations reported with suggestions

## Details

- **Priority:** Should Have
- **Story Points:** 7
- **Dependencies:** None
- **Category:** AI Intelligence Improvements

## Labels

\`user-story\`, \`should-have\`, \`ai-intelligence-improvements\`
" \
  "${EPIC_NUMBERS[ai_intelligence_improvements]}"

# US-15001: Fast AI Response Time
create_user_story \
  "US-15001" \
  "Fast AI Response Time" \
  "## User Story

As auser iterating on designs,  
**I want** AI responses in under 3 seconds,  
**So that** my creative flow isn't interrupted.

## Acceptance Criteria

- [ ] Average response time < 3 seconds (simple designs)
- [ ] P95 response time < 8 seconds
- [ ] Progress indicator for longer generations
- [ ] Response streaming shows partial results

## Details

- **Priority:** Must Have
- **Story Points:** 8
- **Dependencies:** None
- **Category:** AI Performance & Manufacturing

## Labels

\`user-story\`, \`must-have\`, \`ai-performance-manufacturing\`
" \
  "${EPIC_NUMBERS[ai_performance_manufacturing]}"

# US-15002: Streaming AI Responses
create_user_story \
  "US-15002" \
  "Streaming AI Responses" \
  "## User Story

As auser waiting for a response,  
**I want** to see the AI's response as it's generated,  
**So that** I know the system is working and can read as it types.

## Acceptance Criteria

- [ ] Text streams in real-time
- [ ] CAD generation shows progress bar
- [ ] Thumbnail appears when ready
- [ ] Can cancel mid-generation

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** AI Performance & Manufacturing

## Labels

\`user-story\`, \`should-have\`, \`ai-performance-manufacturing\`
" \
  "${EPIC_NUMBERS[ai_performance_manufacturing]}"

# US-15003: 3D Print Optimization
create_user_story \
  "US-15003" \
  "3D Print Optimization" \
  "## User Story

As auser who will 3D print my designs,  
**I want** the AI to optimize designs for printing,  
**So that** I get successful prints with minimal supports.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Auto-optimize for printing
  Given I create a design with overhangs
  When I say \"Optimize for 3D printing\"
  Then the AI suggests:
    - Optimal print orientation
    - Modified overhangs (≤45°)
    - Added chamfers for bed adhesion
    - Split into printable parts if needed

Scenario: Support minimization
  Given I have a complex design
  When I enable \"minimize supports\"
  Then the AI redesigns to reduce support material
  And shows before/after support comparison
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** AI Performance & Manufacturing

## Labels

\`user-story\`, \`should-have\`, \`ai-performance-manufacturing\`
" \
  "${EPIC_NUMBERS[ai_performance_manufacturing]}"

# US-15004: Material Recommendations
create_user_story \
  "US-15004" \
  "Material Recommendations" \
  "## User Story

As auser choosing materials,  
**I want** the AI to recommend appropriate materials,  
**So that** my design performs well for its intended use.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Recommend material
  Given I created an outdoor electronics enclosure
  When I ask \"What material should I use?\"
  Then the AI recommends:
    | Material | Reason |
    | ASA | UV resistant, weatherproof |
    | PETG | Good strength, water resistant |
  And explains pros/cons of each
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** AI Performance & Manufacturing

## Labels

\`user-story\`, \`should-have\`, \`ai-performance-manufacturing\`
" \
  "${EPIC_NUMBERS[ai_performance_manufacturing]}"

# US-15005: Print Settings Suggestions
create_user_story \
  "US-15005" \
  "Print Settings Suggestions" \
  "## User Story

As auser preparing to print,  
**I want** suggested print settings for my design,  
**So that** I achieve optimal results.

## Acceptance Criteria



## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** AI Performance & Manufacturing

## Labels

\`user-story\`, \`should-have\`, \`ai-performance-manufacturing\`
" \
  "${EPIC_NUMBERS[ai_performance_manufacturing]}"

# US-15006: Manufacturer Constraint Awareness
create_user_story \
  "US-15006" \
  "Manufacturer Constraint Awareness" \
  "## User Story

As auser designing for specific manufacturing,  
**I want** the AI to consider manufacturing constraints,  
**So that** my design can actually be manufactured with my chosen method.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Design for 3D printing only
  Given I create a design with thin walls and internal cavities
  When I ask \"Can this be CNC milled?\"
  Then the AI responds \"This design cannot be CNC milled because:
    - Internal cavities are not accessible by cutting tools
    - 1mm walls are too thin for milling
    Suggestion: Use 3D printing (FDM or SLA)\"

Scenario: Specify manufacturing method upfront
  Given I say \"Design a bracket for CNC milling\"
  When the AI generates the design
  Then it avoids:
    - Internal corners < 3mm radius
    - Features requiring 5-axis machining
    - Thin walls < 2mm
\`\`\`

**Manufacturing methods:**
- 3D Printing (FDM, SLA, SLS)
- CNC Milling (3-axis, 5-axis)
- Laser Cutting (2D)
- Injection Molding
- Sheet Metal

## Details

- **Priority:** Must Have
- **Story Points:** 8
- **Dependencies:** None
- **Category:** AI Performance & Manufacturing

## Labels

\`user-story\`, \`must-have\`, \`ai-performance-manufacturing\`
" \
  "${EPIC_NUMBERS[ai_performance_manufacturing]}"

# US-15007: Printability Warnings
create_user_story \
  "US-15007" \
  "Printability Warnings" \
  "## User Story

As auser reviewing my design,  
**I want** warnings about potential print issues,  
**So that** I can fix problems before printing.

## Acceptance Criteria

- [ ] Warnings shown in design review panel
- [ ] Problem areas highlighted in 3D view
- [ ] Suggested fixes provided
- [ ] Can suppress warnings if intentional

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** AI Performance & Manufacturing

## Labels

\`user-story\`, \`should-have\`, \`ai-performance-manufacturing\`
" \
  "${EPIC_NUMBERS[ai_performance_manufacturing]}"

# US-16001: Industrial Dark Theme
create_user_story \
  "US-16001" \
  "Industrial Dark Theme" \
  "## User Story

As auser working on CAD designs,  
**I want** a dark, industrial-themed interface,  
**So that** the app looks professional and is easy on my eyes.

## Acceptance Criteria

- [ ] All components use theme colors
- [ ] Dark mode is the default
- [ ] High contrast for readability
- [ ] Industrial-modern feel

## Details

- **Priority:** Must Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Design System & Theming

## Labels

\`user-story\`, \`must-have\`, \`design-system-theming\`
" \
  "${EPIC_NUMBERS[design_system_theming]}"

# US-16002: Light Mode Option
create_user_story \
  "US-16002" \
  "Light Mode Option" \
  "## User Story

As auser who prefers light interfaces,  
**I want** a light mode alternative,  
**So that** I can work comfortably in bright environments.

## Acceptance Criteria

- [ ] Light mode available in settings
- [ ] Maintains brand consistency
- [ ] Accessible contrast ratios (WCAG AA)
- [ ] Smooth transition animation

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Design System & Theming

## Labels

\`user-story\`, \`should-have\`, \`design-system-theming\`
" \
  "${EPIC_NUMBERS[design_system_theming]}"

# US-16003: Theme Preference Persistence
create_user_story \
  "US-16003" \
  "Theme Preference Persistence" \
  "## User Story

As auser,  
**I want** my theme preference saved,  
**So that** the app remembers my choice.

## Acceptance Criteria

- [ ] Preference saved to localStorage
- [ ] Synced to user profile when logged in
- [ ] Respects system preference initially
- [ ] Toggle in settings and header

## Details

- **Priority:** Should Have
- **Story Points:** 2
- **Dependencies:** None
- **Category:** Design System & Theming

## Labels

\`user-story\`, \`should-have\`, \`design-system-theming\`
" \
  "${EPIC_NUMBERS[design_system_theming]}"

# US-16004: Remove Create Button from Nav
create_user_story \
  "US-16004" \
  "Remove Create Button from Nav" \
  "## User Story

As auser,  
**I want** a cleaner navigation bar,  
**So that** the interface is less cluttered.

## Acceptance Criteria

- [ ] \"Create\" button removed from navbar
- [ ] Create action accessible via main chat
- [ ] Dashboard has clear \"New Design\" action

## Details

- **Priority:** Must Have
- **Story Points:** 1
- **Dependencies:** None
- **Category:** Design System & Theming

## Labels

\`user-story\`, \`must-have\`, \`design-system-theming\`
" \
  "${EPIC_NUMBERS[design_system_theming]}"

# US-16005: Slide-out History Panel
create_user_story \
  "US-16005" \
  "Slide-out History Panel" \
  "## User Story

As auser with many past conversations,  
**I want** a slide-out history panel on the left,  
**So that** I can quickly access previous designs.

## Acceptance Criteria

- [ ] History button on left side of screen
- [ ] Click opens slide-out panel
- [ ] Shows past conversations with previews
- [ ] Click conversation to resume it
- [ ] Panel closes on outside click or Escape

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Design System & Theming

## Labels

\`user-story\`, \`should-have\`, \`design-system-theming\`
" \
  "${EPIC_NUMBERS[design_system_theming]}"

# US-17001: Persistent Chat History
create_user_story \
  "US-17001" \
  "Persistent Chat History" \
  "## User Story

As auser,  
**I want** my conversations saved to the cloud,  
**So that** I can access them from any device.

## Acceptance Criteria

- [ ] Conversations saved to database
- [ ] Messages linked to designs
- [ ] Accessible across devices
- [ ] Syncs in real-time

## Details

- **Priority:** Must Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Chat History & Privacy

## Labels

\`user-story\`, \`must-have\`, \`chat-history-privacy\`
" \
  "${EPIC_NUMBERS[chat_history_privacy]}"

# US-17002: Search Conversations
create_user_story \
  "US-17002" \
  "Search Conversations" \
  "## User Story

As auser with many conversations,  
**I want** to search through my history,  
**So that** I can find past designs quickly.

## Acceptance Criteria

- [ ] Search box in history panel
- [ ] Full-text search across messages
- [ ] Results grouped by conversation
- [ ] Matching text highlighted

## Details

- **Priority:** Should Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Chat History & Privacy

## Labels

\`user-story\`, \`should-have\`, \`chat-history-privacy\`
" \
  "${EPIC_NUMBERS[chat_history_privacy]}"

# US-17003: Export Chat History
create_user_story \
  "US-17003" \
  "Export Chat History" \
  "## User Story

As auser who wants to keep records,  
**I want** to export my conversations,  
**So that** I have a backup or can share them.

## Acceptance Criteria

- [ ] Export button on each conversation
- [ ] Choose format before export
- [ ] Includes design thumbnails in PDF
- [ ] JSON includes all metadata

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Chat History & Privacy

## Labels

\`user-story\`, \`should-have\`, \`chat-history-privacy\`
" \
  "${EPIC_NUMBERS[chat_history_privacy]}"

# US-17004: Delete Chat History
create_user_story \
  "US-17004" \
  "Delete Chat History" \
  "## User Story

As auser concerned about privacy,  
**I want** to delete my chat history,  
**So that** my data isn't stored longer than I want.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Delete single conversation
  Given I am viewing my conversation list
  When I click delete on a conversation
  Then I see a confirmation dialog
  And clicking \"Delete\" permanently removes it

Scenario: Delete all history
  Given I am in privacy settings
  When I click \"Delete All Chat History\"
  Then I must type \"DELETE\" to confirm
  And all conversations are permanently removed
  And I receive a confirmation email
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Chat History & Privacy

## Labels

\`user-story\`, \`must-have\`, \`chat-history-privacy\`
" \
  "${EPIC_NUMBERS[chat_history_privacy]}"

# US-17005: Privacy Dashboard
create_user_story \
  "US-17005" \
  "Privacy Dashboard" \
  "## User Story

As aprivacy-conscious user,  
**I want** a dashboard showing my data usage,  
**So that** I can manage my privacy settings.

## Acceptance Criteria



## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Chat History & Privacy

## Labels

\`user-story\`, \`should-have\`, \`chat-history-privacy\`
" \
  "${EPIC_NUMBERS[chat_history_privacy]}"

# US-17006: Data Retention Settings
create_user_story \
  "US-17006" \
  "Data Retention Settings" \
  "## User Story

As auser,  
**I want** to control how long my data is kept,  
**So that** old conversations auto-delete.

## Acceptance Criteria



## Details

- **Priority:** Could Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Chat History & Privacy

## Labels

\`user-story\`, \`could-have\`, \`chat-history-privacy\`
" \
  "${EPIC_NUMBERS[chat_history_privacy]}"

# US-18001: Rate AI Responses
create_user_story \
  "US-18001" \
  "Rate AI Responses" \
  "## User Story

As auser,  
**I want** to rate AI responses as helpful or not,  
**So that** I can provide feedback to improve the AI.

## Acceptance Criteria

- [ ] Thumbs up/down on each AI response
- [ ] Rating saved immediately
- [ ] Visual feedback on selection
- [ ] Can change rating later

## Details

- **Priority:** Must Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Response Rating & Feedback

## Labels

\`user-story\`, \`must-have\`, \`response-rating-feedback\`
" \
  "${EPIC_NUMBERS[response_rating_feedback]}"

# US-18002: Provide Detailed Feedback
create_user_story \
  "US-18002" \
  "Provide Detailed Feedback" \
  "## User Story

As auser who rated a response poorly,  
**I want** to explain why,  
**So that** specific issues can be addressed.

## Acceptance Criteria



## Details

- **Priority:** Should Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Response Rating & Feedback

## Labels

\`user-story\`, \`should-have\`, \`response-rating-feedback\`
" \
  "${EPIC_NUMBERS[response_rating_feedback]}"

# US-18003: Save Favorite Responses
create_user_story \
  "US-18003" \
  "Save Favorite Responses" \
  "## User Story

As auser who gets great responses,  
**I want** to save my favorites,  
**So that** I can reference them later.

## Acceptance Criteria

- [ ] Star/bookmark button on responses
- [ ] Favorites list accessible in sidebar
- [ ] Can view favorite with original context
- [ ] Copy prompt to reuse

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Response Rating & Feedback

## Labels

\`user-story\`, \`should-have\`, \`response-rating-feedback\`
" \
  "${EPIC_NUMBERS[response_rating_feedback]}"

# US-18004: Organize Favorites with Tags
create_user_story \
  "US-18004" \
  "Organize Favorites with Tags" \
  "## User Story

As auser with many favorites,  
**I want** to organize them with tags,  
**So that** I can find them easily.

## Acceptance Criteria

- [ ] Add tags to favorites
- [ ] Filter favorites by tag
- [ ] Suggested tags based on content
- [ ] Create custom tags

## Details

- **Priority:** Could Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Response Rating & Feedback

## Labels

\`user-story\`, \`could-have\`, \`response-rating-feedback\`
" \
  "${EPIC_NUMBERS[response_rating_feedback]}"

# US-19001: Name the AI Assistant
create_user_story \
  "US-19001" \
  "Name the AI Assistant" \
  "## User Story

As auser,  
**I want** the AI to have a name,  
**So that** interactions feel more personal.

## Acceptance Criteria

- [ ] Default name is \"CADdy\"
- [ ] Name shown in chat messages
- [ ] Name used in welcome message
- [ ] Can customize in settings

## Details

- **Priority:** Could Have
- **Story Points:** 2
- **Dependencies:** None
- **Category:** AI Personalization

## Labels

\`user-story\`, \`could-have\`, \`ai-personalization\`
" \
  "${EPIC_NUMBERS[ai_personalization]}"

# US-19002: Response Style Presets
create_user_story \
  "US-19002" \
  "Response Style Presets" \
  "## User Story

As auser with communication preferences,  
**I want** to choose the AI's response style,  
**So that** responses match my needs.

## Acceptance Criteria



## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** AI Personalization

## Labels

\`user-story\`, \`should-have\`, \`ai-personalization\`
" \
  "${EPIC_NUMBERS[ai_personalization]}"

# US-19003: Custom AI Personality
create_user_story \
  "US-19003" \
  "Custom AI Personality" \
  "## User Story

As apower user,  
**I want** to write custom instructions for the AI,  
**So that** I can fully customize its behavior.

## Acceptance Criteria

- [ ] Free-form text input (500 char limit)
- [ ] Preview with sample response
- [ ] Reset to default option
- [ ] Instructions apply to all conversations

## Details

- **Priority:** Could Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** AI Personalization

## Labels

\`user-story\`, \`could-have\`, \`ai-personalization\`
" \
  "${EPIC_NUMBERS[ai_personalization]}"

# US-19004: Voice Input
create_user_story \
  "US-19004" \
  "Voice Input" \
  "## User Story

As ahands-busy user,  
**I want** to speak my design requests,  
**So that** I don't need to type.

## Acceptance Criteria

- [ ] Microphone button in input field
- [ ] Real-time transcription display
- [ ] Visual feedback while listening
- [ ] Works in modern browsers (Web Speech API)

## Details

- **Priority:** Could Have
- **Story Points:** 8
- **Dependencies:** None
- **Category:** AI Personalization

## Labels

\`user-story\`, \`could-have\`, \`ai-personalization\`
" \
  "${EPIC_NUMBERS[ai_personalization]}"

# US-19005: Voice Output
create_user_story \
  "US-19005" \
  "Voice Output" \
  "## User Story

As auser who prefers listening,  
**I want** the AI to read responses aloud,  
**So that** I can multitask while designing.

## Acceptance Criteria

- [ ] Toggle voice output on/off
- [ ] Adjustable speech rate
- [ ] Stop/pause controls
- [ ] Works with Web Speech API

## Details

- **Priority:** Could Have
- **Story Points:** 8
- **Dependencies:** None
- **Category:** AI Personalization

## Labels

\`user-story\`, \`could-have\`, \`ai-personalization\`
" \
  "${EPIC_NUMBERS[ai_personalization]}"

# US-20001: Real-time Usage Dashboard
create_user_story \
  "US-20001" \
  "Real-time Usage Dashboard" \
  "## User Story



## Acceptance Criteria



## Details

- **Priority:** Must Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Admin Dashboard

## Labels

\`user-story\`, \`must-have\`, \`admin-dashboard\`
" \
  "${EPIC_NUMBERS[admin_dashboard]}"

# US-20002: User Analytics
create_user_story \
  "US-20002" \
  "User Analytics" \
  "## User Story



## Acceptance Criteria



## Details

- **Priority:** Must Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Admin Dashboard

## Labels

\`user-story\`, \`must-have\`, \`admin-dashboard\`
" \
  "${EPIC_NUMBERS[admin_dashboard]}"

# US-20003: Generation Success/Failure Rates
create_user_story \
  "US-20003" \
  "Generation Success/Failure Rates" \
  "## User Story



## Acceptance Criteria



## Details

- **Priority:** Must Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Admin Dashboard

## Labels

\`user-story\`, \`must-have\`, \`admin-dashboard\`
" \
  "${EPIC_NUMBERS[admin_dashboard]}"

# US-20004: User Management
create_user_story \
  "US-20004" \
  "User Management" \
  "## User Story



## Acceptance Criteria



## Details

- **Priority:** Must Have
- **Story Points:** 8
- **Dependencies:** None
- **Category:** Admin Dashboard

## Labels

\`user-story\`, \`must-have\`, \`admin-dashboard\`
" \
  "${EPIC_NUMBERS[admin_dashboard]}"

# US-20005: Role Management
create_user_story \
  "US-20005" \
  "Role Management" \
  "## User Story



## Acceptance Criteria



## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Admin Dashboard

## Labels

\`user-story\`, \`should-have\`, \`admin-dashboard\`
" \
  "${EPIC_NUMBERS[admin_dashboard]}"

# US-2001: Replace CAD File for Existing Component
create_user_story \
  "US-2001" \
  "Replace CAD File for Existing Component" \
  "## User Story

As amaker who has uploaded a reference component,  
**I want** to replace the CAD file (STEP/STL) with an updated version,  
**So that** I can iterate on my component specifications without creating a new component entry.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Replace CAD file via component detail page
  Given I am viewing a component I own
  And the component has an existing STEP file attached
  When I click \"Update Files\" button
  And I upload a new STEP file
  Then the new file replaces the old one
  And the old file is archived for version history
  And the component's updated_at timestamp is refreshed

Scenario: Replace CAD file triggers re-extraction
  Given I am uploading a replacement CAD file
  When I check \"Re-run dimension extraction\" option
  And I complete the upload
  Then a new extraction job is queued
  And I see \"Extraction in progress\" status

Scenario: View file version history
  Given I have replaced a component's CAD file multiple times
  When I open the file history panel
  Then I see a list of all previous file versions
  And each version shows filename, date, and file size
  And I can download any previous version

Scenario: Restore previous file version
  Given I am viewing file history for a component
  When I click \"Restore\" on a previous version
  Then that version becomes the current file
  And a new history entry is created
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Component File Management

## Labels

\`user-story\`, \`must-have\`, \`component-file-management\`
" \
  "${EPIC_NUMBERS[component_file_management]}"

# US-2001: Align Two CAD Files
create_user_story \
  "US-2001" \
  "Align Two CAD Files" \
  "## User Story

As amaker combining multiple parts,  
**I want** to align two CAD files relative to each other,  
**So that** I can create assemblies from separate components.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Align by center
  Given I have two STEP files uploaded
  When I open the alignment editor
  And I select \"Align by center\" mode
  And I select both files
  Then the second file moves so its center aligns with the first
  And I see the aligned preview in 3D

Scenario: Align by face
  Given I am in the alignment editor with two files
  When I select \"Align by face\" mode
  And I click a face on the first object
  And I click a face on the second object
  Then the second object moves so the selected faces are coplanar

Scenario: Apply offset after alignment
  Given two objects are aligned by center
  When I enter offset values (X: 0, Y: 0, Z: 10)
  Then the second object moves 10mm up from the aligned position
  And I can see the offset in the preview

Scenario: Save alignment as assembly
  Given I have aligned multiple files
  When I click \"Save as Assembly\"
  And I enter assembly name \"Pi + Display Assembly\"
  Then an assembly record is created
  And I can find it in my Assemblies list
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 8
- **Dependencies:** None
- **Category:** File Alignment & CAD Combination

## Labels

\`user-story\`, \`should-have\`, \`file-alignment-cad-combination\`
" \
  "${EPIC_NUMBERS[file_alignment_cad_combination]}"

# US-2002: Use Alignment Presets
create_user_story \
  "US-2002" \
  "Use Alignment Presets" \
  "## User Story

As auser who frequently performs common alignments,  
**I want** to use preset alignment configurations,  
**So that** I can quickly position components without manual adjustment.

## Acceptance Criteria

- [ ] Preset buttons visible in alignment toolbar
- [ ] Clicking preset immediately applies transformation
- [ ] User can fine-tune after applying preset
- [ ] Presets respect component bounding boxes

## Details

- **Priority:** Should Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** File Alignment & CAD Combination

## Labels

\`user-story\`, \`should-have\`, \`file-alignment-cad-combination\`
" \
  "${EPIC_NUMBERS[file_alignment_cad_combination]}"

# US-2003: Export Combined Assembly
create_user_story \
  "US-2003" \
  "Export Combined Assembly" \
  "## User Story

As auser who has aligned multiple components,  
**I want** to export the combined assembly as a single file,  
**So that** I can use it in my enclosure design or share with others.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Export assembly as STEP
  Given I have saved an assembly with 3 aligned components
  When I click \"Export\" and select \"STEP\" format
  Then I receive a single STEP file containing all components
  And each component maintains its relative position

Scenario: Export assembly as STL
  Given I have an assembly
  When I export as STL with \"Merge meshes\" option checked
  Then I receive a single STL with unified geometry

Scenario: Export assembly with separate parts
  Given I have an assembly
  When I export as STEP with \"Keep separate\" option
  Then I receive a STEP file with distinct bodies for each component
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** File Alignment & CAD Combination

## Labels

\`user-story\`, \`should-have\`, \`file-alignment-cad-combination\`
" \
  "${EPIC_NUMBERS[file_alignment_cad_combination]}"

# US-201: Generate Part from Natural Language
create_user_story \
  "US-201" \
  "Generate Part from Natural Language" \
  "## User Story

As a **user**, I want to **describe a part in plain English and have the AI generate a 3D model**, so that **I can create parts without CAD expertise**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Generate simple part from description
  Given I am logged in and on the design page
  When I enter \"Create a rectangular box 100mm x 50mm x 30mm with rounded corners\"
  And I click \"Generate\"
  Then a job is submitted to the queue
  And I see the job status updating
  And within 120 seconds, a 3D preview is displayed
  And the dimensions match my request within 5% tolerance

Scenario: Generate part with complex features
  Given I am logged in and on the design page
  When I enter \"Create a project box with screw posts in corners, ventilation slots on sides, and a snap-fit lid\"
  And I click \"Generate\"
  Then the AI generates a part with the specified features
  And I can inspect each feature in the 3D preview

Scenario: Handle ambiguous description
  Given I enter a vague description \"make me a bracket\"
  When I click \"Generate\"
  Then the AI either:
    - Asks clarifying questions about dimensions and mounting
    - Or generates a reasonable default with explanation
  And I can refine the result with follow-up modifications

Scenario: Reject prohibited content
  Given I enter a description for a weapon component
  When I click \"Generate\"
  Then the request is rejected
  And I see a message about prohibited content
  And the attempt is logged for review

Scenario: Handle generation failure
  Given I enter a valid but very complex description
  When generation fails
  Then I see a clear error message
  And I am offered suggestions to simplify the request
  And the job is not counted against my quota
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 13
- **Dependencies:** US-102
- **Category:** Part Design & Generation

## Labels

\`user-story\`, \`must-have\`, \`part-design-generation\`
" \
  "${EPIC_NUMBERS[part_design_generation]}"

# US-202: Browse Template Library
create_user_story \
  "US-202" \
  "Browse Template Library" \
  "## User Story

As a **user**, I want to **browse a library of pre-built templates**, so that **I can quickly start with common part types**.

## Acceptance Criteria

\`\`\`gherkin
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
  When I filter by \"Available to me\"
  Then I see only free tier templates
  And Pro templates are shown grayed out with upgrade prompt
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 5
- **Dependencies:** US-102
- **Category:** Part Design & Generation

## Labels

\`user-story\`, \`must-have\`, \`part-design-generation\`
" \
  "${EPIC_NUMBERS[part_design_generation]}"

# US-203: Customize Template Parameters
create_user_story \
  "US-203" \
  "Customize Template Parameters" \
  "## User Story

As a **user**, I want to **customize template parameters**, so that **the generated part fits my specific needs**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Adjust dimensions
  Given I have selected the \"Project Box\" template
  When I change the width from 100mm to 150mm using the slider
  Then the 3D preview updates in real-time
  And dependent parameters (like screw post positions) adjust automatically

Scenario: Add optional features
  Given I have selected a template with optional features
  When I enable \"Add ventilation slots\"
  And I set slot width to 2mm and spacing to 5mm
  Then the preview shows the ventilation slots
  And I can adjust slot parameters

Scenario: Parameter validation
  Given I am customizing a template
  When I enter a wall thickness of 0.2mm (below minimum)
  Then I see a validation error \"Minimum wall thickness is 0.8mm\"
  And the preview does not update until a valid value is entered

Scenario: Reset to defaults
  Given I have modified multiple parameters
  When I click \"Reset to Defaults\"
  Then all parameters return to their default values
  And the preview updates accordingly

Scenario: Save customized template (Pro)
  Given I am a Pro user
  And I have customized a template
  When I click \"Save as Template\"
  And I enter a name \"My Custom Box\"
  Then the template is saved to my personal template library
  And I can reuse it for future designs
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 8
- **Dependencies:** US-202
- **Category:** Part Design & Generation

## Labels

\`user-story\`, \`must-have\`, \`part-design-generation\`
" \
  "${EPIC_NUMBERS[part_design_generation]}"

# US-204: Receive AI Optimization Suggestions
create_user_story \
  "US-204" \
  "Receive AI Optimization Suggestions" \
  "## User Story

As a **user**, I want to **receive AI suggestions to improve my design**, so that **my parts are more printable and structurally sound**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Receive printability suggestions
  Given I have generated a part with steep overhangs
  When generation completes
  Then I see a suggestion panel with:
    | Type | Message | Location |
    | Warning | \"Overhang at 55° may require supports\" | Highlighted in preview |
  And I can click to zoom to the problem area

Scenario: Receive structural suggestions
  Given I have generated a part with thin walls
  When generation completes
  Then I see suggestions like:
    - \"Wall thickness of 0.9mm may be fragile for PLA\"
    - \"Consider increasing to 1.2mm for better strength\"
  And I can click \"Apply\" to automatically adjust

Scenario: Apply suggestion
  Given I see an optimization suggestion
  When I click \"Apply Suggestion\"
  Then the design is modified accordingly
  And a new version is created
  And I can compare before/after

Scenario: Dismiss suggestion
  Given I see a suggestion I don't want
  When I click \"Dismiss\"
  Then the suggestion is hidden
  And I can proceed with export
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 8
- **Dependencies:** US-201, US-203
- **Category:** Part Design & Generation

## Labels

\`user-story\`, \`should-have\`, \`part-design-generation\`
" \
  "${EPIC_NUMBERS[part_design_generation]}"

# US-205: Modify Design with Natural Language
create_user_story \
  "US-205" \
  "Modify Design with Natural Language" \
  "## User Story

As a **user**, I want to **modify my design using natural language commands**, so that **I can iterate without manual CAD work**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Resize design
  Given I have a generated design
  When I enter \"Make it 20% larger\"
  And I click \"Apply\"
  Then the design scales uniformly by 20%
  And I can see the new dimensions

Scenario: Add feature
  Given I have a generated box design
  When I enter \"Add a hole for M5 bolt on the top face, centered\"
  And I click \"Apply\"
  Then a 5.5mm hole is added to the top face
  And the hole is centered

Scenario: Remove feature
  Given I have a design with mounting tabs
  When I enter \"Remove the tabs on the sides\"
  And I click \"Apply\"
  Then the tabs are removed
  And I see before/after comparison

Scenario: Combine designs
  Given I have two designs in my project
  When I enter \"Attach design B to the right side of design A\"
  And I select the designs
  And I click \"Apply\"
  Then the designs are combined
  And I can adjust the attachment position

Scenario: Undo modification
  Given I have applied a modification
  When I click \"Undo\"
  Then the design reverts to the previous version
  And the modification command is still visible in history
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 8
- **Dependencies:** US-201
- **Category:** Part Design & Generation

## Labels

\`user-story\`, \`must-have\`, \`part-design-generation\`
" \
  "${EPIC_NUMBERS[part_design_generation]}"

# US-21001: Structured Logging
create_user_story \
  "US-21001" \
  "Structured Logging" \
  "## User Story



## Acceptance Criteria



## Details

- **Priority:** Must Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Logging & Audit

## Labels

\`user-story\`, \`must-have\`, \`logging-audit\`
" \
  "${EPIC_NUMBERS[logging_audit]}"

# US-21002: Log Search Interface
create_user_story \
  "US-21002" \
  "Log Search Interface" \
  "## User Story



## Acceptance Criteria



## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Logging & Audit

## Labels

\`user-story\`, \`should-have\`, \`logging-audit\`
" \
  "${EPIC_NUMBERS[logging_audit]}"

# US-21003: User Action Audit Trail
create_user_story \
  "US-21003" \
  "User Action Audit Trail" \
  "## User Story

As acompliance officer,  
**I want** a complete audit trail of user actions,  
**So that** we can meet regulatory requirements.

## Acceptance Criteria



## Details

- **Priority:** Must Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Logging & Audit

## Labels

\`user-story\`, \`must-have\`, \`logging-audit\`
" \
  "${EPIC_NUMBERS[logging_audit]}"

# US-21004: Admin Action Audit Trail
create_user_story \
  "US-21004" \
  "Admin Action Audit Trail" \
  "## User Story

As asuper admin,  
**I want** to see what admins have done,  
**So that** I can ensure accountability.

## Acceptance Criteria



## Details

- **Priority:** Must Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Logging & Audit

## Labels

\`user-story\`, \`must-have\`, \`logging-audit\`
" \
  "${EPIC_NUMBERS[logging_audit]}"

# US-22001: Share Designs to Social Media
create_user_story \
  "US-22001" \
  "Share Designs to Social Media" \
  "## User Story

As aproud maker,  
**I want** to share my designs on social media,  
**So that** I can show off my work.

## Acceptance Criteria

- [ ] Share button on design view
- [ ] Generates image preview
- [ ] Customizable caption
- [ ] Includes link back to app

## Details

- **Priority:** Could Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Sharing & Social

## Labels

\`user-story\`, \`could-have\`, \`sharing-social\`
" \
  "${EPIC_NUMBERS[sharing_social]}"

# US-22002: Email Sharing
create_user_story \
  "US-22002" \
  "Email Sharing" \
  "## User Story

As auser collaborating with others,  
**I want** to share designs via email,  
**So that** teammates can view my work.

## Acceptance Criteria

- [ ] Share via email button
- [ ] Email includes preview image
- [ ] Configurable permissions (view/edit)
- [ ] Expiring links option

## Details

- **Priority:** Could Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Sharing & Social

## Labels

\`user-story\`, \`could-have\`, \`sharing-social\`
" \
  "${EPIC_NUMBERS[sharing_social]}"

# US-22003: Collaborate on Conversations
create_user_story \
  "US-22003" \
  "Collaborate on Conversations" \
  "## User Story

As ateam member,  
**I want** to invite others to my design conversation,  
**So that** we can work together on a project.

## Acceptance Criteria

- [ ] Invite collaborators by email
- [ ] Collaborators can add messages
- [ ] Everyone sees updates in real-time
- [ ] Clear attribution of who said what

## Details

- **Priority:** Should Have
- **Story Points:** 8
- **Dependencies:** None
- **Category:** Sharing & Social

## Labels

\`user-story\`, \`should-have\`, \`sharing-social\`
" \
  "${EPIC_NUMBERS[sharing_social]}"

# US-22004: Team Workspaces
create_user_story \
  "US-22004" \
  "Team Workspaces" \
  "## User Story

As ateam lead,  
**I want** a shared workspace for my team,  
**So that** we can organize projects together.

## Acceptance Criteria



## Details

- **Priority:** Could Have
- **Story Points:** 8
- **Dependencies:** None
- **Category:** Sharing & Social

## Labels

\`user-story\`, \`could-have\`, \`sharing-social\`
" \
  "${EPIC_NUMBERS[sharing_social]}"

# US-23001: Language Selection
create_user_story \
  "US-23001" \
  "Language Selection" \
  "## User Story



## Acceptance Criteria

- [ ] Language selector in settings
- [ ] Auto-detect browser language
- [ ] Preference saved to profile

## Details

- **Priority:** Should Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Multi-Language Support

## Labels

\`user-story\`, \`should-have\`, \`multi-language-support\`
" \
  "${EPIC_NUMBERS[multi-language_support]}"

# US-23002: AI Responses in User Language
create_user_story \
  "US-23002" \
  "AI Responses in User Language" \
  "## User Story

As anon-English speaker,  
**I want** AI responses in my language,  
**So that** I can understand without translation.

## Acceptance Criteria

- [ ] AI responds in user's selected language
- [ ] User can type in any language
- [ ] Technical terms consistent across languages

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Multi-Language Support

## Labels

\`user-story\`, \`should-have\`, \`multi-language-support\`
" \
  "${EPIC_NUMBERS[multi-language_support]}"

# US-24001: Mobile Chat Interface
create_user_story \
  "US-24001" \
  "Mobile Chat Interface" \
  "## User Story

As amobile user,  
**I want** to use the AI chat on my phone,  
**So that** I can design on the go.

## Acceptance Criteria

- [ ] Responsive chat interface
- [ ] Touch-friendly controls
- [ ] Works on iOS and Android
- [ ] Offline message queue

## Details

- **Priority:** Must Have
- **Story Points:** 8
- **Dependencies:** None
- **Category:** Mobile Application

## Labels

\`user-story\`, \`must-have\`, \`mobile-application\`
" \
  "${EPIC_NUMBERS[mobile_application]}"

# US-24002: Mobile 3D Preview
create_user_story \
  "US-24002" \
  "Mobile 3D Preview" \
  "## User Story

As amobile user,  
**I want** to view 3D designs on my phone,  
**So that** I can review from anywhere.

## Acceptance Criteria

- [ ] Touch rotation/zoom
- [ ] Optimized for mobile GPU
- [ ] Low data usage mode

## Details

- **Priority:** Should Have
- **Story Points:** 8
- **Dependencies:** None
- **Category:** Mobile Application

## Labels

\`user-story\`, \`should-have\`, \`mobile-application\`
" \
  "${EPIC_NUMBERS[mobile_application]}"

# US-24003: Push Notifications
create_user_story \
  "US-24003" \
  "Push Notifications" \
  "## User Story

As amobile user,  
**I want** push notifications when jobs complete,  
**So that** I know when to check results.

## Acceptance Criteria



## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Mobile Application

## Labels

\`user-story\`, \`should-have\`, \`mobile-application\`
" \
  "${EPIC_NUMBERS[mobile_application]}"

# US-24004: Camera Reference Photos
create_user_story \
  "US-24004" \
  "Camera Reference Photos" \
  "## User Story

As amobile user,  
**I want** to take photos of parts to reference,  
**So that** I can describe what I need more easily.

## Acceptance Criteria

- [ ] Camera button in chat
- [ ] Take photo or select from gallery
- [ ] Photo attached to message
- [ ] AI can analyze for context

## Details

- **Priority:** Could Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Mobile Application

## Labels

\`user-story\`, \`could-have\`, \`mobile-application\`
" \
  "${EPIC_NUMBERS[mobile_application]}"

# US-25001: Install as App
create_user_story \
  "US-25001" \
  "Install as App" \
  "## User Story

As afrequent user,  
**I want** to install the app on my device,  
**So that** I can access it like a native app.

## Acceptance Criteria

- [ ] Install prompt on supported browsers
- [ ] Custom app icon and name
- [ ] Opens without browser chrome
- [ ] Works on desktop and mobile

## Details

- **Priority:** Should Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Progressive Web App

## Labels

\`user-story\`, \`should-have\`, \`progressive-web-app\`
" \
  "${EPIC_NUMBERS[progressive_web_app]}"

# US-25002: Offline Design Viewing
create_user_story \
  "US-25002" \
  "Offline Design Viewing" \
  "## User Story

As auser in areas with poor connectivity,  
**I want** to view my designs offline,  
**So that** I can reference them without internet.

## Acceptance Criteria

- [ ] Recent designs cached locally
- [ ] 3D viewer works offline
- [ ] Sync when back online
- [ ] Offline indicator in UI

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Progressive Web App

## Labels

\`user-story\`, \`should-have\`, \`progressive-web-app\`
" \
  "${EPIC_NUMBERS[progressive_web_app]}"

# US-25003: Web Push Notifications
create_user_story \
  "US-25003" \
  "Web Push Notifications" \
  "## User Story

As adesktop PWA user,  
**I want** push notifications in my browser,  
**So that** I know when jobs are done.

## Acceptance Criteria

- [ ] Permission request flow
- [ ] Notifications for job completion
- [ ] Click notification opens relevant design
- [ ] Respect quiet hours

## Details

- **Priority:** Could Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Progressive Web App

## Labels

\`user-story\`, \`could-have\`, \`progressive-web-app\`
" \
  "${EPIC_NUMBERS[progressive_web_app]}"

# US-3001: Extract Dimensions from PDF Mechanical Drawings
create_user_story \
  "US-3001" \
  "Extract Dimensions from PDF Mechanical Drawings" \
  "## User Story

As auser who has uploaded a component datasheet PDF,  
**I want** the AI to analyze mechanical drawings and extract dimensions,  
**So that** I don't have to manually enter component specifications.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Automatic extraction on PDF upload
  Given I am uploading a PDF datasheet for a new component
  When the upload completes
  Then AI extraction begins automatically
  And I see \"Analyzing datasheet...\" with progress indicator
  And extraction completes within 60 seconds

Scenario: Extract overall dimensions
  Given the PDF contains a mechanical drawing with overall dimensions
  When extraction completes
  Then the component's length, width, and height are populated
  And each dimension includes a confidence score

Scenario: Extract mounting holes
  Given the PDF shows a mounting hole pattern
  When extraction completes
  Then mounting holes are listed with X, Y positions
  And hole diameters and thread sizes (if shown) are captured

Scenario: Extract connector locations
  Given the PDF shows ports/connectors on the component
  When extraction completes
  Then connectors are listed with position and cutout dimensions
  And connector types (USB, HDMI, etc.) are identified

Scenario: Handle multi-page PDFs
  Given I upload a 20-page datasheet
  When extraction runs
  Then the system identifies pages with mechanical drawings
  And only relevant pages are sent to vision API
  And extraction focuses on dimensional data
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 8
- **Dependencies:** None
- **Category:** AI Dimension Extraction

## Labels

\`user-story\`, \`must-have\`, \`ai-dimension-extraction\`
" \
  "${EPIC_NUMBERS[ai_dimension_extraction]}"

# US-3002: Review and Correct AI Extractions
create_user_story \
  "US-3002" \
  "Review and Correct AI Extractions" \
  "## User Story

As auser reviewing AI-extracted dimensions,  
**I want** to see the extractions overlaid on the original document,  
**So that** I can verify accuracy and correct any errors.

## Acceptance Criteria

\`\`\`gherkin
Scenario: View extraction overlay
  Given AI extraction has completed for a component
  When I open the extraction review screen
  Then I see the PDF page with dimension annotations overlaid
  And extracted values are highlighted with colored boxes
  And confidence is indicated by color (green=high, yellow=medium, red=low)

Scenario: Edit extracted value
  Given I see an incorrect dimension value (shows 84mm, should be 85mm)
  When I click on the dimension annotation
  Then an edit field appears with current value
  When I change it to 85mm and save
  Then the component specification is updated
  And the extraction is marked as \"manually verified\"

Scenario: Add missing dimension
  Given a dimension was not automatically detected
  When I click \"Add Dimension\" 
  And I draw a box around the dimension in the PDF
  And I enter the value
  Then the dimension is added to the component
  And extraction improves for similar documents (feedback loop)

Scenario: Mark extraction as verified
  Given I have reviewed all extracted dimensions
  When I click \"Mark as Verified\"
  Then the component shows \"Specifications Verified\" badge
  And verified components appear higher in search results
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** AI Dimension Extraction

## Labels

\`user-story\`, \`should-have\`, \`ai-dimension-extraction\`
" \
  "${EPIC_NUMBERS[ai_dimension_extraction]}"

# US-3003: Re-analyze Specific Region
create_user_story \
  "US-3003" \
  "Re-analyze Specific Region" \
  "## User Story

As auser who sees a dimension was missed,  
**I want** to select a region of the PDF for focused analysis,  
**So that** the AI can find dimensions it initially missed.

## Acceptance Criteria

- [ ] Can draw rectangle on PDF to select region
- [ ] \"Analyze Selection\" button sends cropped image to GPT-4V
- [ ] Results merge with existing extractions
- [ ] Duplicate dimensions are deduplicated

## Details

- **Priority:** Could Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** AI Dimension Extraction

## Labels

\`user-story\`, \`could-have\`, \`ai-dimension-extraction\`
" \
  "${EPIC_NUMBERS[ai_dimension_extraction]}"

# US-301: Upload STEP/CAD File
create_user_story \
  "US-301" \
  "Upload STEP/CAD File" \
  "## User Story

As a **user**, I want to **upload my existing STEP or CAD files**, so that **I can view and modify them in the platform**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Upload valid STEP file
  Given I am on the upload page
  When I drag and drop a valid .step file under 100MB
  Then I see an upload progress indicator
  And the file is uploaded successfully
  And a 3D preview is generated within 30 seconds

Scenario: Upload via file browser
  Given I am on the upload page
  When I click \"Browse Files\"
  And I select a .stp file from my computer
  Then the file uploads and is processed

Scenario: Upload invalid file type
  Given I am on the upload page
  When I attempt to upload a .pdf file
  Then I see an error \"Unsupported file format. Supported: STEP, STL, OBJ, 3MF\"

Scenario: Upload oversized file
  Given I am on the upload page
  When I attempt to upload a 150MB STEP file
  Then I see an error \"File exceeds maximum size of 100MB\"

Scenario: Handle corrupted file
  Given I upload a STEP file with invalid geometry
  When processing fails
  Then I see an error \"Could not parse file. Please check the file is valid.\"
  And the file is not added to my projects
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 5
- **Dependencies:** US-102
- **Category:** File Management

## Labels

\`user-story\`, \`must-have\`, \`file-management\`
" \
  "${EPIC_NUMBERS[file_management]}"

# US-302: Preview 3D Models
create_user_story \
  "US-302" \
  "Preview 3D Models" \
  "## User Story

As a **user**, I want to **interactively preview my 3D models**, so that **I can inspect them from all angles**.

## Acceptance Criteria

\`\`\`gherkin
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
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 5
- **Dependencies:** US-301, US-201
- **Category:** File Management

## Labels

\`user-story\`, \`must-have\`, \`file-management\`
" \
  "${EPIC_NUMBERS[file_management]}"

# US-303: Export Designs
create_user_story \
  "US-303" \
  "Export Designs" \
  "## User Story

As a **user**, I want to **export my designs in multiple formats**, so that **I can use them in other software or 3D print them**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Export as STL
  Given I have a completed design
  When I click \"Export\"
  And I select \"STL\" format
  And I choose \"High\" quality
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
  When I export and select \"Inches\" as output unit
  Then the exported file dimensions are converted to inches

Scenario: Batch export
  Given I have multiple designs in a project
  When I select multiple designs
  And I click \"Export Selected\"
  Then I can export all as a ZIP file
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 5
- **Dependencies:** US-201, US-301
- **Category:** File Management

## Labels

\`user-story\`, \`must-have\`, \`file-management\`
" \
  "${EPIC_NUMBERS[file_management]}"

# US-304: Version History
create_user_story \
  "US-304" \
  "Version History" \
  "## User Story

As a **user**, I want to **access previous versions of my design**, so that **I can revert changes if needed**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: View version history
  Given I have a design with multiple versions
  When I click \"Version History\"
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
  When I click \"Restore This Version\"
  Then a new version is created matching the old one
  And this becomes the current version
  And the previous version is preserved

Scenario: Compare versions
  Given I have multiple versions
  When I select two versions to compare
  Then I see side-by-side 3D previews
  And differences are highlighted if possible
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** US-205
- **Category:** File Management

## Labels

\`user-story\`, \`should-have\`, \`file-management\`
" \
  "${EPIC_NUMBERS[file_management]}"

# US-305: Trash Bin
create_user_story \
  "US-305" \
  "Trash Bin" \
  "## User Story

As a **user**, I want to **recover accidentally deleted designs from trash**, so that **I don't lose work due to mistakes**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Delete design to trash
  Given I have a design I want to delete
  When I click \"Delete\"
  Then the design is moved to Trash
  And I see confirmation \"Moved to Trash\"
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
  When I click \"Restore\"
  Then the design is moved back to its original project
  And I can access it normally

Scenario: Permanent delete
  Given I have a design in Trash
  When I click \"Delete Permanently\"
  And I confirm the action
  Then the design is permanently removed
  And it cannot be recovered

Scenario: Automatic cleanup
  Given a design has been in Trash for 30 days (Pro) or 14 days (Free)
  When the retention period expires
  Then the design is permanently deleted
  And I receive an email notification 3 days before
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 3
- **Dependencies:** US-102
- **Category:** File Management

## Labels

\`user-story\`, \`should-have\`, \`file-management\`
" \
  "${EPIC_NUMBERS[file_management]}"

# US-4001: Select Enclosure Style Template
create_user_story \
  "US-4001" \
  "Select Enclosure Style Template" \
  "## User Story

As auser generating an enclosure,  
**I want** to choose from predefined style templates,  
**So that** the design matches my aesthetic and functional requirements.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Browse style templates
  Given I am on the enclosure generation page
  When I reach the \"Select Style\" step
  Then I see a grid of style cards with preview images
  And each card shows style name and brief description

Scenario: Select a style
  Given I am viewing style templates
  When I click on \"Rugged\" style card
  Then the card shows a selected indicator
  And the 3D preview updates to show rugged style
  And style-specific parameters appear in the form

Scenario: Preview style before selecting
  Given I hover over a style card
  When I remain hovered for 1 second
  Then a larger preview image appears
  And key characteristics are listed
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Enclosure Style Templates

## Labels

\`user-story\`, \`should-have\`, \`enclosure-style-templates\`
" \
  "${EPIC_NUMBERS[enclosure_style_templates]}"

# US-4002: Configure Rugged Style Parameters
create_user_story \
  "US-4002" \
  "Configure Rugged Style Parameters" \
  "## User Story

As auser who selected the Rugged enclosure style,  
**I want** to configure rugged-specific parameters,  
**So that** I can customize the level of protection.

## Acceptance Criteria

- [ ] Parameters form appears when rugged style selected
- [ ] 3D preview updates as parameters change
- [ ] Wall thickness affects interior dimensions (shown)
- [ ] IP rating presets adjust multiple parameters at once

## Details

- **Priority:** Should Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Enclosure Style Templates

## Labels

\`user-story\`, \`should-have\`, \`enclosure-style-templates\`
" \
  "${EPIC_NUMBERS[enclosure_style_templates]}"

# US-4003: Generate Stackable Enclosure
create_user_story \
  "US-4003" \
  "Generate Stackable Enclosure" \
  "## User Story

As auser building a modular system,  
**I want** to generate enclosures that stack and interlock,  
**So that** I can build expandable installations.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Generate stackable enclosure pair
  Given I selected \"Stackable\" style
  And I configured interlock depth as 3mm
  When I generate the enclosure
  Then the lid has protruding interlock ridges
  And the base has matching recesses
  And two enclosures preview stacking correctly

Scenario: Preview stacked assembly
  Given I have generated a stackable enclosure
  When I click \"Preview Stacked\"
  Then the 3D viewer shows 3 enclosures stacked
  And alignment pins are visible at interfaces
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Enclosure Style Templates

## Labels

\`user-story\`, \`should-have\`, \`enclosure-style-templates\`
" \
  "${EPIC_NUMBERS[enclosure_style_templates]}"

# US-4004: Save Custom Style Preset
create_user_story \
  "US-4004" \
  "Save Custom Style Preset" \
  "## User Story

As aPro user who has customized style parameters,  
**I want** to save my configuration as a custom preset,  
**So that** I can reuse it in future projects.

## Acceptance Criteria

- [ ] \"Save as Custom Style\" button appears for Pro users
- [ ] Can name the custom style
- [ ] Custom styles appear in style picker
- [ ] Can edit or delete custom styles

## Details

- **Priority:** Could Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Enclosure Style Templates

## Labels

\`user-story\`, \`could-have\`, \`enclosure-style-templates\`
" \
  "${EPIC_NUMBERS[enclosure_style_templates]}"

# US-401: Submit Generation Job
create_user_story \
  "US-401" \
  "Submit Generation Job" \
  "## User Story

As a **user**, I want to **submit design jobs to a queue**, so that **my requests are processed asynchronously**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Submit job successfully
  Given I have entered a design description
  When I click \"Generate\"
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
  Then I see \"Queue limit reached. Please wait for jobs to complete.\"
  And I am not charged for the rejected job
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 5
- **Dependencies:** US-201
- **Category:** Queue & Job Processing

## Labels

\`user-story\`, \`must-have\`, \`queue-job-processing\`
" \
  "${EPIC_NUMBERS[queue_job_processing]}"

# US-402: Track Job Status
create_user_story \
  "US-402" \
  "Track Job Status" \
  "## User Story

As a **user**, I want to **track the status of my generation jobs**, so that **I know when they will complete**.

## Acceptance Criteria

\`\`\`gherkin
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
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 5
- **Dependencies:** US-401
- **Category:** Queue & Job Processing

## Labels

\`user-story\`, \`must-have\`, \`queue-job-processing\`
" \
  "${EPIC_NUMBERS[queue_job_processing]}"

# US-403: Priority Queue
create_user_story \
  "US-403" \
  "Priority Queue" \
  "## User Story

As a **Pro subscriber**, I want my **jobs to be processed with priority**, so that **I get faster results than free users**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Pro user queue priority
  Given I am a Pro subscriber
  When I submit a job
  Then my job is placed in the priority queue
  And I see \"Priority\" badge on my job

Scenario: Priority queue processing
  Given the queue has:
    - 10 free tier jobs
    - 2 Pro tier jobs
  When a worker becomes available
  Then the Pro tier job is processed first

Scenario: Display tier benefits
  Given I am a free user viewing queue position
  Then I see a message \"Upgrade to Pro for priority processing\"
  And I see estimated time savings
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 5
- **Dependencies:** US-401
- **Category:** Queue & Job Processing

## Labels

\`user-story\`, \`must-have\`, \`queue-job-processing\`
" \
  "${EPIC_NUMBERS[queue_job_processing]}"

# US-404: Cancel Job
create_user_story \
  "US-404" \
  "Cancel Job" \
  "## User Story

As a **user**, I want to **cancel a queued job**, so that **I can free up my queue slot**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Cancel queued job
  Given I have a job in \"Queued\" status
  When I click \"Cancel\"
  Then the job is removed from the queue
  And my queue slot is freed
  And the job is not counted against my quota

Scenario: Cannot cancel processing job
  Given my job is in \"Processing\" status
  Then the cancel button is disabled
  And I see \"Cannot cancel jobs in progress\"
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 2
- **Dependencies:** US-401
- **Category:** Queue & Job Processing

## Labels

\`user-story\`, \`should-have\`, \`queue-job-processing\`
" \
  "${EPIC_NUMBERS[queue_job_processing]}"

# US-5001: Generate Snap-Fit Mounting Clips
create_user_story \
  "US-5001" \
  "Generate Snap-Fit Mounting Clips" \
  "## User Story

As auser designing for tool-less assembly,  
**I want** snap-fit clips to hold components,  
**So that** users can easily insert and remove components without screws.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Add snap-fit clip to component
  Given I am in the layout editor
  And I have a component placed in the enclosure
  When I select \"Mounting Type\" for the component
  And I choose \"Snap-fit clips\"
  Then snap-fit clips appear around the component edges
  And I can adjust clip positions

Scenario: Configure clip parameters
  Given I have snap-fit clips selected
  When I adjust \"Clip height\" to 5mm
  Then the 3D preview updates with taller clips
  And the component engagement depth increases
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Mounting Type Expansion

## Labels

\`user-story\`, \`should-have\`, \`mounting-type-expansion\`
" \
  "${EPIC_NUMBERS[mounting_type_expansion]}"

# US-5002: Generate DIN Rail Mount
create_user_story \
  "US-5002" \
  "Generate DIN Rail Mount" \
  "## User Story

As auser designing for industrial control panels,  
**I want** DIN rail mounting brackets,  
**So that** the enclosure mounts to standard 35mm DIN rails.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Add DIN rail mount to enclosure
  Given I am configuring enclosure generation
  When I select \"DIN rail mount\" as mounting option
  Then DIN rail clips are added to the back of the enclosure
  And the enclosure dimensions accommodate the clips

Scenario: Preview on DIN rail
  Given my enclosure has DIN rail mounting
  When I click \"Preview on Rail\"
  Then the 3D viewer shows enclosure mounted on a DIN rail
  And I can slide the enclosure along the rail in preview
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Mounting Type Expansion

## Labels

\`user-story\`, \`should-have\`, \`mounting-type-expansion\`
" \
  "${EPIC_NUMBERS[mounting_type_expansion]}"

# US-5003: Generate Wall Mount Brackets
create_user_story \
  "US-5003" \
  "Generate Wall Mount Brackets" \
  "## User Story

As auser installing enclosures on walls,  
**I want** wall mounting options,  
**So that** I can securely attach the enclosure.

## Acceptance Criteria

- [ ] Can select wall mount type per enclosure side
- [ ] Keyhole slots have proper geometry for #8 screws
- [ ] Screw spacing is configurable
- [ ] Export includes mounting template PDF

## Details

- **Priority:** Could Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Mounting Type Expansion

## Labels

\`user-story\`, \`could-have\`, \`mounting-type-expansion\`
" \
  "${EPIC_NUMBERS[mounting_type_expansion]}"

# US-5004: Generate Heat-Set Insert Bosses
create_user_story \
  "US-5004" \
  "Generate Heat-Set Insert Bosses" \
  "## User Story

As auser 3D printing enclosures,  
**I want** properly sized bosses for heat-set inserts,  
**So that** I can use metal threads for repeated assembly.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Select heat-set inserts for lid screws
  Given I am configuring enclosure lid attachment
  When I select \"Heat-set inserts\" as fastener type
  And I choose M3 size
  Then the base has bosses with 4.5mm holes
  And the boss outer diameter is 7.0mm
  And the depth is 5.5mm
\`\`\`

## Details

- **Priority:** Could Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Mounting Type Expansion

## Labels

\`user-story\`, \`could-have\`, \`mounting-type-expansion\`
" \
  "${EPIC_NUMBERS[mounting_type_expansion]}"

# US-501: View Dashboard
create_user_story \
  "US-501" \
  "View Dashboard" \
  "## User Story

As a **logged-in user**, I want to **see a personalized dashboard**, so that **I can quickly access my work and status**.

## Acceptance Criteria

\`\`\`gherkin
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
  When I click \"New Design\"
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
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 5
- **Dependencies:** US-102
- **Category:** Dashboard & Projects

## Labels

\`user-story\`, \`must-have\`, \`dashboard-projects\`
" \
  "${EPIC_NUMBERS[dashboard_projects]}"

# US-502: Organize Projects
create_user_story \
  "US-502" \
  "Organize Projects" \
  "## User Story

As a **user**, I want to **organize my designs into projects/folders**, so that **I can manage my work efficiently**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Create project
  Given I am on the projects page
  When I click \"New Project\"
  And I enter name \"Electronics Enclosures\"
  Then the project is created
  And I can add designs to it

Scenario: Move design to project
  Given I have a design in \"My Designs\"
  When I drag the design to a project folder
  Or right-click and select \"Move to\" > \"Electronics Enclosures\"
  Then the design is moved to that project

Scenario: Rename project
  Given I have a project
  When I right-click and select \"Rename\"
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
    - Move to \"My Designs\"
    - Delete all designs
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** US-501
- **Category:** Dashboard & Projects

## Labels

\`user-story\`, \`should-have\`, \`dashboard-projects\`
" \
  "${EPIC_NUMBERS[dashboard_projects]}"

# US-503: Search Designs
create_user_story \
  "US-503" \
  "Search Designs" \
  "## User Story

As a **user with many designs**, I want to **search for specific designs**, so that **I can find them quickly**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Search by name
  Given I have many designs
  When I type \"bracket\" in the search box
  Then I see all designs with \"bracket\" in the name

Scenario: Search by description
  Given I have designs with descriptions
  When I search for \"M5 bolt\"
  Then I see designs where description contains \"M5 bolt\"

Scenario: Filter results
  Given I have search results
  When I filter by:
    - Date range
    - Project
    - Source (generated/uploaded)
  Then results are filtered accordingly

Scenario: No results
  Given I search for \"xyz123nonexistent\"
  Then I see \"No designs found\"
  And suggestions to create a new design
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 3
- **Dependencies:** US-501
- **Category:** Dashboard & Projects

## Labels

\`user-story\`, \`should-have\`, \`dashboard-projects\`
" \
  "${EPIC_NUMBERS[dashboard_projects]}"

# US-6001: View Pricing and Subscription Tiers
create_user_story \
  "US-6001" \
  "View Pricing and Subscription Tiers" \
  "## User Story

As avisitor evaluating the platform,  
**I want** to see clear pricing information,  
**So that** I can choose the right plan for my needs.

## Acceptance Criteria

\`\`\`gherkin
Scenario: View pricing page
  Given I am a visitor on the website
  When I click \"Pricing\" in the navigation
  Then I see a comparison table of all tiers
  And features are clearly listed with checkmarks/X
  And monthly and yearly pricing is shown

Scenario: Toggle annual billing
  Given I am on the pricing page
  When I toggle \"Annual billing\"
  Then prices update to show yearly rates
  And I see \"2 months free\" badge on Pro/Enterprise
  And the monthly equivalent is shown

Scenario: See current plan indicator
  Given I am logged in as a Pro subscriber
  When I visit the pricing page
  Then my current plan shows \"Current Plan\" badge
  And upgrade/downgrade options are shown for other tiers
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Payment & Subscription

## Labels

\`user-story\`, \`must-have\`, \`payment-subscription\`
" \
  "${EPIC_NUMBERS[payment_subscription]}"

# US-6002: Subscribe to Pro Plan
create_user_story \
  "US-6002" \
  "Subscribe to Pro Plan" \
  "## User Story

As afree user who wants more features,  
**I want** to upgrade to Pro,  
**So that** I can access priority queue and more exports.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Start Pro subscription
  Given I am logged in as a free user
  And I am on the pricing page
  When I click \"Upgrade to Pro\"
  Then I am redirected to Stripe Checkout
  And the checkout shows Pro plan details
  And I can enter payment information

Scenario: Complete successful payment
  Given I am on Stripe Checkout for Pro plan
  When I enter valid payment details and submit
  Then I am redirected back to the app
  And I see \"Welcome to Pro!\" confirmation
  And my account immediately shows Pro features
  And I receive a confirmation email

Scenario: Handle payment failure
  Given I am on Stripe Checkout
  When I enter a declined card
  Then I see an error message
  And I can retry with different payment method
  And my account remains on Free tier
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 8
- **Dependencies:** None
- **Category:** Payment & Subscription

## Labels

\`user-story\`, \`must-have\`, \`payment-subscription\`
" \
  "${EPIC_NUMBERS[payment_subscription]}"

# US-6003: Manage Billing and Subscription
create_user_story \
  "US-6003" \
  "Manage Billing and Subscription" \
  "## User Story

As apaying subscriber,  
**I want** to manage my subscription,  
**So that** I can update payment methods or cancel.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Access billing portal
  Given I am logged in as a Pro subscriber
  When I go to Settings > Billing
  And I click \"Manage Subscription\"
  Then I am redirected to Stripe Customer Portal
  And I can view invoices, update payment, or cancel

Scenario: Cancel subscription
  Given I am in the Stripe Customer Portal
  When I click \"Cancel subscription\"
  And I confirm cancellation
  Then my subscription is set to cancel at period end
  And I return to app seeing \"Canceling at [date]\" status
  And I retain Pro access until the period ends

Scenario: View usage statistics
  Given I am on Settings > Billing
  Then I see my current usage:
  - Generations: 45 of 100 used
  - Storage: 2.3 GB of 5 GB used
  - Components: 23 of 50 used
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Payment & Subscription

## Labels

\`user-story\`, \`should-have\`, \`payment-subscription\`
" \
  "${EPIC_NUMBERS[payment_subscription]}"

# US-6004: Enforce Tier Limits
create_user_story \
  "US-6004" \
  "Enforce Tier Limits" \
  "## User Story

As aplatform operator,  
**I want** feature limits enforced by subscription tier,  
**So that** free users are encouraged to upgrade.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Block generation when limit reached
  Given I am a free user who has used 10 generations this month
  When I try to generate a new part
  Then I see \"Monthly limit reached\" message
  And I see \"Upgrade to Pro for 100 generations\" CTA
  And the generation is blocked

Scenario: Block STEP export for free users
  Given I am a free user viewing a generated part
  When I try to export as STEP
  Then I see \"STEP export requires Pro\" message
  And only STL export is available

Scenario: Warn when approaching limit
  Given I am a free user with 8 of 10 generations used
  When I view the dashboard
  Then I see \"2 generations remaining this month\" warning
  And a subtle upgrade prompt is shown
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Payment & Subscription

## Labels

\`user-story\`, \`must-have\`, \`payment-subscription\`
" \
  "${EPIC_NUMBERS[payment_subscription]}"

# US-601: View Subscription Tiers
create_user_story \
  "US-601" \
  "View Subscription Tiers" \
  "## User Story

As a **visitor or user**, I want to **see the available subscription tiers and their features**, so that **I can choose the right plan**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: View pricing page
  Given I am on the pricing page
  Then I see comparison of tiers:
    | Feature | Free | Pro (\$19/mo) | Enterprise |
    | Generations/month | 10 | Unlimited | Unlimited |
    | Queue priority | Standard | Priority | Highest |
    | Templates | Basic | All | All + Custom |
    | Storage | 500MB | 10GB | Unlimited |
    | Support | Community | Email | Dedicated |

Scenario: Current plan indicator
  Given I am a Pro subscriber
  When I view pricing
  Then the Pro tier is highlighted as \"Current Plan\"
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 2
- **Dependencies:** None
- **Category:** Subscription & Billing

## Labels

\`user-story\`, \`must-have\`, \`subscription-billing\`
" \
  "${EPIC_NUMBERS[subscription_billing]}"

# US-602: Upgrade Subscription
create_user_story \
  "US-602" \
  "Upgrade Subscription" \
  "## User Story

As a **free user**, I want to **upgrade to a paid subscription**, so that **I can access more features**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Upgrade to Pro
  Given I am a free user
  When I click \"Upgrade to Pro\"
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
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 5
- **Dependencies:** US-601
- **Category:** Subscription & Billing

## Labels

\`user-story\`, \`must-have\`, \`subscription-billing\`
" \
  "${EPIC_NUMBERS[subscription_billing]}"

# US-603: Manage Subscription
create_user_story \
  "US-603" \
  "Manage Subscription" \
  "## User Story

As a **paying subscriber**, I want to **manage my subscription**, so that **I can update payment method or cancel**.

## Acceptance Criteria

\`\`\`gherkin
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
  When I click \"Cancel Subscription\"
  Then I see what I'll lose (features, queue priority)
  And I can confirm cancellation
  And subscription remains active until end of billing period

Scenario: Reactivate subscription
  Given I have a cancelled subscription still in active period
  When I click \"Reactivate\"
  Then my subscription continues without interruption
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 3
- **Dependencies:** US-602
- **Category:** Subscription & Billing

## Labels

\`user-story\`, \`must-have\`, \`subscription-billing\`
" \
  "${EPIC_NUMBERS[subscription_billing]}"

# US-7001: Sign In with Google
create_user_story \
  "US-7001" \
  "Sign In with Google" \
  "## User Story

As auser who prefers not to create a new password,  
**I want** to sign in with my Google account,  
**So that** I can access the platform quickly and securely.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Sign in with Google (new user)
  Given I am on the login page
  When I click \"Continue with Google\"
  Then I am redirected to Google sign-in
  When I authorize the application
  Then I am redirected back to the app
  And a new account is created with my Google email
  And I am logged in and see the dashboard

Scenario: Sign in with Google (existing user)
  Given I previously registered with email@example.com
  And I sign in with Google using the same email
  Then my existing account is linked to Google
  And I can sign in with either method

Scenario: Import profile from Google
  Given I complete Google sign-in for the first time
  Then my display name is set from Google profile
  And my avatar is imported from Google
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** OAuth Authentication

## Labels

\`user-story\`, \`should-have\`, \`oauth-authentication\`
" \
  "${EPIC_NUMBERS[oauth_authentication]}"

# US-7002: Sign In with GitHub
create_user_story \
  "US-7002" \
  "Sign In with GitHub" \
  "## User Story

As adeveloper who uses GitHub,  
**I want** to sign in with my GitHub account,  
**So that** I can use my existing identity.

## Acceptance Criteria

- [ ] \"Continue with GitHub\" button on login/register pages
- [ ] OAuth flow completes successfully
- [ ] New user created with GitHub email
- [ ] Profile picture imported from GitHub
- [ ] Username suggested from GitHub username

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** OAuth Authentication

## Labels

\`user-story\`, \`should-have\`, \`oauth-authentication\`
" \
  "${EPIC_NUMBERS[oauth_authentication]}"

# US-7003: Link Additional OAuth Providers
create_user_story \
  "US-7003" \
  "Link Additional OAuth Providers" \
  "## User Story

As auser with an existing account,  
**I want** to link Google/GitHub to my account,  
**So that** I have multiple sign-in options.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Link Google to existing account
  Given I am logged in with email/password
  When I go to Settings > Account > Connected Accounts
  And I click \"Connect Google\"
  And I complete Google authorization
  Then Google shows as connected
  And I can now sign in with either method

Scenario: Unlink OAuth provider
  Given I have both Google and email/password configured
  When I click \"Disconnect\" next to Google
  Then Google is removed from my account
  And I can only sign in with email/password
\`\`\`

## Details

- **Priority:** Could Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** OAuth Authentication

## Labels

\`user-story\`, \`could-have\`, \`oauth-authentication\`
" \
  "${EPIC_NUMBERS[oauth_authentication]}"

# US-701: Share Design
create_user_story \
  "US-701" \
  "Share Design" \
  "## User Story

As a **user**, I want to **share my design with others**, so that **they can view or collaborate on it**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Generate share link
  Given I have a design
  When I click \"Share\"
  And I select \"Anyone with link can view\"
  Then a shareable URL is generated
  And I can copy it to clipboard

Scenario: Share with specific user
  Given I have a design
  When I click \"Share\"
  And I enter an email address
  And I select permission level (View/Edit)
  Then that user receives an email invitation
  And they can access the design with appropriate permissions

Scenario: View shared designs
  Given someone has shared a design with me
  When I go to \"Shared with Me\"
  Then I see the design with the sharer's name
  And I can access it according to my permissions

Scenario: Revoke access
  Given I have shared a design
  When I go to sharing settings
  And I remove a user or disable link sharing
  Then that access is revoked immediately
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** US-201
- **Category:** Collaboration & Sharing

## Labels

\`user-story\`, \`should-have\`, \`collaboration-sharing\`
" \
  "${EPIC_NUMBERS[collaboration_sharing]}"

# US-702: Comment on Designs
create_user_story \
  "US-702" \
  "Comment on Designs" \
  "## User Story

As a **collaborator**, I want to **leave comments on a design**, so that **we can discuss changes**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Add comment
  Given I have access to a shared design
  When I click on the design preview
  And I type a comment
  And I click \"Post\"
  Then the comment is attached to that location
  And other collaborators can see it

Scenario: Reply to comment
  Given there is a comment on a design
  When I click \"Reply\"
  And I type my response
  Then the reply is threaded under the original comment

Scenario: Resolve comment
  Given there is a comment thread
  When I click \"Resolve\"
  Then the comment is marked as resolved
  And it can be hidden from view
\`\`\`

## Details

- **Priority:** Could Have
- **Story Points:** 5
- **Dependencies:** US-701
- **Category:** Collaboration & Sharing

## Labels

\`user-story\`, \`could-have\`, \`collaboration-sharing\`
" \
  "${EPIC_NUMBERS[collaboration_sharing]}"

# US-8001: See Real-time Job Progress
create_user_story \
  "US-8001" \
  "See Real-time Job Progress" \
  "## User Story

As auser who submitted a generation job,  
**I want** to see real-time progress updates,  
**So that** I know how long I need to wait.

## Acceptance Criteria

\`\`\`gherkin
Scenario: View live job progress
  Given I have submitted a part generation job
  When I am on the job status page
  Then I see a progress bar updating in real-time
  And I see status text: \"Generating geometry...\"
  And the progress updates without page refresh

Scenario: Job completes while watching
  Given I am viewing a job in progress
  When the job completes
  Then I immediately see \"Complete\" status
  And the preview image appears
  And \"View Result\" button becomes active
  And I hear a notification sound (if enabled)

Scenario: Handle job failure
  Given I am viewing a job in progress
  When the job fails
  Then I see \"Failed\" status with error message
  And \"Retry\" button appears
  And no page refresh was needed
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Real-time Updates

## Labels

\`user-story\`, \`should-have\`, \`real-time-updates\`
" \
  "${EPIC_NUMBERS[real-time_updates]}"

# US-8002: Receive Real-time Notifications
create_user_story \
  "US-8002" \
  "Receive Real-time Notifications" \
  "## User Story

As auser with background jobs running,  
**I want** to receive notifications when jobs complete,  
**So that** I can continue working and know when results are ready.

## Acceptance Criteria

- [ ] Notification bell icon in header with unread count
- [ ] Real-time notifications appear without refresh
- [ ] Click notification navigates to relevant content
- [ ] Can mark notifications as read
- [ ] Notification preferences in settings

## Details

- **Priority:** Could Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Real-time Updates

## Labels

\`user-story\`, \`could-have\`, \`real-time-updates\`
" \
  "${EPIC_NUMBERS[real-time_updates]}"

# US-801: Admin Dashboard
create_user_story \
  "US-801" \
  "Admin Dashboard" \
  "## User Story

As an **admin**, I want to **view platform statistics and health**, so that **I can monitor the system**.

## Acceptance Criteria

\`\`\`gherkin
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
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** US-102
- **Category:** Administration

## Labels

\`user-story\`, \`should-have\`, \`administration\`
" \
  "${EPIC_NUMBERS[administration]}"

# US-802: Moderate Flagged Content
create_user_story \
  "US-802" \
  "Moderate Flagged Content" \
  "## User Story

As an **admin**, I want to **review flagged content**, so that **I can enforce platform policies**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: View moderation queue
  Given there are flagged items
  When I access the moderation queue
  Then I see items sorted by severity
  With flag reason, user info, content preview

Scenario: Approve content
  Given I am reviewing a flagged item
  When I determine it's acceptable
  And I click \"Approve\"
  Then the item is released
  And the user is notified if applicable
  And ML model is updated

Scenario: Reject content
  Given I am reviewing a flagged item
  When I determine it violates policies
  And I click \"Reject\"
  And I select a reason
  Then the content is deleted
  And the user receives a warning

Scenario: Suspend user
  Given a user has multiple violations
  When I click \"Suspend User\"
  And I enter the suspension reason and duration
  Then the user's account is suspended
  And they receive notification
  And they cannot log in
\`\`\`

## Details

- **Priority:** Must Have
- **Story Points:** 5
- **Dependencies:** US-601
- **Category:** Administration

## Labels

\`user-story\`, \`must-have\`, \`administration\`
" \
  "${EPIC_NUMBERS[administration]}"

# US-803: Manage Users
create_user_story \
  "US-803" \
  "Manage Users" \
  "## User Story

As an **admin**, I want to **manage user accounts**, so that **I can provide support and enforce policies**.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Search users
  Given I am in user management
  When I search for \"john@example.com\"
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
  When I click \"Impersonate\" with approval
  Then I see the platform as that user
  And all actions are logged
  And I can exit impersonation anytime

Scenario: Adjust subscription
  Given I need to apply a credit or adjustment
  When I modify the user's subscription
  Then the change is applied
  And it's logged with reason
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** US-801
- **Category:** Administration

## Labels

\`user-story\`, \`should-have\`, \`administration\`
" \
  "${EPIC_NUMBERS[administration]}"

# US-9001: Share Design with Collaborator
create_user_story \
  "US-9001" \
  "Share Design with Collaborator" \
  "## User Story

As auser who wants feedback on my design,  
**I want** to share it with a teammate,  
**So that** they can view and comment on it.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Share design via email
  Given I am viewing one of my designs
  When I click \"Share\" button
  And I enter colleague@example.com
  And I select \"Can comment\" permission
  And I click \"Send Invite\"
  Then the colleague receives an email with share link
  And the design appears in their \"Shared with Me\" section

Scenario: Share with multiple people
  Given I am in the share dialog
  When I enter multiple email addresses
  Then each person receives an invite
  And I can set different permissions for each

Scenario: View who has access
  Given I have shared a design with 3 people
  When I open the share dialog
  Then I see a list of all people with access
  And I can change their permission level
  And I can remove their access
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Collaboration Features

## Labels

\`user-story\`, \`should-have\`, \`collaboration-features\`
" \
  "${EPIC_NUMBERS[collaboration_features]}"

# US-9002: Comment on Shared Design
create_user_story \
  "US-9002" \
  "Comment on Shared Design" \
  "## User Story

As acollaborator viewing a shared design,  
**I want** to leave comments,  
**So that** I can provide feedback to the designer.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Add comment to design
  Given I have \"comment\" permission on a shared design
  When I click \"Add Comment\"
  And I type \"The mounting holes look too small\"
  And I click \"Post\"
  Then my comment appears in the comment thread
  And the design owner is notified

Scenario: Comment on specific 3D location
  Given I am viewing the 3D preview
  When I click on a point on the model
  And I add a comment
  Then the comment is anchored to that 3D location
  And clicking the comment highlights the location

Scenario: Reply to comment
  Given there is a comment on the design
  When I click \"Reply\"
  And I type my response
  Then my reply is threaded under the original

Scenario: Resolve comment thread
  Given I am the design owner
  And there is a comment thread
  When I click \"Resolve\"
  Then the thread is collapsed and marked resolved
  And resolved comments are hidden by default
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 5
- **Dependencies:** None
- **Category:** Collaboration Features

## Labels

\`user-story\`, \`should-have\`, \`collaboration-features\`
" \
  "${EPIC_NUMBERS[collaboration_features]}"

# US-9003: Create Shareable Link
create_user_story \
  "US-9003" \
  "Create Shareable Link" \
  "## User Story

As auser who wants to share broadly,  
**I want** to create a shareable link,  
**So that** anyone with the link can view the design.

## Acceptance Criteria

\`\`\`gherkin
Scenario: Create view-only share link
  Given I am viewing my design
  When I click \"Share\" and then \"Create Link\"
  And I select \"Anyone with link can view\"
  Then a shareable URL is generated
  And I can copy it to clipboard
  And the link works without login

Scenario: Set link expiration
  Given I am creating a share link
  When I set expiration to \"7 days\"
  Then the link expires after 7 days
  And visitors see \"Link expired\" after that

Scenario: Disable share link
  Given I have created a share link
  When I click \"Disable Link\"
  Then the link stops working immediately
  And visitors see \"Link no longer valid\"
\`\`\`

## Details

- **Priority:** Should Have
- **Story Points:** 3
- **Dependencies:** None
- **Category:** Collaboration Features

## Labels

\`user-story\`, \`should-have\`, \`collaboration-features\`
" \
  "${EPIC_NUMBERS[collaboration_features]}"

echo ""
echo -e "${GREEN}All issues created successfully!${NC}"
echo -e "${BLUE}Epic issues created: ${#EPIC_NUMBERS[@]}${NC}"
echo -e "${BLUE}User story issues created: 123${NC}"