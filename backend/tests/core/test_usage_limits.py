"""
Tests for Core Usage Limits Module.

Tests user tiers, tier limits configuration, and quota management.
"""

import pytest

from app.core.usage_limits import (
    UserTier,
    TIER_LIMITS,
)


# =============================================================================
# UserTier Tests
# =============================================================================

class TestUserTier:
    """Tests for UserTier enum."""

    def test_free_tier(self):
        """Test free tier."""
        assert UserTier.FREE == "free"

    def test_pro_tier(self):
        """Test pro tier."""
        assert UserTier.PRO == "pro"

    def test_enterprise_tier(self):
        """Test enterprise tier."""
        assert UserTier.ENTERPRISE == "enterprise"

    def test_admin_tier(self):
        """Test admin tier."""
        assert UserTier.ADMIN == "admin"

    def test_all_tiers_are_strings(self):
        """Test all tiers are strings."""
        for tier in UserTier:
            assert isinstance(tier.value, str)


# =============================================================================
# TIER_LIMITS Configuration Tests
# =============================================================================

class TestTierLimits:
    """Tests for TIER_LIMITS configuration."""

    def test_limits_exist(self):
        """Test tier limits dictionary exists."""
        assert TIER_LIMITS is not None
        assert isinstance(TIER_LIMITS, dict)

    def test_all_tiers_have_limits(self):
        """Test all user tiers have limits defined."""
        for tier in UserTier:
            assert tier in TIER_LIMITS, f"Missing limits for tier: {tier}"

    def test_free_tier_generation_limits(self):
        """Test free tier has generation limits."""
        limits = TIER_LIMITS[UserTier.FREE]
        
        assert "generations_per_day" in limits
        assert "generations_per_month" in limits
        assert "concurrent_generations" in limits

    def test_free_tier_values(self):
        """Test free tier has restrictive limits."""
        limits = TIER_LIMITS[UserTier.FREE]
        
        assert limits["generations_per_day"] == 5
        assert limits["generations_per_month"] == 50
        assert limits["concurrent_generations"] == 1

    def test_pro_tier_generation_limits(self):
        """Test pro tier has higher generation limits."""
        limits = TIER_LIMITS[UserTier.PRO]
        
        assert limits["generations_per_day"] == 50
        assert limits["generations_per_month"] == 500
        assert limits["concurrent_generations"] == 3

    def test_storage_limits_exist(self):
        """Test storage limits are defined."""
        for tier in [UserTier.FREE, UserTier.PRO]:
            limits = TIER_LIMITS[tier]
            assert "storage_bytes" in limits
            assert "max_file_size_bytes" in limits
            assert "max_files" in limits

    def test_free_storage_limits(self):
        """Test free tier storage limits."""
        limits = TIER_LIMITS[UserTier.FREE]
        
        # 500 MB
        assert limits["storage_bytes"] == 500 * 1024 * 1024
        # 25 MB max file
        assert limits["max_file_size_bytes"] == 25 * 1024 * 1024
        assert limits["max_files"] == 50

    def test_pro_storage_limits(self):
        """Test pro tier storage limits."""
        limits = TIER_LIMITS[UserTier.PRO]
        
        # 10 GB
        assert limits["storage_bytes"] == 10 * 1024 * 1024 * 1024
        # 100 MB max file
        assert limits["max_file_size_bytes"] == 100 * 1024 * 1024

    def test_project_limits_exist(self):
        """Test project limits are defined."""
        for tier in [UserTier.FREE, UserTier.PRO]:
            limits = TIER_LIMITS[tier]
            assert "max_projects" in limits
            assert "max_designs_per_project" in limits

    def test_free_project_limits(self):
        """Test free tier project limits."""
        limits = TIER_LIMITS[UserTier.FREE]
        
        assert limits["max_projects"] == 5
        assert limits["max_designs_per_project"] == 20

    def test_pro_has_more_projects(self):
        """Test pro tier has more projects than free."""
        free_limits = TIER_LIMITS[UserTier.FREE]
        pro_limits = TIER_LIMITS[UserTier.PRO]
        
        assert pro_limits["max_projects"] > free_limits["max_projects"]
        assert pro_limits["max_designs_per_project"] > free_limits["max_designs_per_project"]

    def test_modification_limits_exist(self):
        """Test modification limits are defined."""
        for tier in [UserTier.FREE, UserTier.PRO]:
            limits = TIER_LIMITS[tier]
            assert "modifications_per_day" in limits
            assert "modifications_per_month" in limits

    def test_export_limits_exist(self):
        """Test export limits are defined."""
        for tier in [UserTier.FREE, UserTier.PRO]:
            limits = TIER_LIMITS[tier]
            assert "exports_per_day" in limits
            assert "exports_per_month" in limits

    def test_api_limits_exist(self):
        """Test API limits are defined."""
        for tier in [UserTier.FREE, UserTier.PRO]:
            limits = TIER_LIMITS[tier]
            assert "api_calls_per_minute" in limits
            assert "api_calls_per_day" in limits

    def test_component_limits_exist(self):
        """Test component limits are defined."""
        for tier in [UserTier.FREE, UserTier.PRO]:
            limits = TIER_LIMITS[tier]
            assert "max_components" in limits
            assert "component_extractions_per_day" in limits

    def test_assembly_limits_exist(self):
        """Test assembly limits are defined."""
        for tier in [UserTier.FREE, UserTier.PRO]:
            limits = TIER_LIMITS[tier]
            assert "max_assemblies" in limits
            assert "max_components_per_assembly" in limits


# =============================================================================
# Tier Comparison Tests
# =============================================================================

class TestTierComparison:
    """Tests for comparing tier limits."""

    def test_pro_more_generous_than_free(self):
        """Test pro tier is more generous than free."""
        free = TIER_LIMITS[UserTier.FREE]
        pro = TIER_LIMITS[UserTier.PRO]
        
        assert pro["generations_per_day"] > free["generations_per_day"]
        assert pro["generations_per_month"] > free["generations_per_month"]
        assert pro["storage_bytes"] > free["storage_bytes"]
        assert pro["max_projects"] > free["max_projects"]

    def test_all_limits_are_positive(self):
        """Test all limit values are positive."""
        for tier, limits in TIER_LIMITS.items():
            for key, value in limits.items():
                assert value > 0, f"{tier}.{key} should be positive"

    def test_limits_are_integers(self):
        """Test all limits are integers."""
        for tier, limits in TIER_LIMITS.items():
            for key, value in limits.items():
                assert isinstance(value, int), f"{tier}.{key} should be int"


# =============================================================================
# Edge Cases
# =============================================================================

class TestUsageLimitsEdgeCases:
    """Tests for edge cases in usage limits."""

    def test_free_tier_has_all_required_keys(self):
        """Test free tier has all expected limit keys."""
        required_keys = [
            "generations_per_day",
            "generations_per_month",
            "concurrent_generations",
            "modifications_per_day",
            "modifications_per_month",
            "storage_bytes",
            "max_file_size_bytes",
            "max_files",
            "max_projects",
            "max_designs_per_project",
            "max_components",
            "component_extractions_per_day",
            "max_assemblies",
            "max_components_per_assembly",
            "exports_per_day",
            "exports_per_month",
            "api_calls_per_minute",
            "api_calls_per_day",
        ]
        
        free_limits = TIER_LIMITS[UserTier.FREE]
        
        for key in required_keys:
            assert key in free_limits, f"Missing key: {key}"

    def test_storage_bytes_reasonable(self):
        """Test storage limits are reasonable values."""
        free_storage = TIER_LIMITS[UserTier.FREE]["storage_bytes"]
        pro_storage = TIER_LIMITS[UserTier.PRO]["storage_bytes"]
        
        # Free should be at least 100 MB
        assert free_storage >= 100 * 1024 * 1024
        
        # Pro should be at least 1 GB
        assert pro_storage >= 1 * 1024 * 1024 * 1024

    def test_concurrent_generations_reasonable(self):
        """Test concurrent limits are reasonable."""
        free = TIER_LIMITS[UserTier.FREE]["concurrent_generations"]
        pro = TIER_LIMITS[UserTier.PRO]["concurrent_generations"]
        
        # Should allow at least 1
        assert free >= 1
        # Pro should allow more
        assert pro >= free
