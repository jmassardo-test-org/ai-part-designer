# GitHub Issues Creation from User Stories

This directory contains scripts to extract user stories from markdown files and create GitHub issues automatically.

## Overview

The `extract_user_stories.py` script processes all user story markdown files in `docs/planning/` and generates:

1. **user-stories-extracted.json** - A structured JSON file containing all extracted user stories
2. **create-github-issues.sh** - A bash script to create GitHub issues for all user stories and link them to epic issues

## Extracted User Stories Summary

- **Total User Stories:** 123
- **Total Categories (Epics):** 33
- **Priority Breakdown:**
  - Must Have: 43 stories
  - Should Have: 58 stories
  - Could Have: 22 stories

## Prerequisites

To run the issue creation script, you need:

1. **GitHub CLI (`gh`)** installed and authenticated
   ```bash
   # Install gh CLI (if not already installed)
   # macOS
   brew install gh
   
   # Linux
   curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
   sudo apt update
   sudo apt install gh
   
   # Authenticate
   gh auth login
   ```

2. **Repository access** - You must have permission to create issues in the `jmassardo/ai-part-designer` repository

## Usage

### Step 1: Extract User Stories (Optional - Already Done)

If you need to re-extract user stories from the markdown files:

```bash
cd /home/runner/work/ai-part-designer/ai-part-designer
python3 scripts/extract_user_stories.py
```

This will regenerate:
- `scripts/user-stories-extracted.json`
- `scripts/create-github-issues.sh`

### Step 2: Create GitHub Issues

**Important:** This script will create 123 user story issues + 33 epic issues = **156 total issues** in the repository.

```bash
cd /home/runner/work/ai-part-designer/ai-part-designer
./scripts/create-github-issues.sh
```

The script will:
1. Create epic issues for each category (33 epics)
2. Create individual issues for each user story (123 stories)
3. Link each user story to its parent epic via comments
4. Apply appropriate labels to each issue

### Step 3: Verify

After the script completes, verify:
- All epic issues are created with the `[EPIC]` prefix
- All user story issues are created with the `[US-XXX]` prefix
- Each user story has a comment linking to its epic
- Each epic has comments listing all its user stories

## Issue Structure

### Epic Issues

- **Title:** `[EPIC] Category Name`
- **Labels:** `epic`, `planning`
- **Body:** Contains a list of all user stories in the epic

### User Story Issues

- **Title:** `[US-XXX] Story Title`
- **Labels:** `user-story`, priority level, category
- **Body:** Contains:
  - User story description (As a... I want... So that...)
  - Acceptance criteria (Given-When-Then scenarios)
  - Priority, story points, dependencies, category

## Epic Categories

The 33 epic categories are:

1. AI Dimension Extraction (3 stories)
2. AI Intelligence Improvements (5 stories)
3. AI Performance & Manufacturing (7 stories)
4. AI Personalization (5 stories)
5. AI Slash Commands (3 stories)
6. Admin Dashboard (5 stories)
7. Administration (3 stories)
8. Chat History & Privacy (6 stories)
9. Chat-Style Generation Experience (2 stories)
10. Collaboration & Sharing (2 stories)
11. Collaboration Features (3 stories)
12. Component File Management (3 stories)
13. Dashboard & Projects (3 stories)
14. Design System & Theming (5 stories)
15. Enclosure Style Templates (4 stories)
16. File Alignment & CAD Combination (3 stories)
17. File Management (5 stories)
18. Layout Editor Enhancements (3 stories)
19. Logging & Audit (4 stories)
20. Mobile Application (4 stories)
21. Mounting Type Expansion (4 stories)
22. Multi-Language Support (2 stories)
23. OAuth Authentication (3 stories)
24. Onboarding Experience (2 stories)
25. Part Design & Generation (5 stories)
26. Payment & Subscription (4 stories)
27. Progressive Web App (3 stories)
28. Queue & Job Processing (4 stories)
29. Real-time Updates (2 stories)
30. Response Rating & Feedback (4 stories)
31. Sharing & Social (4 stories)
32. Subscription & Billing (3 stories)
33. User Authentication & Account Management (5 stories)

## Troubleshooting

### Script Fails with Authentication Error

If you see "authentication required" errors:
```bash
gh auth status
gh auth login
```

### Script Creates Duplicate Issues

The script does not check for existing issues. If you need to run it multiple times:
1. Delete all created issues manually or use:
   ```bash
   # List all issues
   gh issue list --repo jmassardo/ai-part-designer --limit 200
   
   # Close issues in bulk (be careful!)
   # This is just an example - adjust as needed
   ```

### Need to Modify User Stories

1. Edit the markdown files in `docs/planning/`
2. Re-run `python3 scripts/extract_user_stories.py`
3. Review the regenerated `create-github-issues.sh`
4. Run the script to create issues

## Files

- `extract_user_stories.py` - Python script to extract user stories from markdown
- `user-stories-extracted.json` - JSON output with all extracted stories (117 KB)
- `create-github-issues.sh` - Bash script to create GitHub issues (135 KB, 5689 lines)
- `README.md` - This file

## Notes

- The script uses the GitHub CLI (`gh`) to create issues
- Each epic and user story is linked via comments, not GitHub's native parent/child relationship (which requires GitHub Projects)
- Labels are applied to help with filtering and organization
- The script is idempotent within a run but will create duplicates if run multiple times

## Example Issue

**Epic:**
```
Title: [EPIC] AI Dimension Extraction
Labels: epic, planning
Body:
  # AI Dimension Extraction
  
  This epic tracks all user stories related to ai dimension extraction.
  
  ## User Stories
  
  - [ ] US-3001
  - [ ] US-3002
  - [ ] US-3003
```

**User Story:**
```
Title: [US-3001] Extract Dimensions from PDF Mechanical Drawings
Labels: user-story, must-have, ai-dimension-extraction
Body:
  ## User Story
  
  As auser preparing components for layout,  
  **I want** to upload a mechanical drawing PDF and extract dimensions,  
  **So that** I don't have to manually measure and input every value.
  
  ## Acceptance Criteria
  
  [Gherkin scenarios...]
  
  ## Details
  
  - Priority: Must Have
  - Story Points: 8
  - Dependencies: None
  - Category: AI Dimension Extraction
```

## Support

For issues or questions:
1. Check this README
2. Review the generated JSON file for data accuracy
3. Inspect the shell script for syntax errors
4. Check GitHub CLI documentation: https://cli.github.com/manual/
