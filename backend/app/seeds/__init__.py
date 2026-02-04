"""
Seed data package.

Provides database seeding utilities for initial data population.
"""

from app.seeds.templates import seed_templates, TEMPLATE_SEEDS
from app.seeds.users import seed_users, PLATFORM_ADMIN, FREE_USERS, PRO_USERS, ENTERPRISE_ORGS
from app.seeds.components_v2 import seed_components_v2
from app.seeds.starters import seed_starters, STARTER_DESIGNS
from app.seeds.marketplace import seed_marketplace, SAMPLE_DESIGN_LISTS, SAMPLE_FILES
from app.seeds.examples import seed_example_projects, copy_example_project, EXAMPLE_PROJECTS

__all__ = [
    # Templates
    "seed_templates",
    "TEMPLATE_SEEDS",
    # Users
    "seed_users",
    "PLATFORM_ADMIN",
    "FREE_USERS",
    "PRO_USERS",
    "ENTERPRISE_ORGS",
    # CAD v2 Components
    "seed_components_v2",
    # Starters
    "seed_starters",
    "STARTER_DESIGNS",
    # Marketplace
    "seed_marketplace",
    "SAMPLE_DESIGN_LISTS",
    "SAMPLE_FILES",
    # Examples
    "seed_example_projects",
    "copy_example_project",
    "EXAMPLE_PROJECTS",
]
