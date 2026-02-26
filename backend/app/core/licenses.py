"""
License type catalog and metadata for the marketplace licensing system.

Defines the closed set of supported license types and their properties.
These are code constants (not DB-managed) because the license catalog
evolves infrequently and benefits from static type checking.
"""

from dataclasses import dataclass
from enum import StrEnum


class LicenseType(StrEnum):
    """Supported license types for marketplace designs."""

    CC_BY_4_0 = "CC-BY-4.0"
    CC_BY_SA_4_0 = "CC-BY-SA-4.0"
    CC_BY_NC_4_0 = "CC-BY-NC-4.0"
    CC_BY_NC_SA_4_0 = "CC-BY-NC-SA-4.0"
    CC_BY_ND_4_0 = "CC-BY-ND-4.0"
    CC_BY_NC_ND_4_0 = "CC-BY-NC-ND-4.0"
    CC0_1_0 = "CC0-1.0"
    ALL_RIGHTS_RESERVED = "ALL-RIGHTS-RESERVED"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True)
class LicenseInfo:
    """Immutable metadata for a license type.

    Attributes:
        spdx_id: SPDX or SPDX-like identifier for the license.
        name: Human-readable name for the license.
        url: URL to the full license text (None for custom/proprietary).
        allows_remix: Whether the license permits derivative works.
        requires_attribution: Whether attribution is required.
        allows_commercial: Whether commercial use is allowed.
        requires_share_alike: Whether derivatives must use the same license.
        icon: Icon identifier for UI rendering.
    """

    spdx_id: str
    name: str
    url: str | None
    allows_remix: bool
    requires_attribution: bool
    allows_commercial: bool
    requires_share_alike: bool
    icon: str


# Full license metadata catalog keyed by LicenseType
LICENSE_METADATA: dict[LicenseType, LicenseInfo] = {
    LicenseType.CC_BY_4_0: LicenseInfo(
        spdx_id="CC-BY-4.0",
        name="Creative Commons Attribution 4.0",
        url="https://creativecommons.org/licenses/by/4.0/",
        allows_remix=True,
        requires_attribution=True,
        allows_commercial=True,
        requires_share_alike=False,
        icon="cc-by",
    ),
    LicenseType.CC_BY_SA_4_0: LicenseInfo(
        spdx_id="CC-BY-SA-4.0",
        name="Creative Commons Attribution-ShareAlike 4.0",
        url="https://creativecommons.org/licenses/by-sa/4.0/",
        allows_remix=True,
        requires_attribution=True,
        allows_commercial=True,
        requires_share_alike=True,
        icon="cc-by-sa",
    ),
    LicenseType.CC_BY_NC_4_0: LicenseInfo(
        spdx_id="CC-BY-NC-4.0",
        name="Creative Commons Attribution-NonCommercial 4.0",
        url="https://creativecommons.org/licenses/by-nc/4.0/",
        allows_remix=True,
        requires_attribution=True,
        allows_commercial=False,
        requires_share_alike=False,
        icon="cc-by-nc",
    ),
    LicenseType.CC_BY_NC_SA_4_0: LicenseInfo(
        spdx_id="CC-BY-NC-SA-4.0",
        name="Creative Commons Attribution-NonCommercial-ShareAlike 4.0",
        url="https://creativecommons.org/licenses/by-nc-sa/4.0/",
        allows_remix=True,
        requires_attribution=True,
        allows_commercial=False,
        requires_share_alike=True,
        icon="cc-by-nc-sa",
    ),
    LicenseType.CC_BY_ND_4_0: LicenseInfo(
        spdx_id="CC-BY-ND-4.0",
        name="Creative Commons Attribution-NoDerivatives 4.0",
        url="https://creativecommons.org/licenses/by-nd/4.0/",
        allows_remix=False,
        requires_attribution=True,
        allows_commercial=True,
        requires_share_alike=False,
        icon="cc-by-nd",
    ),
    LicenseType.CC_BY_NC_ND_4_0: LicenseInfo(
        spdx_id="CC-BY-NC-ND-4.0",
        name="Creative Commons Attribution-NonCommercial-NoDerivatives 4.0",
        url="https://creativecommons.org/licenses/by-nc-nd/4.0/",
        allows_remix=False,
        requires_attribution=True,
        allows_commercial=False,
        requires_share_alike=False,
        icon="cc-by-nc-nd",
    ),
    LicenseType.CC0_1_0: LicenseInfo(
        spdx_id="CC0-1.0",
        name="Creative Commons Zero 1.0 (Public Domain)",
        url="https://creativecommons.org/publicdomain/zero/1.0/",
        allows_remix=True,
        requires_attribution=False,
        allows_commercial=True,
        requires_share_alike=False,
        icon="cc-zero",
    ),
    LicenseType.ALL_RIGHTS_RESERVED: LicenseInfo(
        spdx_id="ALL-RIGHTS-RESERVED",
        name="All Rights Reserved",
        url=None,
        allows_remix=False,
        requires_attribution=False,
        allows_commercial=False,
        requires_share_alike=False,
        icon="lock",
    ),
    LicenseType.CUSTOM: LicenseInfo(
        spdx_id="CUSTOM",
        name="Custom License",
        url=None,
        allows_remix=False,  # Default; actual value comes from custom_allows_remix field
        requires_attribution=False,
        allows_commercial=False,
        requires_share_alike=False,
        icon="file-text",
    ),
}


def get_license_metadata(license_type: str) -> LicenseInfo | None:
    """Get metadata for a license type by its string identifier.

    Args:
        license_type: SPDX-like license identifier string.

    Returns:
        LicenseInfo if the license type is known, None otherwise.
    """
    try:
        lt = LicenseType(license_type)
    except ValueError:
        return None
    return LICENSE_METADATA.get(lt)


def is_valid_license_type(license_type: str) -> bool:
    """Check whether a string is a recognised license type.

    Args:
        license_type: SPDX-like license identifier string to validate.

    Returns:
        True if the license type is in the catalog.
    """
    try:
        LicenseType(license_type)
        return True
    except ValueError:
        return False


def allows_remix(license_type: str, custom_allows_remix: bool = False) -> bool:
    """Determine whether a license permits derivative/remix works.

    For CUSTOM licenses the behaviour depends on the per-design
    ``custom_allows_remix`` flag stored on the design model.

    Args:
        license_type: SPDX-like license identifier string.
        custom_allows_remix: Override for CUSTOM license type.

    Returns:
        True if the license allows remixing; False if unknown or disallowed.
    """
    if license_type == LicenseType.CUSTOM:
        return custom_allows_remix

    info = get_license_metadata(license_type)
    if info is None:
        return False
    return info.allows_remix


def get_share_alike_compatible_licenses(license_type: str) -> list[str]:
    """Return the set of license types a remix may use given a parent license.

    Share-alike licenses require that derivatives keep the **same** license.
    Non-share-alike licenses allow derivatives to choose any license.

    Args:
        license_type: The parent design's license identifier.

    Returns:
        A list of valid license type strings for the derivative work.
        Returns an empty list if the license type is unknown.
    """
    info = get_license_metadata(license_type)
    if info is None:
        return []

    if info.requires_share_alike:
        # Share-alike: derivative MUST use the same license
        return [license_type]

    # Non-share-alike: any license is acceptable
    return [lt.value for lt in LicenseType]
