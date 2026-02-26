"""
Tests for the license catalog and helper functions.

Tests all license types, metadata lookup, validation, remix permission,
and share-alike compatibility logic.
"""

from __future__ import annotations

import pytest

from app.core.licenses import (
    LICENSE_METADATA,
    LicenseInfo,
    LicenseType,
    allows_remix,
    get_license_metadata,
    get_share_alike_compatible_licenses,
    is_valid_license_type,
)

# =============================================================================
# LicenseType Enum Tests
# =============================================================================


class TestLicenseType:
    """Tests for the LicenseType enum."""

    def test_all_license_types_are_strings(self) -> None:
        """All LicenseType values should be valid strings."""
        for lt in LicenseType:
            assert isinstance(lt.value, str)
            assert len(lt.value) > 0

    def test_license_type_count(self) -> None:
        """There should be exactly 9 license types."""
        assert len(LicenseType) == 9

    def test_cc_by_4_0_value(self) -> None:
        """CC-BY-4.0 has the correct string value."""
        assert LicenseType.CC_BY_4_0 == "CC-BY-4.0"

    def test_cc_by_sa_4_0_value(self) -> None:
        """CC-BY-SA-4.0 has the correct string value."""
        assert LicenseType.CC_BY_SA_4_0 == "CC-BY-SA-4.0"

    def test_cc_by_nc_4_0_value(self) -> None:
        """CC-BY-NC-4.0 has the correct string value."""
        assert LicenseType.CC_BY_NC_4_0 == "CC-BY-NC-4.0"

    def test_cc_by_nc_sa_4_0_value(self) -> None:
        """CC-BY-NC-SA-4.0 has the correct string value."""
        assert LicenseType.CC_BY_NC_SA_4_0 == "CC-BY-NC-SA-4.0"

    def test_cc_by_nd_4_0_value(self) -> None:
        """CC-BY-ND-4.0 has the correct string value."""
        assert LicenseType.CC_BY_ND_4_0 == "CC-BY-ND-4.0"

    def test_cc_by_nc_nd_4_0_value(self) -> None:
        """CC-BY-NC-ND-4.0 has the correct string value."""
        assert LicenseType.CC_BY_NC_ND_4_0 == "CC-BY-NC-ND-4.0"

    def test_cc0_1_0_value(self) -> None:
        """CC0-1.0 has the correct string value."""
        assert LicenseType.CC0_1_0 == "CC0-1.0"

    def test_all_rights_reserved_value(self) -> None:
        """ALL-RIGHTS-RESERVED has the correct string value."""
        assert LicenseType.ALL_RIGHTS_RESERVED == "ALL-RIGHTS-RESERVED"

    def test_custom_value(self) -> None:
        """CUSTOM has the correct string value."""
        assert LicenseType.CUSTOM == "CUSTOM"

    def test_license_type_from_string(self) -> None:
        """LicenseType can be constructed from its string value."""
        assert LicenseType("CC-BY-4.0") is LicenseType.CC_BY_4_0

    def test_invalid_license_type_raises(self) -> None:
        """Creating LicenseType with invalid string raises ValueError."""
        with pytest.raises(ValueError):
            LicenseType("INVALID-TYPE")


# =============================================================================
# LicenseInfo Dataclass Tests
# =============================================================================


class TestLicenseInfo:
    """Tests for the LicenseInfo frozen dataclass."""

    def test_license_info_is_frozen(self) -> None:
        """LicenseInfo instances should be immutable."""
        info = LicenseInfo(
            spdx_id="TEST",
            name="Test License",
            url="https://example.com",
            allows_remix=True,
            requires_attribution=True,
            allows_commercial=True,
            requires_share_alike=False,
            icon="test",
        )
        with pytest.raises(AttributeError):
            info.name = "Modified"  # type: ignore[misc]

    def test_license_info_equality(self) -> None:
        """Two LicenseInfo with same fields should be equal."""
        info1 = LicenseInfo(
            spdx_id="X", name="X", url=None,
            allows_remix=True, requires_attribution=False,
            allows_commercial=True, requires_share_alike=False,
            icon="x",
        )
        info2 = LicenseInfo(
            spdx_id="X", name="X", url=None,
            allows_remix=True, requires_attribution=False,
            allows_commercial=True, requires_share_alike=False,
            icon="x",
        )
        assert info1 == info2


# =============================================================================
# LICENSE_METADATA Catalog Tests
# =============================================================================


class TestLicenseMetadata:
    """Tests for the LICENSE_METADATA dictionary."""

    def test_all_license_types_have_metadata(self) -> None:
        """Every LicenseType should have a corresponding metadata entry."""
        for lt in LicenseType:
            assert lt in LICENSE_METADATA, f"Missing metadata for {lt}"

    def test_metadata_count_matches_types(self) -> None:
        """Metadata dict should have the same count as LicenseType."""
        assert len(LICENSE_METADATA) == len(LicenseType)

    def test_all_metadata_spdx_ids_match_keys(self) -> None:
        """Each metadata entry's spdx_id should match its LicenseType value."""
        for lt, info in LICENSE_METADATA.items():
            assert info.spdx_id == lt.value

    def test_cc_by_4_0_allows_remix(self) -> None:
        """CC-BY-4.0 allows remixing."""
        info = LICENSE_METADATA[LicenseType.CC_BY_4_0]
        assert info.allows_remix is True

    def test_cc_by_4_0_requires_attribution(self) -> None:
        """CC-BY-4.0 requires attribution."""
        info = LICENSE_METADATA[LicenseType.CC_BY_4_0]
        assert info.requires_attribution is True

    def test_cc_by_4_0_allows_commercial(self) -> None:
        """CC-BY-4.0 allows commercial use."""
        info = LICENSE_METADATA[LicenseType.CC_BY_4_0]
        assert info.allows_commercial is True

    def test_cc_by_sa_requires_share_alike(self) -> None:
        """CC-BY-SA-4.0 requires share-alike."""
        info = LICENSE_METADATA[LicenseType.CC_BY_SA_4_0]
        assert info.requires_share_alike is True

    def test_cc_by_nc_disallows_commercial(self) -> None:
        """CC-BY-NC-4.0 disallows commercial use."""
        info = LICENSE_METADATA[LicenseType.CC_BY_NC_4_0]
        assert info.allows_commercial is False

    def test_cc_by_nd_disallows_remix(self) -> None:
        """CC-BY-ND-4.0 does not allow remixing."""
        info = LICENSE_METADATA[LicenseType.CC_BY_ND_4_0]
        assert info.allows_remix is False

    def test_cc0_no_attribution_required(self) -> None:
        """CC0-1.0 does not require attribution."""
        info = LICENSE_METADATA[LicenseType.CC0_1_0]
        assert info.requires_attribution is False
        assert info.allows_remix is True
        assert info.allows_commercial is True

    def test_all_rights_reserved_no_remix(self) -> None:
        """ALL-RIGHTS-RESERVED disallows remixing and commercial use."""
        info = LICENSE_METADATA[LicenseType.ALL_RIGHTS_RESERVED]
        assert info.allows_remix is False
        assert info.allows_commercial is False

    def test_custom_defaults_no_remix(self) -> None:
        """CUSTOM defaults to no remix (actual value from design field)."""
        info = LICENSE_METADATA[LicenseType.CUSTOM]
        assert info.allows_remix is False

    def test_all_metadata_entries_have_icon(self) -> None:
        """Every metadata entry should have a non-empty icon."""
        for lt, info in LICENSE_METADATA.items():
            assert info.icon, f"Missing icon for {lt}"

    def test_all_cc_licenses_have_urls(self) -> None:
        """All CC licenses should have a URL, proprietary ones may not."""
        cc_types = [lt for lt in LicenseType if lt.value.startswith("CC")]
        for lt in cc_types:
            info = LICENSE_METADATA[lt]
            assert info.url is not None, f"Missing URL for {lt}"
            assert info.url.startswith("https://"), f"URL should be https for {lt}"


# =============================================================================
# get_license_metadata Tests
# =============================================================================


class TestGetLicenseMetadata:
    """Tests for the get_license_metadata function."""

    def test_get_valid_license_returns_info(self) -> None:
        """Valid license type string returns LicenseInfo."""
        info = get_license_metadata("CC-BY-4.0")
        assert info is not None
        assert info.spdx_id == "CC-BY-4.0"

    def test_get_all_valid_types_return_info(self) -> None:
        """All valid license type strings return LicenseInfo."""
        for lt in LicenseType:
            info = get_license_metadata(lt.value)
            assert info is not None, f"get_license_metadata returned None for {lt.value}"

    def test_get_invalid_license_returns_none(self) -> None:
        """Invalid license type string returns None."""
        assert get_license_metadata("INVALID") is None

    def test_get_empty_string_returns_none(self) -> None:
        """Empty string returns None."""
        assert get_license_metadata("") is None

    def test_get_case_sensitive(self) -> None:
        """License lookup is case-sensitive (SPDX IDs are exact)."""
        # Lowercase should not match
        assert get_license_metadata("cc-by-4.0") is None


# =============================================================================
# is_valid_license_type Tests
# =============================================================================


class TestIsValidLicenseType:
    """Tests for the is_valid_license_type function."""

    def test_all_license_types_are_valid(self) -> None:
        """All LicenseType values should return True."""
        for lt in LicenseType:
            assert is_valid_license_type(lt.value) is True, f"Expected {lt.value} to be valid"

    def test_invalid_type_returns_false(self) -> None:
        """Unknown strings should return False."""
        assert is_valid_license_type("NOT-A-LICENSE") is False

    def test_empty_string_returns_false(self) -> None:
        """Empty string should return False."""
        assert is_valid_license_type("") is False

    def test_none_like_string_returns_false(self) -> None:
        """String 'None' should return False."""
        assert is_valid_license_type("None") is False


# =============================================================================
# allows_remix Tests
# =============================================================================


class TestAllowsRemix:
    """Tests for the allows_remix function."""

    def test_cc_by_allows_remix(self) -> None:
        """CC-BY-4.0 allows remixing."""
        assert allows_remix("CC-BY-4.0") is True

    def test_cc_by_sa_allows_remix(self) -> None:
        """CC-BY-SA-4.0 allows remixing (with share-alike constraint)."""
        assert allows_remix("CC-BY-SA-4.0") is True

    def test_cc_by_nc_allows_remix(self) -> None:
        """CC-BY-NC-4.0 allows remixing (non-commercially)."""
        assert allows_remix("CC-BY-NC-4.0") is True

    def test_cc_by_nd_disallows_remix(self) -> None:
        """CC-BY-ND-4.0 does not allow remixing."""
        assert allows_remix("CC-BY-ND-4.0") is False

    def test_cc_by_nc_nd_disallows_remix(self) -> None:
        """CC-BY-NC-ND-4.0 does not allow remixing."""
        assert allows_remix("CC-BY-NC-ND-4.0") is False

    def test_cc0_allows_remix(self) -> None:
        """CC0-1.0 (public domain) allows remixing."""
        assert allows_remix("CC0-1.0") is True

    def test_all_rights_reserved_disallows_remix(self) -> None:
        """ALL-RIGHTS-RESERVED does not allow remixing."""
        assert allows_remix("ALL-RIGHTS-RESERVED") is False

    def test_custom_without_flag_disallows_remix(self) -> None:
        """CUSTOM license without custom_allows_remix=True disallows remixing."""
        assert allows_remix("CUSTOM", custom_allows_remix=False) is False

    def test_custom_with_flag_allows_remix(self) -> None:
        """CUSTOM license with custom_allows_remix=True allows remixing."""
        assert allows_remix("CUSTOM", custom_allows_remix=True) is True

    def test_invalid_type_disallows_remix(self) -> None:
        """Unknown license types default to disallowing remix."""
        assert allows_remix("UNKNOWN") is False

    def test_empty_string_disallows_remix(self) -> None:
        """Empty string default to disallowing remix."""
        assert allows_remix("") is False


# =============================================================================
# get_share_alike_compatible_licenses Tests
# =============================================================================


class TestGetShareAlikeCompatibleLicenses:
    """Tests for the get_share_alike_compatible_licenses function."""

    def test_cc_by_sa_only_allows_same_license(self) -> None:
        """CC-BY-SA-4.0 derivatives must use CC-BY-SA-4.0."""
        compatible = get_share_alike_compatible_licenses("CC-BY-SA-4.0")
        assert compatible == ["CC-BY-SA-4.0"]

    def test_cc_by_nc_sa_only_allows_same_license(self) -> None:
        """CC-BY-NC-SA-4.0 derivatives must use CC-BY-NC-SA-4.0."""
        compatible = get_share_alike_compatible_licenses("CC-BY-NC-SA-4.0")
        assert compatible == ["CC-BY-NC-SA-4.0"]

    def test_cc_by_allows_any_license(self) -> None:
        """CC-BY-4.0 (no share-alike) allows any license for derivatives."""
        compatible = get_share_alike_compatible_licenses("CC-BY-4.0")
        # Should contain all license types
        assert len(compatible) == len(LicenseType)
        for lt in LicenseType:
            assert lt.value in compatible

    def test_cc0_allows_any_license(self) -> None:
        """CC0-1.0 (public domain) allows any license for derivatives."""
        compatible = get_share_alike_compatible_licenses("CC0-1.0")
        assert len(compatible) == len(LicenseType)

    def test_all_rights_reserved_allows_any(self) -> None:
        """ALL-RIGHTS-RESERVED (no share-alike) returns all license types."""
        compatible = get_share_alike_compatible_licenses("ALL-RIGHTS-RESERVED")
        assert len(compatible) == len(LicenseType)

    def test_invalid_type_returns_empty_list(self) -> None:
        """Unknown license type returns empty list."""
        assert get_share_alike_compatible_licenses("INVALID") == []

    def test_empty_string_returns_empty_list(self) -> None:
        """Empty string returns empty list."""
        assert get_share_alike_compatible_licenses("") == []

    def test_custom_license_allows_any(self) -> None:
        """CUSTOM license (no share-alike by default) allows any license."""
        compatible = get_share_alike_compatible_licenses("CUSTOM")
        assert len(compatible) == len(LicenseType)
