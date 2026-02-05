"""
Seed data package.

Provides database seeding utilities for initial data population.
"""

from app.seeds.components_v2 import seed_components_v2
from app.seeds.examples import EXAMPLE_PROJECTS, copy_example_project, seed_example_projects
from app.seeds.marketplace import SAMPLE_DESIGN_LISTS, SAMPLE_FILES, seed_marketplace
from app.seeds.starters import STARTER_DESIGNS, seed_starters
from app.seeds.templates import TEMPLATE_SEEDS, seed_templates
from app.seeds.users import ENTERPRISE_ORGS, FREE_USERS, PLATFORM_ADMIN, PRO_USERS, seed_users

__all__ = [
    "ENTERPRISE_ORGS",
    "EXAMPLE_PROJECTS",
    "FREE_USERS",
    "PLATFORM_ADMIN",
    "PRO_USERS",
    "SAMPLE_DESIGN_LISTS",
    "SAMPLE_FILES",
    "STARTER_DESIGNS",
    "TEMPLATE_SEEDS",
    "copy_example_project",
    # CAD v2 Components
    "seed_components_v2",
    # Examples
    "seed_example_projects",
    # Marketplace
    "seed_marketplace",
    # Starters
    "seed_starters",
    # Templates
    "seed_templates",
    # Users
    "seed_users",
]
