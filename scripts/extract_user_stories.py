#!/usr/bin/env python3
"""
Extract user stories from markdown files and generate GitHub issue creation scripts.

This script parses user story markdown files and creates:
1. A JSON file with all extracted user stories
2. A bash script to create GitHub issues for each user story
3. Epic issues for each major category
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class UserStory:
    """Represents a single user story."""
    id: str
    title: str
    priority: str
    story_points: int
    dependencies: List[str]
    story: str
    acceptance_criteria: str
    category: str
    file_source: str
    
    def to_github_issue_body(self) -> str:
        """Generate GitHub issue body in markdown format."""
        body = f"""## User Story

{self.story}

## Acceptance Criteria

{self.acceptance_criteria}

## Details

- **Priority:** {self.priority}
- **Story Points:** {self.story_points}
- **Dependencies:** {', '.join(self.dependencies) if self.dependencies else 'None'}
- **Category:** {self.category}

## Labels

`user-story`, `{self.priority.lower().replace(' ', '-')}`, `{self.category.lower().replace(' & ', '-').replace(' ', '-')}`
"""
        return body


class UserStoryExtractor:
    """Extract user stories from markdown files."""
    
    def __init__(self, docs_dir: Path):
        self.docs_dir = docs_dir
        self.user_stories: List[UserStory] = []
        self.categories: Dict[str, List[str]] = {}
        
    def extract_from_file(self, file_path: Path) -> None:
        """Extract all user stories from a single markdown file."""
        print(f"Processing {file_path.name}...")
        
        content = file_path.read_text()
        
        # Extract category sections - support both numbered and Epic formats
        category_pattern1 = r'^## (\d+)\. (.+?)$'  # Format: ## 1. Category Name
        category_pattern2 = r'^## Epic \d+: (.+?)$'  # Format: ## Epic 1: Name
        story_pattern = r'^### (US-\d+): (.+?)$'
        
        current_category = "Uncategorized"
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Check for category header (both formats)
            category_match = re.match(category_pattern1, line)
            if category_match:
                current_category = category_match.group(2).strip()
                if current_category not in self.categories:
                    self.categories[current_category] = []
                i += 1
                continue
            
            category_match2 = re.match(category_pattern2, line)
            if category_match2:
                current_category = category_match2.group(1).strip()
                if current_category not in self.categories:
                    self.categories[current_category] = []
                i += 1
                continue
            
            # Check for user story header
            story_match = re.match(story_pattern, line)
            if story_match:
                story_id = story_match.group(1)
                story_title = story_match.group(2).strip()
                
                # Initialize category if needed
                if current_category not in self.categories:
                    self.categories[current_category] = []
                
                # Extract the full story section
                story_data = self._extract_story_section(lines, i)
                if story_data:
                    user_story = UserStory(
                        id=story_id,
                        title=story_title,
                        priority=story_data.get('priority', 'Should Have'),
                        story_points=story_data.get('story_points', 3),
                        dependencies=story_data.get('dependencies', []),
                        story=story_data.get('story', ''),
                        acceptance_criteria=story_data.get('acceptance_criteria', ''),
                        category=current_category,
                        file_source=file_path.name
                    )
                    self.user_stories.append(user_story)
                    self.categories[current_category].append(story_id)
                    print(f"  ✓ Extracted {story_id}: {story_title}")
                
            i += 1
    
    def _extract_story_section(self, lines: List[str], start_idx: int) -> Optional[Dict]:
        """Extract a complete user story section starting from the header line."""
        i = start_idx + 1
        section_lines = []
        
        # Collect lines until we hit the next story or section
        while i < len(lines):
            line = lines[i]
            # Stop at next user story or major section
            if re.match(r'^### US-\d+:', line) or re.match(r'^## (Epic |\d+\.)', line):
                break
            section_lines.append(line)
            i += 1
        
        section_text = '\n'.join(section_lines)
        
        # Extract table attributes
        priority = self._extract_table_value(section_text, 'Priority')
        story_points_str = self._extract_table_value(section_text, 'Story Points')
        dependencies_str = self._extract_table_value(section_text, 'Dependencies')
        
        # Parse priority - handle different formats (e.g., "P0 - Launch Blocker" -> "Must Have")
        if priority:
            if 'P0' in priority or 'Launch Blocker' in priority or 'Must Have' in priority:
                priority = 'Must Have'
            elif 'P1' in priority or 'Should Have' in priority:
                priority = 'Should Have'
            elif 'P2' in priority or 'Could Have' in priority:
                priority = 'Could Have'
            else:
                priority = 'Should Have'  # Default
        
        # Parse dependencies
        dependencies = []
        if dependencies_str and dependencies_str != 'None':
            dependencies = [d.strip() for d in dependencies_str.split(',')]
        
        # Extract story text - try multiple patterns
        story_match = re.search(r'\*\*Story:\*\*\s*\n(.+?)(?=\n\*\*Acceptance Criteria)', section_text, re.DOTALL)
        if not story_match:
            # Try alternative format: **As a** user, **I want** ... **So that** ...
            story_match = re.search(r'\*\*As a\*\*(.+?)(?=\n\||\n\*\*Acceptance Criteria)', section_text, re.DOTALL)
            if story_match:
                # Reconstruct the story format
                story = f"As a{story_match.group(1).strip()}"
            else:
                story = ''
        else:
            story = story_match.group(1).strip()
        
        # Extract acceptance criteria
        ac_match = re.search(r'\*\*Acceptance Criteria:\*\*\s*\n(.+?)(?=\n---|\n\*\*UI Mockup|\n\*\*Technical Notes|\n\*\*Dependencies|\Z)', section_text, re.DOTALL)
        acceptance_criteria = ac_match.group(1).strip() if ac_match else ''
        
        return {
            'priority': priority or 'Should Have',
            'story_points': int(story_points_str) if story_points_str and story_points_str.isdigit() else 3,
            'dependencies': dependencies,
            'story': story,
            'acceptance_criteria': acceptance_criteria
        }
    
    def _extract_table_value(self, text: str, attribute: str) -> Optional[str]:
        """Extract a value from a markdown table."""
        # Try exact match first
        pattern = rf'\| \*\*{attribute}\*\* \| (.+?) \|'
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        
        # Try alternative names for common attributes
        alternatives = {
            'Story Points': ['Points'],
            'Priority': ['Priority']
        }
        
        if attribute in alternatives:
            for alt in alternatives[attribute]:
                pattern = rf'\| \*\*{alt}\*\* \| (.+?) \|'
                match = re.search(pattern, text)
                if match:
                    return match.group(1).strip()
        
        return None
    
    def generate_issue_creation_script(self, output_path: Path) -> None:
        """Generate a bash script to create GitHub issues."""
        script_lines = [
            "#!/bin/bash",
            "#",
            "# GitHub Issues Creation Script",
            "# Generated from user story markdown files",
            "#",
            "# Prerequisites:",
            "#   - gh CLI installed and authenticated",
            "#   - Run from repository root directory",
            "#",
            "",
            "set -e  # Exit on error",
            "",
            "REPO='jmassardo/ai-part-designer'",
            "EPIC_PREFIX='EPIC'",
            "",
            "# Color output",
            "GREEN='\\033[0;32m'",
            "BLUE='\\033[0;34m'",
            "RED='\\033[0;31m'",
            "NC='\\033[0m' # No Color",
            "",
            "echo -e \"${BLUE}Creating GitHub issues from user stories...${NC}\"",
            "echo \"\"",
            "",
            "# Store epic issue numbers",
            "declare -A EPIC_NUMBERS",
            "",
            "# Function to create an epic issue",
            "create_epic() {",
            "  local title=\"$1\"",
            "  local description=\"$2\"",
            "  local category_key=\"$3\"",
            "  ",
            "  echo -e \"${BLUE}Creating epic: $title${NC}\"",
            "  ",
            "  ISSUE_URL=$(gh issue create \\",
            "    --repo \"$REPO\" \\",
            "    --title \"[EPIC] $title\" \\",
            "    --body \"$description\" \\",
            "    --label \"epic,planning\" | tail -n 1)",
            "  ",
            "  ISSUE_NUMBER=$(echo \"$ISSUE_URL\" | grep -oP '\\d+$')",
            "  EPIC_NUMBERS[\"$category_key\"]=\"$ISSUE_NUMBER\"",
            "  ",
            "  echo -e \"${GREEN}✓ Created epic #$ISSUE_NUMBER${NC}\"",
            "  echo \"\"",
            "}",
            "",
            "# Function to create a user story issue",
            "create_user_story() {",
            "  local story_id=\"$1\"",
            "  local title=\"$2\"",
            "  local body=\"$3\"",
            "  local epic_number=\"$4\"",
            "  ",
            "  echo -e \"Creating user story: $story_id - $title\"",
            "  ",
            "  # Create the issue",
            "  ISSUE_URL=$(gh issue create \\",
            "    --repo \"$REPO\" \\",
            "    --title \"[$story_id] $title\" \\",
            "    --body \"$body\" | tail -n 1)",
            "  ",
            "  ISSUE_NUMBER=$(echo \"$ISSUE_URL\" | grep -oP '\\d+$')",
            "  ",
            "  # Link to epic if epic number is provided",
            "  if [ -n \"$epic_number\" ] && [ \"$epic_number\" != \"0\" ]; then",
            "    # Add a comment linking to the epic",
            "    gh issue comment \"$ISSUE_NUMBER\" \\",
            "      --repo \"$REPO\" \\",
            "      --body \"Part of epic #$epic_number\"",
            "    ",
            "    # Add a comment to the epic with the story",
            "    gh issue comment \"$epic_number\" \\",
            "      --repo \"$REPO\" \\",
            "      --body \"- #$ISSUE_NUMBER - $story_id: $title\"",
            "  fi",
            "  ",
            "  echo -e \"${GREEN}✓ Created issue #$ISSUE_NUMBER${NC}\"",
            "}",
            "",
            "##############################################################################",
            "# EPIC ISSUES",
            "##############################################################################",
            "",
        ]
        
        # Create epic issues for each category
        for category, story_ids in sorted(self.categories.items()):
            if not story_ids:
                continue
                
            category_key = category.lower().replace(' & ', '_').replace(' ', '_')
            epic_description = f"""# {category}

This epic tracks all user stories related to {category.lower()}.

## User Stories

This epic contains {len(story_ids)} user stories:

{chr(10).join(f'- [ ] {sid}' for sid in story_ids)}

## Progress

Track progress as individual user story issues are completed.
"""
            
            script_lines.extend([
                f"# Epic: {category}",
                f"create_epic \\",
                f"  \"{category}\" \\",
                f"  \"{epic_description}\" \\",
                f"  \"{category_key}\"",
                "",
            ])
        
        script_lines.extend([
            "##############################################################################",
            "# USER STORY ISSUES",
            "##############################################################################",
            "",
        ])
        
        # Create issues for each user story
        for story in sorted(self.user_stories, key=lambda s: s.id):
            category_key = story.category.lower().replace(' & ', '_').replace(' ', '_')
            
            # Escape special characters for bash
            body = story.to_github_issue_body().replace('"', '\\"').replace('`', '\\`').replace('$', '\\$')
            
            script_lines.extend([
                f"# {story.id}: {story.title}",
                f"create_user_story \\",
                f"  \"{story.id}\" \\",
                f"  \"{story.title}\" \\",
                f"  \"{body}\" \\",
                f"  \"${{EPIC_NUMBERS[{category_key}]}}\"",
                "",
            ])
        
        script_lines.extend([
            "echo \"\"",
            "echo -e \"${GREEN}All issues created successfully!${NC}\"",
            "echo -e \"${BLUE}Epic issues created: ${#EPIC_NUMBERS[@]}${NC}\"",
            f"echo -e \"${{BLUE}}User story issues created: {len(self.user_stories)}${{NC}}\"",
        ])
        
        output_path.write_text('\n'.join(script_lines))
        output_path.chmod(0o755)  # Make executable
        print(f"\n✓ Generated script: {output_path}")
    
    def save_json(self, output_path: Path) -> None:
        """Save all user stories as JSON."""
        data = {
            'categories': self.categories,
            'user_stories': [asdict(story) for story in self.user_stories],
            'summary': {
                'total_stories': len(self.user_stories),
                'total_categories': len(self.categories),
                'by_priority': self._count_by_priority(),
                'by_category': {cat: len(stories) for cat, stories in self.categories.items()}
            }
        }
        
        output_path.write_text(json.dumps(data, indent=2))
        print(f"✓ Saved JSON: {output_path}")
    
    def _count_by_priority(self) -> Dict[str, int]:
        """Count user stories by priority."""
        counts = {}
        for story in self.user_stories:
            priority = story.priority
            counts[priority] = counts.get(priority, 0) + 1
        return counts
    
    def print_summary(self) -> None:
        """Print extraction summary."""
        print("\n" + "="*80)
        print("EXTRACTION SUMMARY")
        print("="*80)
        print(f"Total user stories: {len(self.user_stories)}")
        print(f"Total categories: {len(self.categories)}")
        print("\nBy Category:")
        for category, story_ids in sorted(self.categories.items()):
            print(f"  {category}: {len(story_ids)} stories")
        print("\nBy Priority:")
        for priority, count in sorted(self._count_by_priority().items()):
            print(f"  {priority}: {count} stories")
        print("="*80 + "\n")


def main():
    """Main execution."""
    # Setup paths
    repo_root = Path(__file__).parent.parent
    docs_dir = repo_root / 'docs' / 'planning'
    output_dir = repo_root / 'scripts'
    output_dir.mkdir(exist_ok=True)
    
    # Initialize extractor
    extractor = UserStoryExtractor(docs_dir)
    
    # Process all user story files
    story_files = [
        'user-stories-detailed.md',
        'user-stories-phase-4.md',
        'user-stories-phase-5.md',
    ]
    
    for filename in story_files:
        file_path = docs_dir / filename
        if file_path.exists():
            extractor.extract_from_file(file_path)
        else:
            print(f"Warning: {filename} not found")
    
    # Generate outputs
    extractor.save_json(output_dir / 'user-stories-extracted.json')
    extractor.generate_issue_creation_script(output_dir / 'create-github-issues.sh')
    extractor.print_summary()
    
    print("\nNext steps:")
    print("1. Review the generated files:")
    print("   - scripts/user-stories-extracted.json")
    print("   - scripts/create-github-issues.sh")
    print("2. Run the script to create issues:")
    print("   cd /home/runner/work/ai-part-designer/ai-part-designer")
    print("   ./scripts/create-github-issues.sh")


if __name__ == '__main__':
    main()
