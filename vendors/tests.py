from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from store.models import Category
from vendors.models import (
    VendorBankDetails,
    VendorCommission,
    VendorLedger,
    VendorPayout,
    VendorProfile,
)

User = get_user_model()


class VendorModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="seller1", email="seller1@example.com", password="pass")
        self.admin = User.objects.create_superuser(username="admin1", email="admin1@example.com", password="pass")
        self.vendor = VendorProfile.objects.create(
            user=self.user,
            store_name="Kathmandu Books",
            slug="kathmandu-books",
            business_email="contact@kathmandubooks.com",
            business_phone="+977-9800000000",
            pan_vat_number="123456789",
        )

    def test_vendor_profile_provisional_defaults(self):
        self.assertEqual(self.vendor.commission_rate, Decimal("10.00"))
        self.assertEqual(self.vendor.settlement_holding_days, 7)
        self.assertEqual(self.vendor.rto_fee_liability, VendorProfile.RTO_VENDOR_ABSORBS)
        self.assertEqual(self.vendor.status, VendorProfile.STATUS_PENDING)
        self.assertTrue(self.vendor.is_cod_enabled)

    def test_vendor_store_name_and_slug_are_unique(self):
        user2 = User.objects.create_user(username="seller2", email="seller2@example.com", password="pass")
        with self.assertRaises(IntegrityError):
            VendorProfile.objects.create(
                user=user2,
                store_name="Kathmandu Books",
                slug="kathmandu-books-2",
                business_email="other@example.com",
                business_phone="+977-9811111111",
            )

    def test_vendor_bank_details(self):
        bank = VendorBankDetails.objects.create(
            vendor=self.vendor,
            bank_name="Nabil Bank Ltd",
            bank_account_name="Kathmandu Books Pvt Ltd",
            bank_account_number="01234567890123",
            bank_branch="Tinkune",
        )
        self.assertEqual(self.vendor.bank_details, bank)
        self.assertEqual(bank.bank_account_number, "01234567890123")
        # Verify encryption at rest in database column
        self.assertNotEqual(bank.encrypted_account_number, "01234567890123")
        self.assertTrue(bank.masked_account_number.endswith("0123"))

    def test_vendor_commission_override_per_category(self):
        category = Category.objects.create(name="Engineering Books", slug="engineering-books")
        commission = VendorCommission.objects.create(
            vendor=self.vendor,
            category=category,
            rate=Decimal("8.50"),
        )
        self.assertEqual(commission.rate, Decimal("8.50"))
        # Uniqueness per vendor and category
        with self.assertRaises(IntegrityError):
            VendorCommission.objects.create(
                vendor=self.vendor,
                category=category,
                rate=Decimal("12.00"),
            )

    def test_vendor_ledger_uniqueness_constraint(self):
        entry1 = VendorLedger.objects.create(
            vendor=self.vendor,
            entry_type=VendorLedger.ENTRY_CREDIT_ORDER_SALE,
            amount=Decimal("1500.00"),
            reference_id="EVT-001",
        )
        self.assertIsNotNone(entry1.pk)

        # Duplicate event with same vendor, entry_type and reference_id must fail DB constraint
        with self.assertRaises(IntegrityError):
            VendorLedger.objects.create(
                vendor=self.vendor,
                entry_type=VendorLedger.ENTRY_CREDIT_ORDER_SALE,
                amount=Decimal("1500.00"),
                reference_id="EVT-001",
            )

    def test_vendor_payout_lifecycle_stages(self):
        payout = VendorPayout.objects.create(
            vendor=self.vendor,
            payout_reference="PAYOUT-2026-0001",
            gross_amount=Decimal("10000.00"),
            commission_deducted=Decimal("1000.00"),
            shipping_deducted=Decimal("500.00"),
            net_disbursed=Decimal("8500.00"),
            status=VendorPayout.STATUS_PROPOSED,
        )
        self.assertEqual(payout.status, VendorPayout.STATUS_PROPOSED)
        payout.status = VendorPayout.STATUS_APPROVED
        payout.save()
        payout.status = VendorPayout.STATUS_SUBMITTED
        payout.save()
        payout.status = VendorPayout.STATUS_CONFIRMED
        payout.disbursed_by = self.admin
        payout.save()
        self.assertEqual(payout.status, VendorPayout.STATUS_CONFIRMED)
