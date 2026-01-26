# ADR-012: Content Moderation Approach

## Status
Proposed

## Context
We need to prevent misuse of the platform for generating prohibited content. Key concerns:
- Weapon components (firearms, knives, etc.)
- Illegal items (lock picks, drug paraphernalia)
- Copyright/trademark infringement
- Explicit content
- Rate abuse and system exploitation

This is critical for:
- Legal compliance
- Platform reputation
- User safety
- Payment processor requirements

## Decision
We will implement a **multi-layer content moderation system** with:
1. **Input filtering**: Keyword blocklist + ML intent classification
2. **Output validation**: Geometric analysis for weapon-like shapes
3. **Human review queue**: For edge cases
4. **User reputation system**: Track violations per user

Technology choices:
- **Text moderation**: OpenAI Moderation API + custom classifier
- **Intent classification**: Fine-tuned model or GPT-4 with examples
- **Geometric analysis**: Custom heuristics + ML classifier
- **Review interface**: Internal admin dashboard

## Consequences

### Positive
- **Multi-layer protection**: Multiple checks reduce false negatives
- **Scalable**: Automated first, human review for edge cases
- **Adaptable**: ML models can be updated as threats evolve
- **Audit trail**: All moderation decisions logged

### Negative
- **False positives**: May block legitimate requests
- **Processing overhead**: Adds latency to generation
- **Ongoing maintenance**: Need to update blocklists and models
- **Human cost**: Review queue requires staffing

### Mitigation
- Tune thresholds to balance safety vs. usability
- Clear appeal process for false positives
- Start conservative, loosen as we learn

## Technical Details

### Moderation Flow
```
┌─────────────────────────────────────────────────────────────────────────┐
│                        USER INPUT                                        │
│   "Create a rectangular tube with pistol grip profile..."               │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    LAYER 1: KEYWORD FILTER                              │
│   Fast blocklist check for obvious prohibited terms                      │
│   Result: PASS / BLOCK                                                   │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ PASS
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    LAYER 2: OPENAI MODERATION                           │
│   Check against OpenAI's moderation categories                           │
│   Result: PASS / BLOCK                                                   │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ PASS
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    LAYER 3: INTENT CLASSIFICATION                       │
│   Custom ML/LLM classification for CAD-specific threats                  │
│   Categories: weapon, illegal_item, copyright, explicit, benign          │
│   Result: PASS / BLOCK / REVIEW                                         │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ PASS
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    CAD GENERATION                                        │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    LAYER 4: OUTPUT VALIDATION                           │
│   Geometric analysis of generated shape                                  │
│   - Weapon silhouette detection                                          │
│   - Prohibited shape matching                                            │
│   Result: PASS / BLOCK / REVIEW                                         │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
            ┌──────────────┐          ┌──────────────┐
            │    PASS      │          │    REVIEW    │
            │   Deliver    │          │   Hold for   │
            │   to user    │          │   human      │
            └──────────────┘          └──────────────┘
```

### Keyword Filter
```python
# app/services/moderation/keyword_filter.py
import re
from typing import NamedTuple

class FilterResult(NamedTuple):
    blocked: bool
    matched_terms: list[str]
    category: str | None

# Compiled regex patterns for performance
BLOCKLIST_PATTERNS = {
    "weapons": re.compile(
        r'\b(gun|pistol|rifle|firearm|weapon|trigger\s*guard|'
        r'barrel|receiver|suppressor|silencer|magazine|'
        r'bump\s*stock|auto\s*sear|ar-?15|glock|'
        r'knife|blade|sword|dagger|switchblade)\b',
        re.IGNORECASE
    ),
    "illegal": re.compile(
        r'\b(lock\s*pick|bump\s*key|slim\s*jim|'
        r'credit\s*card\s*skimmer|atm\s*skimmer|'
        r'pipe\s*bomb|explosive)\b',
        re.IGNORECASE
    ),
    "drug_paraphernalia": re.compile(
        r'\b(pipe|bong|bowl|grinder|rolling)\b.*\b(weed|marijuana|cannabis|drug)\b',
        re.IGNORECASE
    ),
}

def keyword_filter(text: str) -> FilterResult:
    """Fast keyword-based filtering."""
    for category, pattern in BLOCKLIST_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            return FilterResult(
                blocked=True,
                matched_terms=matches,
                category=category
            )
    return FilterResult(blocked=False, matched_terms=[], category=None)
```

### Intent Classification
```python
# app/services/moderation/intent_classifier.py
from openai import AsyncOpenAI
from pydantic import BaseModel
from enum import Enum

class IntentCategory(str, Enum):
    BENIGN = "benign"
    WEAPON = "weapon"
    WEAPON_COMPONENT = "weapon_component"
    ILLEGAL_ITEM = "illegal_item"
    COPYRIGHT = "copyright"
    EXPLICIT = "explicit"
    UNCERTAIN = "uncertain"

class IntentResult(BaseModel):
    category: IntentCategory
    confidence: float
    reasoning: str
    
INTENT_PROMPT = """You are a content moderation system for a 3D part design platform.
Analyze the following design request and classify its intent.

Categories:
- benign: Normal, legitimate design request (tools, enclosures, brackets, etc.)
- weapon: Firearms, knives, or other weapons
- weapon_component: Parts that could be used to make weapons (trigger guards, barrel blanks, etc.)
- illegal_item: Lock picks, skimmers, drug paraphernalia, etc.
- copyright: Trademarked logos, copyrighted characters
- explicit: Adult content
- uncertain: Cannot determine, needs human review

Design request: "{description}"

Respond with JSON:
{{"category": "...", "confidence": 0.0-1.0, "reasoning": "..."}}
"""

class IntentClassifier:
    def __init__(self):
        self.client = AsyncOpenAI()
    
    async def classify(self, description: str) -> IntentResult:
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",  # Fast and cheap for moderation
            messages=[
                {"role": "system", "content": "You are a content moderation classifier."},
                {"role": "user", "content": INTENT_PROMPT.format(description=description)}
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=200
        )
        
        result = json.loads(response.choices[0].message.content)
        return IntentResult(**result)
```

### Moderation Service
```python
# app/services/moderation/service.py
from dataclasses import dataclass
from enum import Enum

class ModerationAction(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    REVIEW = "review"

@dataclass
class ModerationResult:
    action: ModerationAction
    reason: str | None
    category: str | None
    confidence: float | None
    details: dict

class ModerationService:
    def __init__(self):
        self.keyword_filter = KeywordFilter()
        self.intent_classifier = IntentClassifier()
        self.openai_client = AsyncOpenAI()
    
    async def check_input(self, description: str, user: User) -> ModerationResult:
        """Run full moderation pipeline on input."""
        
        # Layer 1: Keyword filter (fast)
        keyword_result = self.keyword_filter.check(description)
        if keyword_result.blocked:
            await self._log_moderation(user, "keyword", keyword_result)
            return ModerationResult(
                action=ModerationAction.BLOCK,
                reason="prohibited_content",
                category=keyword_result.category,
                confidence=1.0,
                details={"matched_terms": keyword_result.matched_terms}
            )
        
        # Layer 2: OpenAI moderation API
        moderation = await self.openai_client.moderations.create(input=description)
        if moderation.results[0].flagged:
            categories = moderation.results[0].categories
            await self._log_moderation(user, "openai", moderation.results[0])
            return ModerationResult(
                action=ModerationAction.BLOCK,
                reason="content_policy",
                category=self._get_flagged_category(categories),
                confidence=1.0,
                details={"openai_categories": categories.model_dump()}
            )
        
        # Layer 3: Intent classification
        intent = await self.intent_classifier.classify(description)
        
        if intent.category in [IntentCategory.WEAPON, IntentCategory.ILLEGAL_ITEM]:
            if intent.confidence > 0.8:
                await self._log_moderation(user, "intent", intent)
                return ModerationResult(
                    action=ModerationAction.BLOCK,
                    reason=intent.category.value,
                    category=intent.category.value,
                    confidence=intent.confidence,
                    details={"reasoning": intent.reasoning}
                )
            elif intent.confidence > 0.5:
                await self._create_review_item(user, description, intent)
                return ModerationResult(
                    action=ModerationAction.REVIEW,
                    reason="manual_review_required",
                    category=intent.category.value,
                    confidence=intent.confidence,
                    details={"reasoning": intent.reasoning}
                )
        
        if intent.category == IntentCategory.UNCERTAIN:
            await self._create_review_item(user, description, intent)
            return ModerationResult(
                action=ModerationAction.REVIEW,
                reason="uncertain_intent",
                category=None,
                confidence=intent.confidence,
                details={"reasoning": intent.reasoning}
            )
        
        # Passed all checks
        return ModerationResult(
            action=ModerationAction.ALLOW,
            reason=None,
            category=None,
            confidence=None,
            details={}
        )
    
    async def check_output(self, geometry_metadata: dict, user: User) -> ModerationResult:
        """Check generated geometry for prohibited shapes."""
        # Implement geometric analysis here
        # - Silhouette matching against weapon shapes
        # - ML classifier on 3D geometry features
        pass
```

### User Reputation System
```python
# app/services/moderation/reputation.py
from datetime import datetime, timedelta

class UserReputation:
    """Track user moderation history."""
    
    async def record_violation(
        self, 
        user_id: str, 
        category: str, 
        severity: str
    ):
        """Record a moderation violation."""
        await db.execute(
            """
            INSERT INTO user_violations (user_id, category, severity, created_at)
            VALUES ($1, $2, $3, $4)
            """,
            user_id, category, severity, datetime.utcnow()
        )
        
        # Check if user should be suspended
        await self._check_suspension(user_id)
    
    async def _check_suspension(self, user_id: str):
        """Auto-suspend users with multiple violations."""
        recent_violations = await db.fetch(
            """
            SELECT COUNT(*) as count
            FROM user_violations
            WHERE user_id = $1 AND created_at > $2
            """,
            user_id, datetime.utcnow() - timedelta(days=30)
        )
        
        count = recent_violations[0]['count']
        
        if count >= 5:
            await self._suspend_user(user_id, reason="multiple_violations")
        elif count >= 3:
            await self._warn_user(user_id)
    
    async def get_risk_score(self, user_id: str) -> float:
        """Get user's risk score (0-1)."""
        violations = await db.fetch(
            """
            SELECT category, severity, created_at
            FROM user_violations
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT 20
            """,
            user_id
        )
        
        # Weight recent violations more heavily
        score = 0.0
        for v in violations:
            age_days = (datetime.utcnow() - v['created_at']).days
            weight = 1.0 / (1 + age_days / 30)  # Decay over 30 days
            severity_weight = {"low": 0.1, "medium": 0.3, "high": 0.5}
            score += weight * severity_weight.get(v['severity'], 0.2)
        
        return min(1.0, score)
```

### Admin Review Interface
```python
# app/api/v1/admin/moderation.py
from fastapi import APIRouter, Depends

router = APIRouter()

@router.get("/moderation/queue")
async def get_review_queue(
    status: str = "pending",
    current_admin: User = Depends(get_current_admin)
):
    """Get items pending human review."""
    items = await db.fetch(
        """
        SELECT r.*, u.email, u.display_name
        FROM moderation_reviews r
        JOIN users u ON r.user_id = u.id
        WHERE r.status = $1
        ORDER BY r.created_at ASC
        LIMIT 50
        """,
        status
    )
    return items

@router.post("/moderation/reviews/{review_id}/decision")
async def submit_decision(
    review_id: str,
    decision: ModerationDecision,
    current_admin: User = Depends(get_current_admin)
):
    """Submit moderation decision."""
    await db.execute(
        """
        UPDATE moderation_reviews
        SET status = $1, decision = $2, reviewer_id = $3, reviewed_at = $4
        WHERE id = $5
        """,
        "completed", decision.action, current_admin.id, datetime.utcnow(), review_id
    )
    
    if decision.action == "block":
        await reputation.record_violation(
            review.user_id,
            decision.category,
            decision.severity
        )
    
    return {"status": "success"}
```

### Metrics and Reporting
```python
# Track moderation metrics
MODERATION_CHECKS = Counter(
    'moderation_checks_total',
    'Total moderation checks',
    ['layer', 'result']  # layer: keyword/openai/intent, result: allow/block/review
)

MODERATION_LATENCY = Histogram(
    'moderation_latency_seconds',
    'Moderation check latency',
    ['layer']
)

REVIEW_QUEUE_SIZE = Gauge(
    'moderation_review_queue_size',
    'Number of items pending review'
)
```

## Response to Users
```python
# User-facing error messages
MODERATION_MESSAGES = {
    "prohibited_content": "This design request contains content that violates our terms of service.",
    "weapon": "We cannot generate weapons or weapon components.",
    "illegal_item": "This request appears to be for an item that may be illegal.",
    "copyright": "This request may involve copyrighted or trademarked material.",
    "manual_review_required": "Your request is being reviewed and you'll receive a response shortly.",
}
```

## References
- [OpenAI Moderation API](https://platform.openai.com/docs/guides/moderation)
- [Content Moderation Best Practices](https://www.cloudflare.com/learning/ai/content-moderation/)
- [Trust and Safety Guidelines](https://www.tspa.org/curriculum/)
