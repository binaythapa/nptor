from datetime import timedelta
from decimal import Decimal
import secrets
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from vendors.models import VendorLedger, VendorPayout, VendorPayoutAllocation, VendorProfile


class SettlementService:
    @classmethod
    def get_settlement_holding_days(cls, vendor: Optional[VendorProfile] = None) -> int:
        """
        Returns the configurable holding period in calendar days.
        Configurable per vendor with fallback to settings.STORE_SETTLEMENT_HOLDING_DAYS
        (provisionally defaulting to 14 days, subject to commercial confirmation).
        """
        if vendor and getattr(vendor, "settlement_holding_days", None):
            return vendor.settlement_holding_days
        return getattr(settings, "STORE_SETTLEMENT_HOLDING_DAYS", 14)

    @classmethod
    def get_vendor_financial_summary(cls, vendor: VendorProfile) -> Dict[str, Any]:
        """
        Calculates an auditable breakdown of a vendor's ledger balances:
        - Lifetime sales, commissions, shipping, refunds, and RTO penalties
        - Current holding balance (in settlement period)
        - Current available balance (unlocked and ready for payout)
        - Disbursed balance (already settled and paid out)
        """
        now = timezone.now()
        entries = vendor.ledger_entries.all()

        def sum_type(entry_types):
            res = entries.filter(entry_type__in=entry_types).aggregate(total=Sum("amount"))["total"]
            return res or Decimal("0.00")

        gross_sales = sum_type([VendorLedger.ENTRY_CREDIT_ORDER_SALE, VendorLedger.ENTRY_CREDIT_COD_REMITTED])
        commissions = sum_type([VendorLedger.ENTRY_DEBIT_COMMISSION])
        shipping_fees = sum_type([VendorLedger.ENTRY_CREDIT_SHIPPING_COLLECTED, VendorLedger.ENTRY_DEBIT_COURIER_SHIPPING])
        refunds = sum_type([VendorLedger.ENTRY_DEBIT_REFUND, VendorLedger.ENTRY_CREDIT_COMMISSION_REVERSAL])
        rto_penalties = sum_type([VendorLedger.ENTRY_DEBIT_RTO_SHIPPING])
        payouts_disbursed = sum_type([VendorLedger.ENTRY_DEBIT_PAYOUT])

        # Active balances
        holding_entries = entries.filter(is_settled=False, unlocks_at__gt=now)
        holding_balance = holding_entries.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        available_entries = entries.filter(is_settled=False, unlocks_at__lte=now)
        available_balance = available_entries.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        return {
            "gross_sales": gross_sales,
            "commissions_deducted": abs(commissions),
            "shipping_net": shipping_fees,
            "refunds_net": refunds,
            "rto_penalties": abs(rto_penalties),
            "payouts_disbursed": abs(payouts_disbursed),
            "holding_balance": holding_balance,
            "available_balance": available_balance,
            "net_earned_balance": available_balance + holding_balance,
            "holding_period_days": cls.get_settlement_holding_days(vendor),
        }

    @classmethod
    def propose_payout_batch(cls, vendor: VendorProfile, actor=None) -> VendorPayout:
        """
        Proposes a new payout batch for all unlocked available balances.
        Prevents duplicate batches if a previous batch is in-flight.
        Explicitly binds eligible ledger entries to the payout via VendorPayoutAllocation.
        """
        now = timezone.now()

        with transaction.atomic():
            # Check and lock for existing in-flight payout
            active_payout = (
                VendorPayout.objects
                .select_for_update()
                .filter(
                    vendor=vendor,
                    status__in=[
                        VendorPayout.STATUS_PROPOSED,
                        VendorPayout.STATUS_APPROVED,
                        VendorPayout.STATUS_SUBMITTED,
                    ],
                )
                .first()
            )

            if active_payout:
                raise ValidationError(
                    f"An active payout batch ({active_payout.payout_reference}) is already in progress ({active_payout.get_status_display()})."
                )

            # Exclude entries that are already allocated to an active or confirmed payout
            active_or_confirmed_statuses = [
                VendorPayout.STATUS_PROPOSED,
                VendorPayout.STATUS_APPROVED,
                VendorPayout.STATUS_SUBMITTED,
                VendorPayout.STATUS_CONFIRMED,
            ]

            eligible_entries = list(
                vendor.ledger_entries
                .select_for_update()
                .filter(is_settled=False, unlocks_at__lte=now)
                .exclude(payout_allocations__payout__status__in=active_or_confirmed_statuses)
                .order_by("created_at")
            )

            if not eligible_entries:
                raise ValidationError("Vendor has no eligible unlocked balance available for payout.")

            total_available = sum(e.amount for e in eligible_entries)
            if total_available <= Decimal("0.00"):
                raise ValidationError(f"Available balance (NPR {total_available}) is not positive. Payout cannot be created.")

            # Calculate audit components
            gross = sum(e.amount for e in eligible_entries if e.amount > Decimal("0.00"))
            comm_deducted = abs(sum(e.amount for e in eligible_entries if e.entry_type == VendorLedger.ENTRY_DEBIT_COMMISSION))
            ship_deducted = abs(sum(e.amount for e in eligible_entries if e.entry_type == VendorLedger.ENTRY_DEBIT_COURIER_SHIPPING))
            rto_deducted = abs(sum(e.amount for e in eligible_entries if e.entry_type == VendorLedger.ENTRY_DEBIT_RTO_SHIPPING))

            ref = f"PO-{vendor.id}-{now.strftime('%Y%m%d%H%M')}-{secrets.token_hex(3).upper()}"

            payout = VendorPayout.objects.create(
                vendor=vendor,
                payout_reference=ref,
                gross_amount=gross,
                commission_deducted=comm_deducted,
                shipping_deducted=ship_deducted,
                rto_penalties_deducted=rto_deducted,
                net_disbursed=total_available,
                currency="NPR",
                status=VendorPayout.STATUS_PROPOSED,
            )

            # Explicitly bind eligible ledger entries to this payout batch
            allocations = [
                VendorPayoutAllocation(
                    payout=payout,
                    ledger_entry=entry,
                    allocated_amount=entry.amount,
                )
                for entry in eligible_entries
            ]
            VendorPayoutAllocation.objects.bulk_create(allocations)

            return payout

    @classmethod
    def approve_payout(cls, payout_id: int, actor=None) -> VendorPayout:
        """
        Staff approves a proposed payout batch for bank processing.
        """
        with transaction.atomic():
            payout = VendorPayout.objects.select_for_update().get(id=payout_id)
            if payout.status != VendorPayout.STATUS_PROPOSED:
                raise ValidationError(f"Cannot approve payout in status '{payout.get_status_display()}'.")

            payout.status = VendorPayout.STATUS_APPROVED
            payout.save(update_fields=["status"])
            return payout

    @classmethod
    def submit_payout_to_bank(cls, payout_id: int, bank_transaction_reference: str, actor=None) -> VendorPayout:
        """
        Staff marks payout as submitted to ConnectIPS/bank for manual disbursement.
        Does not mark as confirmed until settlement remittance clears.
        """
        if not bank_transaction_reference:
            raise ValidationError("Bank or ConnectIPS transaction reference is required.")

        with transaction.atomic():
            payout = VendorPayout.objects.select_for_update().get(id=payout_id)
            if payout.status != VendorPayout.STATUS_APPROVED:
                raise ValidationError(f"Cannot submit payout in status '{payout.get_status_display()}'. It must be approved first.")

            payout.status = VendorPayout.STATUS_SUBMITTED
            payout.bank_transaction_reference = bank_transaction_reference.strip()
            payout.save(update_fields=["status", "bank_transaction_reference"])
            return payout

    @classmethod
    def confirm_payout(cls, payout_id: int, actor=None) -> VendorPayout:
        """
        Staff confirms bank statement verification.
        Marks payout confirmed, marks ledger entries as settled, and posts a balancing
        payout debit entry to the vendor's ledger.
        Idempotent via unique idempotency key.
        Guarantees that ONLY entries explicitly allocated to this payout batch are settled,
        protecting against settlement of unallocated or backdated entries.
        """
        with transaction.atomic():
            payout = VendorPayout.objects.select_for_update().get(id=payout_id)

            if payout.status == VendorPayout.STATUS_CONFIRMED:
                return payout  # Idempotent return

            if payout.status not in [VendorPayout.STATUS_SUBMITTED, VendorPayout.STATUS_APPROVED]:
                raise ValidationError(f"Cannot confirm payout in status '{payout.get_status_display()}'.")

            # 1. Fetch allocated ledger entries explicitly linked to THIS payout
            allocations = (
                VendorPayoutAllocation.objects
                .select_for_update()
                .filter(payout=payout)
                .select_related("ledger_entry")
            )
            allocated_entry_ids = [alloc.ledger_entry_id for alloc in allocations]

            if not allocated_entry_ids:
                raise ValidationError(f"Payout {payout.payout_reference} has no allocated ledger entries.")

            # Verify none of them are already settled by some other payout
            already_settled = VendorLedger.objects.filter(
                id__in=allocated_entry_ids,
                is_settled=True,
            ).exists()
            if already_settled:
                raise ValidationError(
                    f"Integrity error: One or more ledger entries in payout {payout.payout_reference} have already been settled."
                )

            # Mark ONLY the explicitly allocated entries as settled
            # Any backdated entries created after payout proposal are NOT in allocated_entry_ids
            # and cannot be marked settled here!
            VendorLedger.objects.filter(id__in=allocated_entry_ids).update(is_settled=True)

            payout.status = VendorPayout.STATUS_CONFIRMED
            payout.disbursed_at = timezone.now()
            payout.disbursed_by = actor
            payout.save(update_fields=["status", "disbursed_at", "disbursed_by"])

            # 2. Post balancing debit entry to vendor ledger
            VendorLedger.objects.get_or_create(
                idempotency_key=f"payout-confirm-{payout.payout_reference}",
                defaults={
                    "vendor": payout.vendor,
                    "entry_type": VendorLedger.ENTRY_DEBIT_PAYOUT,
                    "amount": -payout.net_disbursed,
                    "currency": payout.currency,
                    "is_settled": True,
                    "reference_id": payout.payout_reference,
                    "notes": f"Payout disbursed via bank ref: {payout.bank_transaction_reference}",
                },
            )

            return payout

    @classmethod
    def reject_payout(cls, payout_id: int, reason: str = "", actor=None) -> VendorPayout:
        """
        Marks payout as failed/rejected (e.g. invalid bank details or failed transfer).
        Entries remain unsettled so funds stay in vendor's available balance.
        """
        with transaction.atomic():
            payout = VendorPayout.objects.select_for_update().get(id=payout_id)

            if payout.status == VendorPayout.STATUS_CONFIRMED:
                raise ValidationError("Cannot reject an already confirmed and disbursed payout.")

            payout.status = VendorPayout.STATUS_FAILED
            payout.save(update_fields=["status"])
            return payout
