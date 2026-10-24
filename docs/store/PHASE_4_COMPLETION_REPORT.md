# NPTOR Store — Phase 4 Completion Report: Database-Backed Cart, Inventory Reservations & Checkout Engine

**Date:** 2026-10-23  
**Branch:** `feature/store-commerce-foundation`  
**Status:** Completed & Verified  

---

## 1. Executive Summary

Phase 4 of the native Django NPTOR Store has been successfully implemented and verified locally on branch `feature/store-commerce-foundation`.

All objectives defined in the Phase 4 authorization have been delivered:
1. **Seller Banking Security & AES-256 Encryption-at-Rest:** Plaintext bank account numbers have been eliminated from the schema and replaced with AES-256 Fernet-encrypted ciphertext, masked account presentation (`************1234`), property encapsulation, and strict multi-tenant isolation.
2. **Protected Digital Asset Storage:** Created a dedicated non-public filesystem storage backend outside the webroot with direct URL generation disabled (`base_url=None`), preventing unauthorized digital asset streaming or exposure.
3. **Database-Backed Shopping Cart & Atomic Stock Reservations:** Built `Cart`, `CartItem`, and `StockReservation` models with session/user lifecycle support, cart merging on login, real-time price change detection, draft/inactive product rejection, and atomic inventory row locking (`select_for_update()`) ordered deterministically by variant ID to eliminate deadlock risk.
4. **Multi-Vendor Checkout Engine:** Implemented `prepare_checkout()` orchestrating server-side validation, Nepal delivery gating for physical goods (`country == 'NP'`), international digital checkout enablement, strict COD restrictions (prohibiting COD for digital and mixed carts), multi-vendor cart splitting into independent `SubOrder` records with commission deductions, and duplicate checkout prevention via idempotency keys.
5. **Zero Educational Impact & Safe Baseline Preservation:** Educational courses, exams, subscriptions, and existing payment pipelines (`payments.models.PaymentOrder`) remain untouched. All 46 Store-related tests pass (100% pass rate).

---

## 2. Seller Banking Security Verification & Implementation

Prior to implementing cart and checkout workflows, `VendorBankDetails` was audited and hardened:

- **Vulnerability Identified:** The initial schema stored `bank_account_number` as plain database text, presenting risk in the event of database access or dump exposure.
- **AES-256 Fernet Encryption at Rest:** Created `vendors/crypto.py` providing `encrypt_bank_account()` and `decrypt_bank_account()`. Encryption uses 32-byte URL-safe base64 keys derived from `settings.SECRET_KEY` or an optional dedicated `BANK_DETAILS_ENCRYPTION_KEY` environment variable.
- **Model Refactoring (`vendors/models.py`):**
  - Replaced `bank_account_number` column with `encrypted_account_number` (CharField) and `last_four_digits` (CharField(4)).
  - Encapsulated `@property def bank_account_number` getter and setter to seamlessly encrypt upon write and decrypt in memory upon read.
  - Provided `@property def masked_account_number` displaying `************1234`, computed purely from `last_four_digits` without invoking cryptography routines.
- **Tenant Isolation & Logging Safeguards:**
  - Ordinary vendor portal views query strictly via `vendor=request.user.vendor_profile`.
  - Admin and portal templates display only `masked_account_number`.
  - Migration `vendors.0002_remove_vendorbankdetails_bank_account_number_and_more` applied cleanly.
  - Unit tests in `vendors/tests.py` and `vendors/tests_onboarding.py` confirm raw database column contains ciphertext while Python property returns plaintext and masked display reflects last four digits.

---

## 3. Protected Digital Asset Storage Implementation

To guarantee digital file security before any purchases take place:
- **Dedicated Storage Class (`store/storage.py`):** Configured `FileSystemStorage` configured with `base_url=None` and directory location pointing to `BASE_DIR / "protected_storage"` (or `/home3/nptorcom/protected_storage` in production).
- **Direct Link Elimination:** Because `base_url` is `None`, any call to `asset.file.url` raises `ValueError`, guaranteeing that templates or views cannot inadvertently expose direct public URLs.
- **Model Migration (`store/models.py`):** `ProductDigitalAsset.file` utilizes `storage=protected_storage`. Applied via migration `store.0003_alter_productdigitalasset_file`.

---

## 4. Database-Backed Cart & Stock Reservation Engine

Implemented in `cart/services/cart_service.py` and `cart/services/reservation_service.py`:

| Service Function | Capability & Safeguards |
|---|---|
| `get_or_create_cart(request)` | Resolves persistent cart for authenticated users or anonymous session keys (`request.session.session_key`). |
| `merge_carts(guest_cart, user_cart)` | On login, merges guest cart items into user cart; updates quantities and purges guest cart record. |
| `add_to_cart()`, `update_cart_item()`, `remove_from_cart()` | Validates quantity > 0, enforces live stock boundaries (`quantity - reserved_quantity`), and blocks draft, unapproved, or inactive products. |
| `validate_cart(cart)` | Auto-purges items whose products were deactivated/unapproved, updates item unit prices if vendor modified them, alerts caller to price changes, and classifies cart composition (`physical_only`, `digital_only`, `mixed`). |
| `reserve_cart_stock(cart, ttl_minutes=15)` | Within an atomic transaction, acquires `select_for_update()` locks on `ProductInventory` ordered deterministically by `variant_id` (preventing MySQL deadlocks). Increments `reserved_quantity` and generates `StockReservation` with expiry timestamp. |
| `release_cart_reservations(cart)` | Safely releases active reservations and restores available stock if checkout is abandoned or fails. |
| `release_expired_reservations()` | Celery / cron maintenance task releasing expired reservations back to inventory. |

---

## 5. Multi-Vendor Checkout & Order Preparation Engine

Implemented in `orders/services/checkout_service.py`:

1. **Market Scope & Nepal Physical Delivery Gating:**
   - Physical and mixed carts strictly require `shipping_address["country"] == "NP"`.
   - International orders for physical goods are blocked with descriptive validation errors.
   - Digital-only carts can be checked out worldwide (`country != "NP"` permitted).
2. **Server-Side COD Policy:**
   - Prohibits COD for digital-only carts (digital goods require online payment).
   - Prohibits COD for mixed physical/digital carts.
   - Validates that every vendor in the cart has COD enabled (`vendor.is_cod_eligible == True`).
3. **Atomic Stock Locking:**
   - Invokes `ReservationService.reserve_cart_stock(cart)` prior to order generation.
4. **Multi-Vendor Cart Splitting:**
   - Generates a master `Order` capturing grand totals, customer details, and shipping address.
   - Iterates through distinct vendors and creates an independent `SubOrder` for each vendor.
   - Associates `OrderItem` records with the corresponding `SubOrder`.
   - Calculates vendor commission: `platform_commission = suborder.items_subtotal * vendor.commission_rate / 100` and records `seller_payout_amount = suborder.grand_total - platform_commission`.
5. **Pending Payment & Idempotency:**
   - Creates an `OrderPayment` record in `status="pending"`.
   - Enforces duplicate checkout protection via `idempotency_key` unique constraints.
6. **Cart Cleanup:**
   - Upon successful preparation, marks cart as `abandoned` (cleared) so user's cart is refreshed.

---

## 6. Verification & Test Results

### A. Store & Commerce Test Suite
Ran command:
```powershell
.\venv\Scripts\python.exe manage.py test cart orders vendors store --keepdb
```
**Results:**
- `cart.tests_cart_service`: 7 tests passed (anonymous/authenticated carts, cart merging, unapproved rejection, stock limits, price change handling, atomic reservation, expiry release).
- `orders.tests_checkout`: 7 tests passed (Nepal delivery enforcement, international digital checkout, COD validation, multi-vendor order splitting, platform commission calculation, idempotency).
- `vendors.tests` & `vendors.tests_onboarding`: 15 tests passed (AES encryption-at-rest, masked account numbers, onboarding workflow, vendor profile boundaries).
- `store.tests`: 17 tests passed (catalog, taxonomy, variant forms, inventory constraints).
- **Total Store Tests:** 46 passing out of 46 (100% pass rate).

### B. System Integrity & Backward Compatibility
- `manage.py check`: Passed with 0 system errors.
- Existing educational models (`courses`, `quiz`, `payments.models.PaymentOrder`) remain completely isolated and unmodified.
- No real payment gateway credentials activated; no mock payments processed; no live courier API integrated.

---

## 7. Phase 5 Readiness

With Phase 4 complete, the commerce engine is ready for **Phase 5: Payment Integration, COD Confirmation & Order Placement Workflows**:
- Offline / COD order completion workflow.
- Nepal online payment adapter foundation (eSewa / Khalti / Fonepay abstraction layer).
- Secure webhook & callback verification architecture.
- Transitioning `StockReservation` from reserved to permanently deducted upon payment verification.
