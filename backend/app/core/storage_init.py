"""
Storage initialization for MinIO/S3 buckets.

Configures bucket versioning, lifecycle policies, and ensures
all required buckets exist with proper settings. This module is
designed to be called from a CLI script, K8s init job, or application
startup to guarantee storage infrastructure is correctly configured.

All operations are idempotent and safe to run multiple times.
"""

import logging
from typing import Any

import aioboto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.storage import StorageBucket

logger = logging.getLogger(__name__)

# Buckets that should have versioning enabled (critical data)
VERSIONED_BUCKETS: list[StorageBucket] = [
    StorageBucket.DESIGNS,
    StorageBucket.UPLOADS,
    StorageBucket.EXPORTS,
]

# Buckets that should NOT have versioning (temporary/ephemeral data)
TEMP_BUCKETS: list[StorageBucket] = [StorageBucket.TEMP]

# Days before temp objects expire
TEMP_EXPIRY_DAYS: int = 7

# Days before designs transition to cold storage
DESIGNS_TRANSITION_DAYS: int = 180

BUCKET_PREFIX: str = f"ai-part-designer-{settings.ENVIRONMENT}"


def _get_bucket_name(bucket: StorageBucket) -> str:
    """Get full bucket name with environment prefix.

    Args:
        bucket: The storage bucket enum value.

    Returns:
        Full bucket name string with environment prefix.
    """
    return f"{BUCKET_PREFIX}-{bucket.value}"


async def initialize_storage() -> dict[str, Any]:
    """Initialize storage buckets with versioning and lifecycle policies.

    This function is idempotent and safe to run multiple times.
    It performs the following steps:
    1. Ensures all required buckets exist
    2. Enables versioning on critical buckets (DESIGNS, UPLOADS, EXPORTS)
    3. Configures lifecycle policies:
       - TEMP bucket: expire objects after 7 days
       - DESIGNS bucket: transition to GLACIER after 180 days

    Returns:
        Summary dict with created/configured bucket details including
        lists of created buckets, versioned buckets, and lifecycle configs.
    """
    session = aioboto3.Session()
    config = {
        "endpoint_url": settings.storage_endpoint,
        "aws_access_key_id": settings.storage_access_key,
        "aws_secret_access_key": settings.storage_secret_key,
        "region_name": settings.storage_region,
    }

    summary: dict[str, Any] = {
        "buckets_created": [],
        "buckets_existed": [],
        "versioning_enabled": [],
        "lifecycle_configured": [],
        "errors": [],
    }

    logger.info("Starting storage initialization")

    async with session.client("s3", **config) as client:
        # Step 1: Ensure all buckets exist
        for bucket in StorageBucket:
            bucket_name = _get_bucket_name(bucket)
            try:
                created = await _ensure_bucket_exists(client, bucket_name)
                if created:
                    summary["buckets_created"].append(bucket_name)
                    logger.info("Created bucket: %s", bucket_name)
                else:
                    summary["buckets_existed"].append(bucket_name)
                    logger.debug("Bucket already exists: %s", bucket_name)
            except Exception as e:
                error_msg = f"Failed to ensure bucket {bucket_name}: {e}"
                summary["errors"].append(error_msg)
                logger.error(error_msg)

        # Step 2: Enable versioning on critical buckets
        for bucket in VERSIONED_BUCKETS:
            bucket_name = _get_bucket_name(bucket)
            try:
                await _enable_versioning(client, bucket_name)
                summary["versioning_enabled"].append(bucket_name)
                logger.info("Enabled versioning on bucket: %s", bucket_name)
            except Exception as e:
                error_msg = f"Failed to enable versioning on {bucket_name}: {e}"
                summary["errors"].append(error_msg)
                logger.error(error_msg)

        # Step 3: Configure lifecycle policies
        # TEMP bucket: expire after 7 days
        for bucket in TEMP_BUCKETS:
            bucket_name = _get_bucket_name(bucket)
            try:
                await _configure_temp_lifecycle(client, bucket_name)
                summary["lifecycle_configured"].append(
                    {"bucket": bucket_name, "policy": "expire_7_days"}
                )
                logger.info(
                    "Configured temp lifecycle on bucket: %s", bucket_name
                )
            except Exception as e:
                error_msg = (
                    f"Failed to configure temp lifecycle on {bucket_name}: {e}"
                )
                summary["errors"].append(error_msg)
                logger.error(error_msg)

        # DESIGNS bucket: transition to cold storage after 180 days
        designs_bucket_name = _get_bucket_name(StorageBucket.DESIGNS)
        try:
            await _configure_designs_lifecycle(client, designs_bucket_name)
            summary["lifecycle_configured"].append(
                {"bucket": designs_bucket_name, "policy": "glacier_180_days"}
            )
            logger.info(
                "Configured designs lifecycle on bucket: %s",
                designs_bucket_name,
            )
        except Exception as e:
            error_msg = (
                f"Failed to configure designs lifecycle on "
                f"{designs_bucket_name}: {e}"
            )
            summary["errors"].append(error_msg)
            logger.error(error_msg)

    logger.info(
        "Storage initialization complete. Created: %d, Existed: %d, Errors: %d",
        len(summary["buckets_created"]),
        len(summary["buckets_existed"]),
        len(summary["errors"]),
    )

    return summary


async def _ensure_bucket_exists(client: Any, bucket_name: str) -> bool:
    """Create bucket if it doesn't exist.

    Args:
        client: The boto3 S3 client.
        bucket_name: Full name of the bucket to create.

    Returns:
        True if the bucket was created, False if it already existed.

    Raises:
        ClientError: If bucket creation fails for reasons other than
            the bucket already existing.
    """
    try:
        await client.head_bucket(Bucket=bucket_name)
        return False
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code in ("404", "NoSuchBucket"):
            await client.create_bucket(Bucket=bucket_name)
            return True
        raise


async def _enable_versioning(client: Any, bucket_name: str) -> None:
    """Enable versioning on a bucket.

    This is idempotent — calling it on an already-versioned bucket
    has no effect.

    Args:
        client: The boto3 S3 client.
        bucket_name: Full name of the bucket.
    """
    await client.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={"Status": "Enabled"},
    )


async def _configure_temp_lifecycle(client: Any, bucket_name: str) -> None:
    """Configure temp bucket lifecycle: expire objects after 7 days.

    Sets a lifecycle rule that automatically deletes all objects
    in the bucket after TEMP_EXPIRY_DAYS days.

    Args:
        client: The boto3 S3 client.
        bucket_name: Full name of the temp bucket.
    """
    lifecycle_config: dict[str, Any] = {
        "Rules": [
            {
                "ID": "expire-temp-objects",
                "Status": "Enabled",
                "Filter": {"Prefix": ""},
                "Expiration": {"Days": TEMP_EXPIRY_DAYS},
            }
        ]
    }

    await client.put_bucket_lifecycle_configuration(
        Bucket=bucket_name,
        LifecycleConfiguration=lifecycle_config,
    )


async def _configure_designs_lifecycle(client: Any, bucket_name: str) -> None:
    """Configure designs bucket lifecycle: transition to cold storage after 180 days.

    Sets a lifecycle rule that transitions design objects to GLACIER
    storage class after DESIGNS_TRANSITION_DAYS days for cost optimization.

    Args:
        client: The boto3 S3 client.
        bucket_name: Full name of the designs bucket.
    """
    lifecycle_config: dict[str, Any] = {
        "Rules": [
            {
                "ID": "transition-designs-to-glacier",
                "Status": "Enabled",
                "Filter": {"Prefix": ""},
                "Transitions": [
                    {
                        "Days": DESIGNS_TRANSITION_DAYS,
                        "StorageClass": "GLACIER",
                    }
                ],
            }
        ]
    }

    await client.put_bucket_lifecycle_configuration(
        Bucket=bucket_name,
        LifecycleConfiguration=lifecycle_config,
    )
