"""
Tests for Tier Enforcement Middleware.

Tests tier limits configuration and feature access.
"""

import pytest

from app.middleware.tier_enforcement import TIER_LIMITS
from app.models.subscription import TierSlug

# =============================================================================
# TIER_LIMITS Configuration Tests
# =============================================================================


class TestTierLimitsConfiguration:
    """Tests for TIER_LIMITS configuration."""

    def test_limits_exist(self):
        """Test tier limits dictionary exists."""
        assert TIER_LIMITS is not None
        assert isinstance(TIER_LIMITS, dict)

    def test_all_tiers_have_limits(self):
        """Test all tier slugs have limits defined."""
        expected_tiers = [TierSlug.FREE, TierSlug.PRO, TierSlug.ENTERPRISE]

        for tier in expected_tiers:
            assert tier in TIER_LIMITS, f"Missing limits for tier: {tier}"


# =============================================================================
# Free Tier Tests
# =============================================================================


class TestFreeTierLimits:
    """Tests for free tier limits."""

    @pytest.fixture
    def free_limits(self):
        """Get free tier limits."""
        return TIER_LIMITS[TierSlug.FREE]

    def test_monthly_generations(self, free_limits):
        """Test free tier has limited monthly generations."""
        assert free_limits["monthly_generations"] == 10

    def test_monthly_refinements(self, free_limits):
        """Test free tier has limited monthly refinements."""
        assert free_limits["monthly_refinements"] == 5

    def test_max_projects(self, free_limits):
        """Test free tier project limit."""
        assert free_limits["max_projects"] == 5

    def test_max_designs_per_project(self, free_limits):
        """Test free tier designs per project limit."""
        assert free_limits["max_designs_per_project"] == 10

    def test_storage_limit(self, free_limits):
        """Test free tier storage limit."""
        assert free_limits["max_storage_gb"] == 1

    def test_file_size_limit(self, free_limits):
        """Test free tier file size limit."""
        assert free_limits["max_file_size_mb"] == 25

    def test_concurrent_jobs(self, free_limits):
        """Test free tier concurrent jobs limit."""
        assert free_limits["max_concurrent_jobs"] == 1

    def test_export_formats(self, free_limits):
        """Test free tier export formats."""
        assert "stl" in free_limits["export_formats"]
        assert "obj" in free_limits["export_formats"]
        # Premium formats should not be included
        assert "step" not in free_limits["export_formats"]

    def test_features_restricted(self, free_limits):
        """Test free tier has restricted features."""
        features = free_limits["features"]

        assert features["ai_generation"] is True
        assert features["export_2d"] is False
        assert features["collaboration"] is False
        assert features["api_access"] is False


# =============================================================================
# Pro Tier Tests
# =============================================================================


class TestProTierLimits:
    """Tests for pro tier limits."""

    @pytest.fixture
    def pro_limits(self):
        """Get pro tier limits."""
        return TIER_LIMITS[TierSlug.PRO]

    def test_monthly_generations(self, pro_limits):
        """Test pro tier has more monthly generations."""
        assert pro_limits["monthly_generations"] == 100

    def test_monthly_refinements(self, pro_limits):
        """Test pro tier has more refinements."""
        assert pro_limits["monthly_refinements"] == 50

    def test_max_projects(self, pro_limits):
        """Test pro tier project limit."""
        assert pro_limits["max_projects"] == 50

    def test_storage_limit(self, pro_limits):
        """Test pro tier storage limit."""
        assert pro_limits["max_storage_gb"] == 50

    def test_concurrent_jobs(self, pro_limits):
        """Test pro tier concurrent jobs."""
        assert pro_limits["max_concurrent_jobs"] == 5

    def test_export_formats_extended(self, pro_limits):
        """Test pro tier has more export formats."""
        formats = pro_limits["export_formats"]

        assert "stl" in formats
        assert "step" in formats
        assert "iges" in formats
        assert "3mf" in formats

    def test_features_expanded(self, pro_limits):
        """Test pro tier has expanded features."""
        features = pro_limits["features"]

        assert features["ai_generation"] is True
        assert features["export_2d"] is True
        assert features["collaboration"] is True
        assert features["priority_queue"] is True
        assert features["custom_templates"] is True


# =============================================================================
# Enterprise Tier Tests
# =============================================================================


class TestEnterpriseTierLimits:
    """Tests for enterprise tier limits."""

    @pytest.fixture
    def enterprise_limits(self):
        """Get enterprise tier limits."""
        return TIER_LIMITS[TierSlug.ENTERPRISE]

    def test_monthly_generations(self, enterprise_limits):
        """Test enterprise tier has high monthly generations."""
        assert enterprise_limits["monthly_generations"] == 1000

    def test_unlimited_projects(self, enterprise_limits):
        """Test enterprise tier has unlimited projects."""
        assert enterprise_limits["max_projects"] == -1

    def test_unlimited_designs(self, enterprise_limits):
        """Test enterprise tier has unlimited designs."""
        assert enterprise_limits["max_designs_per_project"] == -1

    def test_large_storage(self, enterprise_limits):
        """Test enterprise tier has large storage."""
        assert enterprise_limits["max_storage_gb"] >= 500

    def test_high_concurrent_jobs(self, enterprise_limits):
        """Test enterprise tier has many concurrent jobs."""
        assert enterprise_limits["max_concurrent_jobs"] >= 20

    def test_all_export_formats(self, enterprise_limits):
        """Test enterprise tier has all export formats."""
        formats = enterprise_limits["export_formats"]

        assert "dxf" in formats or "dwg" in formats

    def test_all_features_enabled(self, enterprise_limits):
        """Test enterprise tier has all features."""
        features = enterprise_limits["features"]

        assert features["ai_generation"] is True
        assert features["api_access"] is True


# =============================================================================
# Tier Comparison Tests
# =============================================================================


class TestTierComparison:
    """Tests comparing tier limits."""

    def test_pro_more_generous_than_free(self):
        """Test pro tier is more generous than free."""
        free = TIER_LIMITS[TierSlug.FREE]
        pro = TIER_LIMITS[TierSlug.PRO]

        assert pro["monthly_generations"] > free["monthly_generations"]
        assert pro["max_projects"] > free["max_projects"]
        assert pro["max_storage_gb"] > free["max_storage_gb"]
        assert pro["max_concurrent_jobs"] > free["max_concurrent_jobs"]

    def test_enterprise_most_generous(self):
        """Test enterprise tier is most generous."""
        pro = TIER_LIMITS[TierSlug.PRO]
        enterprise = TIER_LIMITS[TierSlug.ENTERPRISE]

        assert enterprise["monthly_generations"] > pro["monthly_generations"]
        assert enterprise["max_storage_gb"] > pro["max_storage_gb"]

    def test_feature_progression(self):
        """Test features expand with higher tiers."""
        free = TIER_LIMITS[TierSlug.FREE]["features"]
        pro = TIER_LIMITS[TierSlug.PRO]["features"]
        enterprise = TIER_LIMITS[TierSlug.ENTERPRISE]["features"]

        # Free has basic features only
        assert free["ai_generation"] is True
        assert free["export_2d"] is False

        # Pro adds more
        assert pro["export_2d"] is True
        assert pro["collaboration"] is True

        # Enterprise has everything
        assert enterprise["api_access"] is True


# =============================================================================
# Edge Cases
# =============================================================================


class TestTierEnforcementEdgeCases:
    """Tests for edge cases."""

    def test_unlimited_indicated_by_negative_one(self):
        """Test unlimited values are indicated by -1."""
        enterprise = TIER_LIMITS[TierSlug.ENTERPRISE]

        # -1 means unlimited
        assert enterprise["max_projects"] == -1
        assert enterprise["max_designs_per_project"] == -1

    def test_all_tiers_have_features_dict(self):
        """Test all tiers have features dictionary."""
        for tier in [TierSlug.FREE, TierSlug.PRO, TierSlug.ENTERPRISE]:
            limits = TIER_LIMITS[tier]
            assert "features" in limits
            assert isinstance(limits["features"], dict)

    def test_all_tiers_have_export_formats(self):
        """Test all tiers have export formats list."""
        for tier in [TierSlug.FREE, TierSlug.PRO, TierSlug.ENTERPRISE]:
            limits = TIER_LIMITS[tier]
            assert "export_formats" in limits
            assert isinstance(limits["export_formats"], list)
            assert len(limits["export_formats"]) > 0

    def test_all_numeric_limits_are_integers(self):
        """Test numeric limits are integers."""
        for tier, limits in TIER_LIMITS.items():
            for key in [
                "monthly_generations",
                "monthly_refinements",
                "max_projects",
                "max_designs_per_project",
                "max_storage_gb",
                "max_file_size_mb",
                "max_concurrent_jobs",
            ]:
                if key in limits:
                    assert isinstance(limits[key], int), f"{tier}.{key} should be int"
