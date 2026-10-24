import os
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.test import SimpleTestCase, TestCase
from django.contrib.auth import get_user_model

from vendors.crypto import (
    DecryptionError,
    KeyConfigurationError,
    encrypt_bank_account,
    decrypt_bank_account,
    rotate_bank_account_ciphertext,
)
from vendors.models import VendorProfile, VendorBankDetails

User = get_user_model()


class BankCryptoUnitTests(SimpleTestCase):
    def setUp(self):
        self.key_a = Fernet.generate_key().decode("ascii")
        self.key_b = Fernet.generate_key().decode("ascii")
        self.key_c = Fernet.generate_key().decode("ascii")

    def test_encryption_and_decryption_with_dedicated_key(self):
        with patch.dict(os.environ, {"BANK_DETAILS_ENCRYPTION_KEY": self.key_a}):
            raw_acc = "0123456789012345"
            ciphertext = encrypt_bank_account(raw_acc)
            self.assertNotEqual(ciphertext, raw_acc)
            decrypted = decrypt_bank_account(ciphertext)
            self.assertEqual(decrypted, raw_acc)

    def test_key_rotation_with_multifernet(self):
        # 1. Encrypt with Key A
        with patch.dict(os.environ, {"BANK_DETAILS_ENCRYPTION_KEY": self.key_a}):
            raw_acc = "9876543210987654"
            ciphertext_a = encrypt_bank_account(raw_acc)

        # 2. Rotate keys: Key B is now primary, Key A is secondary/fallback
        with patch.dict(os.environ, {"BANK_DETAILS_ENCRYPTION_KEYS": f"{self.key_b},{self.key_a}"}):
            # MultiFernet can still decrypt ciphertext created with Key A
            decrypted_fallback = decrypt_bank_account(ciphertext_a)
            self.assertEqual(decrypted_fallback, raw_acc)

            # Re-encrypt/rotate to Key B
            rotated_ciphertext = rotate_bank_account_ciphertext(ciphertext_a)
            self.assertNotEqual(rotated_ciphertext, ciphertext_a)

        # 3. Key A is now completely retired; only Key B is active
        with patch.dict(os.environ, {"BANK_DETAILS_ENCRYPTION_KEY": self.key_b}):
            # Rotated ciphertext decrypts with Key B alone
            decrypted_final = decrypt_bank_account(rotated_ciphertext)
            self.assertEqual(decrypted_final, raw_acc)

    def test_mismatched_key_raises_decryption_error(self):
        # Encrypt with Key A
        with patch.dict(os.environ, {"BANK_DETAILS_ENCRYPTION_KEY": self.key_a}):
            ciphertext = encrypt_bank_account("0011223344556677")

        # Attempt to decrypt with unrelated Key C (no fallback)
        with patch.dict(os.environ, {"BANK_DETAILS_ENCRYPTION_KEY": self.key_c}):
            with self.assertRaises(DecryptionError):
                decrypt_bank_account(ciphertext)

    def test_corrupted_ciphertext_raises_decryption_error(self):
        with patch.dict(os.environ, {"BANK_DETAILS_ENCRYPTION_KEY": self.key_a}):
            with self.assertRaises(DecryptionError):
                decrypt_bank_account("corrupted_invalid_base64_string")

    def test_invalid_key_format_raises_configuration_error(self):
        with patch.dict(os.environ, {"BANK_DETAILS_ENCRYPTION_KEY": "not-a-valid-fernet-key"}):
            with self.assertRaises(KeyConfigurationError):
                encrypt_bank_account("12345678")


class VendorBankDetailsModelCryptoTests(TestCase):
    def setUp(self):
        self.key_a = Fernet.generate_key().decode("ascii")
        self.user = User.objects.create_user(username="crypto_vendor", email="vendor@test.com", password="pass")
        self.vendor = VendorProfile.objects.create(
            user=self.user,
            store_name="Crypto Test Store",
            slug="crypto-store",
            commission_rate=10,
        )

    def test_bank_details_model_with_dedicated_key(self):
        with patch.dict(os.environ, {"BANK_DETAILS_ENCRYPTION_KEY": self.key_a}):
            bank = VendorBankDetails.objects.create(
                vendor=self.vendor,
                bank_name="Nepal Bank Ltd",
                bank_account_name="Crypto Store P. Ltd.",
                bank_account_number="01234567899999",
            )
            # Database raw column contains ciphertext
            bank.refresh_from_db()
            self.assertNotEqual(bank.encrypted_account_number, "01234567899999")
            self.assertEqual(bank.last_four_digits, "9999")
            self.assertEqual(bank.masked_account_number, "************9999")
            self.assertEqual(bank.bank_account_number, "01234567899999")
