"""
IP Abuse Detection Service

Tracks suspicious behavior patterns and manages IP-based bans.
Integrates with content moderation to detect repeat offenders.
"""

import hashlib
import ipaddress
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.usage_limits import AbuseReport
from app.models.rating import UserBan

# =============================================================================
# Configuration
# =============================================================================


class ViolationType(StrEnum):
    """Types of violations that can trigger abuse detection."""

    WEAPON_CONTENT = "weapon_content"
    ILLEGAL_CONTENT = "illegal_content"
    RATE_LIMIT_ABUSE = "rate_limit_abuse"
    PROMPT_INJECTION = "prompt_injection"
    ACCOUNT_ABUSE = "account_abuse"
    SPAM = "spam"
    EVASION_ATTEMPT = "evasion_attempt"
    TOS_VIOLATION = "tos_violation"
    OFF_TOPIC_ABUSE = "off_topic_abuse"  # Repeated off-topic requests
    API_PROXY_ABUSE = "api_proxy_abuse"  # Using service as AI proxy


class BanDuration(StrEnum):
    """Standard ban durations."""

    WARNING = "warning"  # Just a warning, no ban
    HOUR_1 = "1_hour"
    HOUR_24 = "24_hours"
    DAYS_7 = "7_days"
    DAYS_30 = "30_days"
    PERMANENT = "permanent"


# Violation severity and escalation rules
VIOLATION_SEVERITY = {
    # Critical - immediate permanent ban
    ViolationType.WEAPON_CONTENT: {
        "base_severity": "critical",
        "first_offense": BanDuration.PERMANENT,  # Zero tolerance
        "escalation": BanDuration.PERMANENT,
    },
    ViolationType.ILLEGAL_CONTENT: {
        "base_severity": "critical",
        "first_offense": BanDuration.PERMANENT,
        "escalation": BanDuration.PERMANENT,
    },
    # High - escalating bans
    ViolationType.PROMPT_INJECTION: {
        "base_severity": "high",
        "first_offense": BanDuration.HOUR_24,
        "escalation": BanDuration.DAYS_7,
    },
    ViolationType.EVASION_ATTEMPT: {
        "base_severity": "high",
        "first_offense": BanDuration.DAYS_7,
        "escalation": BanDuration.PERMANENT,
    },
    ViolationType.API_PROXY_ABUSE: {
        "base_severity": "high",
        "first_offense": BanDuration.DAYS_7,  # Serious abuse of service
        "escalation": BanDuration.PERMANENT,
    },
    # Medium - warnings then bans
    ViolationType.RATE_LIMIT_ABUSE: {
        "base_severity": "medium",
        "first_offense": BanDuration.WARNING,
        "second_offense": BanDuration.HOUR_1,
        "third_offense": BanDuration.HOUR_24,
        "escalation": BanDuration.DAYS_7,
    },
    ViolationType.ACCOUNT_ABUSE: {
        "base_severity": "medium",
        "first_offense": BanDuration.HOUR_24,
        "escalation": BanDuration.DAYS_30,
    },
    ViolationType.OFF_TOPIC_ABUSE: {
        "base_severity": "medium",
        "first_offense": BanDuration.WARNING,
        "second_offense": BanDuration.WARNING,
        "third_offense": BanDuration.HOUR_1,  # Repeated misuse
        "escalation": BanDuration.HOUR_24,
    },
    # Low - multiple warnings before ban
    ViolationType.SPAM: {
        "base_severity": "low",
        "first_offense": BanDuration.WARNING,
        "second_offense": BanDuration.WARNING,
        "third_offense": BanDuration.HOUR_1,
        "escalation": BanDuration.HOUR_24,
    },
    ViolationType.TOS_VIOLATION: {
        "base_severity": "low",
        "first_offense": BanDuration.WARNING,
        "escalation": BanDuration.DAYS_7,
    },
}

# How long to remember violations for escalation
VIOLATION_MEMORY_DAYS = 90

# Suspicious pattern thresholds
SUSPICIOUS_PATTERNS = {
    "rapid_account_creation": {
        "threshold": 3,  # accounts from same IP
        "window_hours": 24,
    },
    "repeated_moderation_flags": {
        "threshold": 3,  # flags in window
        "window_hours": 1,
    },
    "rate_limit_violations": {
        "threshold": 10,  # 429 responses
        "window_hours": 1,
    },
    "failed_auth_attempts": {
        "threshold": 10,
        "window_minutes": 15,
    },
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ViolationEvent:
    """A single violation event."""

    id: UUID = field(default_factory=uuid4)
    violation_type: ViolationType = ViolationType.TOS_VIOLATION
    severity: str = "low"
    description: str = ""
    evidence: dict = field(default_factory=dict)
    user_id: UUID | None = None
    ip_address: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AbuseDecision:
    """Decision about how to handle a violation."""

    action: str  # "allow", "warn", "block", "ban"
    ban_duration: BanDuration | None = None
    reason: str = ""
    is_repeat_offender: bool = False
    previous_violations: int = 0
    should_notify_admin: bool = False


# =============================================================================
# Abuse Detection Service
# =============================================================================


class AbuseDetectionService:
    """
    Service for detecting and handling abuse.

    Tracks violations, applies escalating penalties,
    and manages IP/user bans.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._ip_cache: dict[str, list[datetime]] = defaultdict(list)

    # =========================================================================
    # Violation Handling
    # =========================================================================

    async def record_violation(
        self,
        violation: ViolationEvent,
        apply_ban: bool = True,
    ) -> AbuseDecision:
        """
        Record a violation and determine appropriate action.

        Args:
            violation: The violation event to record
            apply_ban: Whether to apply a ban (False = just log for monitoring)

        Returns decision on whether to warn, block, or ban.
        """
        # Get violation history
        history = await self._get_violation_history(
            user_id=violation.user_id,
            ip_address=violation.ip_address,
        )

        # Get escalation rules
        rules = VIOLATION_SEVERITY.get(
            violation.violation_type,
            VIOLATION_SEVERITY[ViolationType.TOS_VIOLATION],
        )

        # Determine action based on history
        previous_count = len(history)
        decision = self._determine_action(
            violation_type=violation.violation_type,
            previous_count=previous_count,
            rules=rules,
        )

        # Record the abuse report
        report = AbuseReport(
            user_id=violation.user_id,
            ip_address=violation.ip_address,
            trigger_type="content_moderation"
            if violation.violation_type
            in [ViolationType.WEAPON_CONTENT, ViolationType.ILLEGAL_CONTENT]
            else "suspicious_pattern",
            severity=violation.severity,
            description=violation.description,
            evidence=violation.evidence,
            prompt=violation.evidence.get("prompt"),
        )
        self.db.add(report)

        # Apply ban if needed (and if apply_ban is True)
        if apply_ban and decision.ban_duration and decision.ban_duration != BanDuration.WARNING:
            await self._apply_ban(
                user_id=violation.user_id,
                ip_address=violation.ip_address,
                duration=decision.ban_duration,
                reason=decision.reason,
                violation_history=[v.id for v in history],
            )

        await self.db.commit()

        return decision

    def _determine_action(
        self,
        violation_type: ViolationType,
        previous_count: int,
        rules: dict,
    ) -> AbuseDecision:
        """Determine appropriate action based on violation history."""

        # Critical violations = immediate permanent ban
        if rules["base_severity"] == "critical":
            return AbuseDecision(
                action="ban",
                ban_duration=BanDuration.PERMANENT,
                reason=f"Critical violation: {violation_type.value}",
                is_repeat_offender=previous_count > 0,
                previous_violations=previous_count,
                should_notify_admin=True,
            )

        # Determine ban duration based on offense count
        if previous_count == 0:
            duration = rules.get("first_offense", BanDuration.WARNING)
        elif previous_count == 1:
            duration = rules.get("second_offense", rules.get("escalation"))
        elif previous_count == 2:
            duration = rules.get("third_offense", rules.get("escalation"))
        else:
            duration = rules.get("escalation", BanDuration.PERMANENT)

        if duration == BanDuration.WARNING:
            return AbuseDecision(
                action="warn",
                ban_duration=None,
                reason=f"Warning for {violation_type.value}",
                is_repeat_offender=previous_count > 0,
                previous_violations=previous_count,
            )
        if duration == BanDuration.PERMANENT:
            return AbuseDecision(
                action="ban",
                ban_duration=duration,
                reason=f"Permanent ban for repeated {violation_type.value}",
                is_repeat_offender=True,
                previous_violations=previous_count,
                should_notify_admin=True,
            )
        return AbuseDecision(
            action="ban",
            ban_duration=duration,
            reason=f"Temporary ban for {violation_type.value}",
            is_repeat_offender=previous_count > 0,
            previous_violations=previous_count,
            should_notify_admin=previous_count >= 2,
        )

    async def _get_violation_history(
        self,
        user_id: UUID | None,
        ip_address: str | None,
    ) -> list:
        """Get violation history for user/IP."""
        cutoff = datetime.utcnow() - timedelta(days=VIOLATION_MEMORY_DAYS)

        conditions = [AbuseReport.created_at > cutoff]

        if user_id and ip_address:
            conditions.append(
                or_(
                    AbuseReport.user_id == user_id,
                    AbuseReport.ip_address == ip_address,
                )
            )
        elif user_id:
            conditions.append(AbuseReport.user_id == user_id)
        elif ip_address:
            conditions.append(AbuseReport.ip_address == ip_address)
        else:
            return []

        query = select(AbuseReport).where(and_(*conditions))
        result = await self.db.execute(query)

        return list(result.scalars().all())

    async def _apply_ban(
        self,
        user_id: UUID | None,
        ip_address: str | None,
        duration: BanDuration,
        reason: str,
        violation_history: list,
    ) -> UserBan:
        """Apply a ban to user and/or IP."""

        # Calculate expiration
        if duration == BanDuration.PERMANENT:
            expires_at = None
            ban_type = "permanent"
        else:
            duration_map = {
                BanDuration.HOUR_1: timedelta(hours=1),
                BanDuration.HOUR_24: timedelta(hours=24),
                BanDuration.DAYS_7: timedelta(days=7),
                BanDuration.DAYS_30: timedelta(days=30),
            }
            expires_at = datetime.utcnow() + duration_map.get(duration, timedelta(hours=24))
            ban_type = "temporary"

        ban = UserBan(
            user_id=user_id,
            ip_address=ip_address,
            reason=reason,
            ban_type=ban_type,
            expires_at=expires_at,
            violation_count=len(violation_history) + 1,
            violation_history=violation_history,
        )

        self.db.add(ban)
        return ban

    # =========================================================================
    # Ban Checking
    # =========================================================================

    async def is_banned(
        self,
        user_id: UUID | None = None,
        ip_address: str | None = None,
    ) -> tuple[bool, UserBan | None]:
        """Check if user or IP is currently banned."""
        now = datetime.utcnow()

        conditions = [
            UserBan.is_active,
            or_(
                UserBan.expires_at.is_(None),  # Permanent
                UserBan.expires_at > now,  # Not expired
            ),
        ]

        if user_id and ip_address:
            conditions.append(
                or_(
                    UserBan.user_id == user_id,
                    UserBan.ip_address == ip_address,
                )
            )
        elif user_id:
            conditions.append(UserBan.user_id == user_id)
        elif ip_address:
            conditions.append(UserBan.ip_address == ip_address)
        else:
            return False, None

        query = select(UserBan).where(and_(*conditions)).limit(1)
        result = await self.db.execute(query)
        ban = result.scalar_one_or_none()

        return ban is not None, ban

    async def get_ban_info(
        self,
        user_id: UUID | None = None,
        ip_address: str | None = None,
    ) -> dict | None:
        """Get ban information if banned."""
        is_banned, ban = await self.is_banned(user_id, ip_address)

        if not is_banned or not ban:
            return None

        return {
            "is_banned": True,
            "reason": ban.reason,
            "ban_type": ban.ban_type,
            "expires_at": ban.expires_at.isoformat() if ban.expires_at else None,
            "violation_count": ban.violation_count,
        }

    # =========================================================================
    # Pattern Detection
    # =========================================================================

    async def check_suspicious_patterns(
        self,
        user_id: UUID | None,
        ip_address: str,
        event_type: str,
    ) -> ViolationEvent | None:
        """
        Check for suspicious behavior patterns.

        Returns a ViolationEvent if suspicious pattern detected.
        """
        # Track this event
        cache_key = f"{ip_address}:{event_type}"
        now = datetime.utcnow()

        # Add to cache and cleanup old entries
        self._ip_cache[cache_key].append(now)
        self._ip_cache[cache_key] = [
            t for t in self._ip_cache[cache_key] if now - t < timedelta(hours=24)
        ]

        # Check against thresholds
        pattern_config = SUSPICIOUS_PATTERNS.get(event_type)
        if not pattern_config:
            return None

        threshold = pattern_config["threshold"]
        window_hours = pattern_config.get("window_hours", 1)
        window_minutes = pattern_config.get("window_minutes", window_hours * 60)

        cutoff = now - timedelta(minutes=window_minutes)
        recent_count = len([t for t in self._ip_cache[cache_key] if t > cutoff])

        if recent_count >= threshold:
            return ViolationEvent(
                violation_type=ViolationType.RATE_LIMIT_ABUSE,
                severity="medium",
                description=f"Suspicious pattern detected: {event_type}",
                evidence={
                    "pattern": event_type,
                    "count": recent_count,
                    "threshold": threshold,
                    "window_minutes": window_minutes,
                },
                user_id=user_id,
                ip_address=ip_address,
            )

        return None

    # =========================================================================
    # Ban Management
    # =========================================================================

    async def lift_ban(
        self,
        ban_id: UUID,
        admin_id: UUID,
    ) -> bool:
        """Lift a ban manually."""
        query = select(UserBan).where(UserBan.id == ban_id)
        result = await self.db.execute(query)
        ban = result.scalar_one_or_none()

        if not ban:
            return False

        ban.is_active = False
        ban.lifted_at = datetime.utcnow()
        ban.lifted_by = admin_id

        await self.db.commit()
        return True

    async def get_active_bans(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[UserBan]:
        """Get list of active bans for admin review."""
        now = datetime.utcnow()

        query = (
            select(UserBan)
            .where(
                and_(
                    UserBan.is_active,
                    or_(
                        UserBan.expires_at.is_(None),
                        UserBan.expires_at > now,
                    ),
                )
            )
            .order_by(UserBan.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def cleanup_expired_bans(self) -> int:
        """Deactivate expired bans."""
        now = datetime.utcnow()

        stmt = (
            update(UserBan)
            .where(
                and_(
                    UserBan.is_active,
                    UserBan.expires_at.isnot(None),
                    UserBan.expires_at <= now,
                )
            )
            .values(is_active=False)
        )

        result = await self.db.execute(stmt)
        await self.db.commit()

        return result.rowcount


# =============================================================================
# IP Utilities
# =============================================================================


def normalize_ip(ip: str) -> str:
    """Normalize an IP address."""
    try:
        return str(ipaddress.ip_address(ip))
    except ValueError:
        return ip


def get_ip_range(ip: str, prefix: int = 24) -> str:
    """Get IP range for blocking related IPs."""
    try:
        addr = ipaddress.ip_address(ip)
        if isinstance(addr, ipaddress.IPv4Address):
            network = ipaddress.ip_network(f"{ip}/{prefix}", strict=False)
            return str(network)
        # IPv6 - use larger prefix
        network = ipaddress.ip_network(f"{ip}/64", strict=False)
        return str(network)
    except ValueError:
        return ip


def hash_ip(ip: str) -> str:
    """Hash IP for privacy-preserving logging."""
    return hashlib.sha256(ip.encode()).hexdigest()[:16]
