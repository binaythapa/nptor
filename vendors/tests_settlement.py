from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from vendors.models import VendorLedger, VendorPayout, VendorProfile
from vendors.services.settlement_service import SettlementService

User = get_user_model()


class SettlementServiceTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_superuser(username="store_admin", email="admin@test.com", password="pass")
        self.vendor_user = User.objects.create_user(username="seller1", email="seller1@test.com", password="pass")
        self.regular_user = User.objects.create_user(username="customer_user", email="cust@test.com", password="pass")

        self.vendor = VendorProfile.objects.create(
            user=self.vendor_user,
            store_name="Himalayan Gadgets",
            slug="himalayan-gadgets",
            commission_rate=Decimal("10.00"),
            settlement_holding_days=14,
            status=VendorProfile.STATUS_ACTIVE,
        )

    def _seed_sample_ledger_entries(self):
        now = timezone.now()
        past = now - timedelta(days=20)
        future = now + timedelta(days=5)

        # 1. Unlocked sale (past hold)
        VendorLedger.objects.create(
            vendor=self.vendor,
            entry_type=VendorLedger.ENTRY_CREDIT_ORDER_SALE,
            amount=Decimal("5000.00"),
            unlocks_at=past,
            is_settled=False,
            reference_id="ORD-01",
            idempotency_key="seed-sale-01",
        )
        # Unlocked commission
        VendorLedger.objects.create(
            vendor=self.vendor,
            entry_type=VendorLedger.ENTRY_DEBIT_COMMISSION,
            amount=Decimal("-500.00"),
            unlocks_at=past,
            is_settled=False,
            reference_id="ORD-01",
            idempotency_key="seed-comm-01",
        )

        # 2. Locked sale (still in hold window)
        VendorLedger.objects.create(
            vendor=self.vendor,
            entry_type=VendorLedger.ENTRY_CREDIT_ORDER_SALE,
            amount=Decimal("3000.00"),
            unlocks_at=future,
            is_settled=False,
            reference_id="ORD-02",
            idempotency_key="seed-sale-02",
        )
        # Locked commission
        VendorLedger.objects.create(
            vendor=self.vendor,
            entry_type=VendorLedger.ENTRY_DEBIT_COMMISSION,
            amount=Decimal("-300.00"),
            unlocks_at=future,
            is_settled=False,
            reference_id="ORD-02",
            idempotency_key="seed-comm-02",
        )

    def test_financial_summary_holding_vs_available(self):
        self._seed_sample_ledger_entries()
        summary = SettlementService.get_vendor_financial_summary(self.vendor)

        self.assertEqual(summary["gross_sales"], Decimal("8000.00"))
        self.assertEqual(summary["commissions_deducted"], Decimal("800.00"))
        # Unlocked: 5000 - 500 = 4500.00
        self.assertEqual(summary["available_balance"], Decimal("4500.00"))
        # Holding: 3000 - 300 = 2700.00
        self.assertEqual(summary["holding_balance"], Decimal("2700.00"))
        self.assertEqual(summary["holding_period_days"], 14)

    def test_payout_batch_lifecycle_and_balanced_ledger(self):
        self._seed_sample_ledger_entries()

        # 1. Propose payout batch for unlocked balance
        payout = SettlementService.propose_payout_batch(self.vendor, actor=self.staff_user)
        self.assertEqual(payout.status, VendorPayout.STATUS_PROPOSED)
        self.assertEqual(payout.net_disbursed, Decimal("4500.00"))
        self.assertEqual(payout.gross_amount, Decimal("5000.00"))
        self.assertEqual(payout.commission_deducted, Decimal("500.00"))

        # 2. Prevent duplicate payout proposals
        with self.assertRaises(ValidationError):
            SettlementService.propose_payout_batch(self.vendor, actor=self.staff_user)

        # 3. Staff approves payout
        payout = SettlementService.approve_payout(payout.id, actor=self.staff_user)
        self.assertEqual(payout.status, VendorPayout.STATUS_APPROVED)

        # 4. Staff submits payout to bank
        payout = SettlementService.submit_payout_to_bank(
            payout.id,
            bank_transaction_reference="CONNECTIPS-TXN-12345",
            actor=self.staff_user,
        )
        self.assertEqual(payout.status, VendorPayout.STATUS_SUBMITTED)
        self.assertEqual(payout.bank_transaction_reference, "CONNECTIPS-TXN-12345")

        # 5. Staff confirms bank receipt
        confirmed_payout = SettlementService.confirm_payout(payout.id, actor=self.staff_user)
        self.assertEqual(confirmed_payout.status, VendorPayout.STATUS_CONFIRMED)

        # 6. Verify ledger entries are settled and balanced debit entry was posted
        unlocked_entries = self.vendor.ledger_entries.filter(reference_id="ORD-01")
        for entry in unlocked_entries:
            self.assertTrue(entry.is_settled)

        payout_ledger_entry = VendorLedger.objects.filter(
            vendor=self.vendor,
            entry_type=VendorLedger.ENTRY_DEBIT_PAYOUT,
        ).first()
        self.assertIsNotNone(payout_ledger_entry)
        self.assertEqual(payout_ledger_entry.amount, Decimal("-4500.00"))
        self.assertTrue(payout_ledger_entry.is_settled)

        # Available balance is now 0; holding balance remains 2700.00
        summary_after = SettlementService.get_vendor_financial_summary(self.vendor)
        self.assertEqual(summary_after["available_balance"], Decimal("0.00"))
        self.assertEqual(summary_after["holding_balance"], Decimal("2700.00"))

        # 7. Idempotency test: confirming again causes no duplicate debit entries
        SettlementService.confirm_payout(payout.id, actor=self.staff_user)
        self.assertEqual(VendorLedger.objects.filter(entry_type=VendorLedger.ENTRY_DEBIT_PAYOUT).count(), 1)

    def test_payout_rejection_restores_balance(self):
        self._seed_sample_ledger_entries()
        payout = SettlementService.propose_payout_batch(self.vendor, actor=self.staff_user)

        # Reject payout
        rejected = SettlementService.reject_payout(payout.id, reason="Account closed", actor=self.staff_user)
        self.assertEqual(rejected.status, VendorPayout.STATUS_FAILED)

        # Funds remain available
        summary = SettlementService.get_vendor_financial_summary(self.vendor)
        self.assertEqual(summary["available_balance"], Decimal("4500.00"))

    def test_backdated_entries_not_settled_by_prior_payout(self):
        """
        Guarantees that backdated entries inserted after a payout was proposed
        are NEVER settled when that payout is confirmed.
        """
        self._seed_sample_ledger_entries()
        payout = SettlementService.propose_payout_batch(self.vendor, actor=self.staff_user)
        SettlementService.approve_payout(payout.id, actor=self.staff_user)
        SettlementService.submit_payout_to_bank(payout.id, bank_transaction_reference="REF-BANK-999", actor=self.staff_user)

        # Insert a backdated ledger entry (unlocks_at is in the past)
        backdated_entry = VendorLedger.objects.create(
            vendor=self.vendor,
            entry_type=VendorLedger.ENTRY_CREDIT_ORDER_SALE,
            amount=Decimal("1500.00"),
            unlocks_at=timezone.now() - timedelta(days=30),
            is_settled=False,
            reference_id="ORD-BACKDATED",
            idempotency_key="seed-backdated-01",
        )

        # Confirm the payout
        SettlementService.confirm_payout(payout.id, actor=self.staff_user)

        # Verify: original allocated entries are settled
        ord01_entries = self.vendor.ledger_entries.filter(reference_id="ORD-01")
        for e in ord01_entries:
            self.assertTrue(e.is_settled)

        # Verify: backdated entry was NOT settled
        backdated_entry.refresh_from_db()
        self.assertFalse(backdated_entry.is_settled)

    def test_rejection_preserves_allocations_and_allows_reallocation(self):
        """
        When a payout is rejected, original allocation records are preserved for audit
        and entries become eligible for a subsequent payout proposal.
        """
        self._seed_sample_ledger_entries()
        payout1 = SettlementService.propose_payout_batch(self.vendor, actor=self.staff_user)
        self.assertEqual(payout1.allocations.count(), 2)

        # Reject payout 1
        SettlementService.reject_payout(payout1.id, reason="Incorrect IBAN", actor=self.staff_user)
        payout1.refresh_from_db()
        self.assertEqual(payout1.status, VendorPayout.STATUS_FAILED)
        self.assertEqual(payout1.allocations.count(), 2)  # Audit trail preserved

        # Propose payout 2
        payout2 = SettlementService.propose_payout_batch(self.vendor, actor=self.staff_user)
        self.assertEqual(payout2.status, VendorPayout.STATUS_PROPOSED)
        self.assertEqual(payout2.allocations.count(), 2)
        self.assertEqual(payout2.net_disbursed, Decimal("4500.00"))

    def test_admin_settlement_views_authorization(self):
        # Regular non-staff user receives 302 redirect to admin login
        self.client.force_login(self.regular_user)
        resp = self.client.get(reverse("vendors:admin_settlement_dashboard"))
        self.assertEqual(resp.status_code, 302)

        # Staff user can access dashboard and ledger views
        self.client.force_login(self.staff_user)
        resp_admin = self.client.get(reverse("vendors:admin_settlement_dashboard"))
        self.assertEqual(resp_admin.status_code, 200)

        resp_ledger = self.client.get(reverse("vendors:admin_vendor_ledger", kwargs={"vendor_id": self.vendor.id}))
        self.assertEqual(resp_ledger.status_code, 200)

        resp_queue = self.client.get(reverse("vendors:admin_payout_queue"))
        self.assertEqual(resp_queue.status_code, 200)
