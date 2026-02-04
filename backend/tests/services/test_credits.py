"""
Tests for Credit Service.

Tests credit balance operations, transactions, deductions,
and quota enforcement.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from app.services.credits import (
    CreditService,
    InsufficientCreditsError,
    QuotaExceededError,
)
from app.models.subscription import (
    CreditBalance,
    CreditTransaction,
    TransactionType,
    SubscriptionTier,
    TierSlug,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def credit_service(db_session):
    """Create credit service with database session."""
    return CreditService(db_session)


# =============================================================================
# Balance Operations Tests
# =============================================================================

class TestBalanceOperations:
    """Tests for credit balance operations."""

    @pytest.mark.asyncio
    async def test_get_balance_creates_if_missing(
        self,
        credit_service: CreditService,
        db_session,
        test_user,
    ):
        """Test that get_balance creates new balance if none exists."""
        balance = await credit_service.get_balance(test_user.id)

        assert balance is not None
        assert balance.user_id == test_user.id
        assert balance.balance == 0
        assert balance.lifetime_earned == 0
        assert balance.lifetime_spent == 0

    @pytest.mark.asyncio
    async def test_get_balance_returns_existing(
        self,
        credit_service: CreditService,
        db_session,
        test_user,
    ):
        """Test that get_balance returns existing balance."""
        # Create existing balance
        existing = CreditBalance(
            user_id=test_user.id,
            balance=500,
            lifetime_earned=1000,
            lifetime_spent=500,
        )
        db_session.add(existing)
        await db_session.commit()

        balance = await credit_service.get_balance(test_user.id)

        assert balance.balance == 500
        assert balance.lifetime_earned == 1000
        assert balance.lifetime_spent == 500

    @pytest.mark.asyncio
    async def test_get_balance_amount(
        self,
        credit_service: CreditService,
        db_session,
        test_user,
    ):
        """Test getting just the balance amount."""
        balance = CreditBalance(
            user_id=test_user.id,
            balance=250,
            lifetime_earned=500,
            lifetime_spent=250,
        )
        db_session.add(balance)
        await db_session.commit()

        amount = await credit_service.get_balance_amount(test_user.id)

        assert amount == 250


# =============================================================================
# Can Afford Tests
# =============================================================================

class TestCanAfford:
    """Tests for affordability checks."""

    @pytest.mark.asyncio
    async def test_can_afford_with_sufficient_balance(
        self,
        credit_service: CreditService,
        db_session,
        test_user,
    ):
        """Test user can afford operation with sufficient balance."""
        balance = CreditBalance(
            user_id=test_user.id,
            balance=100,
            lifetime_earned=100,
            lifetime_spent=0,
        )
        db_session.add(balance)
        await db_session.commit()

        can_afford, cost, current = await credit_service.can_afford(
            test_user.id,
            TransactionType.GENERATION,
        )

        assert can_afford is True
        assert cost > 0  # Cost is defined in the model
        assert current == 100

    @pytest.mark.asyncio
    async def test_can_afford_with_insufficient_balance(
        self,
        credit_service: CreditService,
        db_session,
        test_user,
    ):
        """Test user cannot afford operation with low balance."""
        balance = CreditBalance(
            user_id=test_user.id,
            balance=0,
            lifetime_earned=0,
            lifetime_spent=0,
        )
        db_session.add(balance)
        await db_session.commit()

        can_afford, cost, current = await credit_service.can_afford(
            test_user.id,
            TransactionType.GENERATION,
        )

        assert can_afford is False
        assert current == 0


# =============================================================================
# Check and Deduct Tests
# =============================================================================

class TestCheckAndDeduct:
    """Tests for credit deduction operations."""

    @pytest.mark.asyncio
    async def test_check_and_deduct_success(
        self,
        credit_service: CreditService,
        db_session,
        test_user,
    ):
        """Test successful credit deduction."""
        balance = CreditBalance(
            user_id=test_user.id,
            balance=100,
            lifetime_earned=100,
            lifetime_spent=0,
        )
        db_session.add(balance)
        await db_session.commit()

        transaction = await credit_service.check_and_deduct(
            user_id=test_user.id,
            operation=TransactionType.GENERATION,
            reference_type="job",
            reference_id=uuid4(),
            description="Test generation",
        )

        # Transaction should be created
        assert transaction is not None
        assert transaction.amount < 0  # Deduction is negative
        assert transaction.user_id == test_user.id

        # Balance should be reduced
        await db_session.refresh(balance)
        assert balance.balance < 100
        assert balance.lifetime_spent > 0

    @pytest.mark.asyncio
    async def test_check_and_deduct_insufficient_credits(
        self,
        credit_service: CreditService,
        db_session,
        test_user,
    ):
        """Test deduction fails with insufficient credits."""
        balance = CreditBalance(
            user_id=test_user.id,
            balance=0,
            lifetime_earned=0,
            lifetime_spent=0,
        )
        db_session.add(balance)
        await db_session.commit()

        with pytest.raises(InsufficientCreditsError) as exc:
            await credit_service.check_and_deduct(
                user_id=test_user.id,
                operation=TransactionType.GENERATION,
            )

        assert exc.value.available == 0
        assert exc.value.required > 0

    @pytest.mark.asyncio
    async def test_check_and_deduct_records_transaction(
        self,
        credit_service: CreditService,
        db_session,
        test_user,
    ):
        """Test that deduction creates transaction record."""
        balance = CreditBalance(
            user_id=test_user.id,
            balance=100,
            lifetime_earned=100,
            lifetime_spent=0,
        )
        db_session.add(balance)
        await db_session.commit()

        ref_id = uuid4()
        transaction = await credit_service.check_and_deduct(
            user_id=test_user.id,
            operation=TransactionType.GENERATION,
            reference_type="design",
            reference_id=ref_id,
        )

        assert transaction.reference_type == "design"
        assert transaction.reference_id == ref_id
        assert transaction.balance_before == 100
        assert transaction.balance_after < 100


# =============================================================================
# Add Credits Tests
# =============================================================================

class TestAddCredits:
    """Tests for adding credits."""

    @pytest.mark.asyncio
    async def test_add_credits_success(
        self,
        credit_service: CreditService,
        db_session,
        test_user,
    ):
        """Test successfully adding credits."""
        balance = CreditBalance(
            user_id=test_user.id,
            balance=50,
            lifetime_earned=50,
            lifetime_spent=0,
        )
        db_session.add(balance)
        await db_session.commit()

        transaction = await credit_service.add_credits(
            user_id=test_user.id,
            amount=100,
            transaction_type=TransactionType.MONTHLY_REFILL,
            description="Monthly refill",
        )

        # Transaction should be recorded
        assert transaction.amount == 100
        assert transaction.balance_before == 50
        assert transaction.balance_after == 150

        # Balance should be updated
        await db_session.refresh(balance)
        assert balance.balance == 150
        assert balance.lifetime_earned == 150

    @pytest.mark.asyncio
    async def test_add_credits_negative_amount_error(
        self,
        credit_service: CreditService,
        db_session,
        test_user,
    ):
        """Test error when adding negative credits."""
        balance = CreditBalance(
            user_id=test_user.id,
            balance=100,
            lifetime_earned=100,
            lifetime_spent=0,
        )
        db_session.add(balance)
        await db_session.commit()

        with pytest.raises(ValueError) as exc:
            await credit_service.add_credits(
                user_id=test_user.id,
                amount=-50,
                transaction_type=TransactionType.MONTHLY_REFILL,
                description="Invalid",
            )

        assert "positive" in str(exc.value)

    @pytest.mark.asyncio
    async def test_add_credits_zero_amount_error(
        self,
        credit_service: CreditService,
        db_session,
        test_user,
    ):
        """Test error when adding zero credits."""
        balance = CreditBalance(
            user_id=test_user.id,
            balance=100,
            lifetime_earned=100,
            lifetime_spent=0,
        )
        db_session.add(balance)
        await db_session.commit()

        with pytest.raises(ValueError):
            await credit_service.add_credits(
                user_id=test_user.id,
                amount=0,
                transaction_type=TransactionType.MONTHLY_REFILL,
                description="Invalid",
            )

    @pytest.mark.asyncio
    async def test_add_credits_creates_balance_if_missing(
        self,
        credit_service: CreditService,
        db_session,
        test_user,
    ):
        """Test adding credits creates balance if not exists."""
        transaction = await credit_service.add_credits(
            user_id=test_user.id,
            amount=500,
            transaction_type=TransactionType.MONTHLY_REFILL,
            description="Initial credits",
        )

        assert transaction.balance_before == 0
        assert transaction.balance_after == 500


# =============================================================================
# Transaction History Tests
# =============================================================================

class TestTransactionHistory:
    """Tests for transaction tracking."""

    @pytest.mark.asyncio
    async def test_multiple_transactions_tracked(
        self,
        credit_service: CreditService,
        db_session,
        test_user,
    ):
        """Test that multiple transactions are properly tracked."""
        # Add initial credits
        await credit_service.add_credits(
            user_id=test_user.id,
            amount=100,
            transaction_type=TransactionType.MONTHLY_REFILL,
            description="Initial",
        )

        # Make some deductions
        await credit_service.check_and_deduct(
            user_id=test_user.id,
            operation=TransactionType.GENERATION,
        )

        # Add more credits
        await credit_service.add_credits(
            user_id=test_user.id,
            amount=50,
            transaction_type=TransactionType.BONUS,
            description="Bonus",
        )

        # Verify balance reflects all transactions
        balance = await credit_service.get_balance(test_user.id)
        assert balance.lifetime_earned == 150
        assert balance.lifetime_spent > 0


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_exact_balance_deduction(
        self,
        credit_service: CreditService,
        db_session,
        test_user,
    ):
        """Test deduction when balance exactly matches cost."""
        from app.models.subscription import get_operation_cost
        
        cost = get_operation_cost(TransactionType.GENERATION)
        
        balance = CreditBalance(
            user_id=test_user.id,
            balance=cost,  # Exactly enough
            lifetime_earned=cost,
            lifetime_spent=0,
        )
        db_session.add(balance)
        await db_session.commit()

        transaction = await credit_service.check_and_deduct(
            user_id=test_user.id,
            operation=TransactionType.GENERATION,
        )

        # Should succeed
        assert transaction is not None
        await db_session.refresh(balance)
        assert balance.balance == 0

    @pytest.mark.asyncio
    async def test_large_credit_addition(
        self,
        credit_service: CreditService,
        db_session,
        test_user,
    ):
        """Test adding large amount of credits."""
        transaction = await credit_service.add_credits(
            user_id=test_user.id,
            amount=1_000_000,
            transaction_type=TransactionType.PURCHASE,
            description="Enterprise credits",
        )

        assert transaction.balance_after == 1_000_000

        balance = await credit_service.get_balance(test_user.id)
        assert balance.balance == 1_000_000
