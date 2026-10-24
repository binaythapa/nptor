# NPTOR Store — Production Deployment Guide & Operational Runbook

This document details the exact configuration, infrastructure prerequisites, deployment procedures, operational runbooks, and rollback protocols for launching the **NPTOR Store MVP**.

---

## 1. System Architecture & Boundaries

The NPTOR Store MVP provides a multi-vendor marketplace tailored for Nepal's educational and book retail ecosystem:
- **Product Catalog & Details**: Physical books and digital downloadable resources (study manuals, question sets, mock PDFs).
- **Cart & Reservation**: In-memory and persisted carts, session-to-account guest merge, atomic 15-minute stock reservations to prevent overselling.
- **Nepal-Centric Checkout**: Mandatory Nepal delivery validation (`country="NP"`), district/province address capture, and Cash on Delivery (COD) restriction (ineligible for pure digital products).
- **Payment Processing**: Provider-independent payment adapter interface. In MVP, the deterministic `DummyPaymentAdapter` is configured; live ConnectIPS/eSewa/Khalti gateway credentials are separated for future activation.
- **Digital Delivery Engine**: Cryptographically secure 64-hex delivery tokens, `select_for_update` concurrency locking, download counters, 30-day token expiry, revocability, and protected filesystem storage located strictly outside the public webroot.
- **Multi-Vendor Suborders & Ledger**: Automated master-order splitting by vendor, isolated suborder fulfillment dashboards, platform commission calculation, double-entry immutable vendor ledger records, and payout allocation tracking.
- **Staff Administration**: Staff order overview (`@staff_member_required`) and audited payout review.

---

## 2. Environment Variables & Secrets Reference

In production, all secrets must be supplied via system environment variables or secure deployment files (e.g. cPanel environment configuration, systemd service overrides, or Docker environment secrets). **Never commit credentials to version control.**

| Environment Variable | Required | Description / Example |
| :--- | :--- | :--- |
| `DJANGO_SETTINGS_MODULE` | Yes | `objective_exam.settings` |
| `SECRET_KEY` | Yes | High-entropy secret string for Django cryptographic signing. |
| `DEBUG` | Yes | Must be set to `False` in production. |
| `ALLOWED_HOSTS` | Yes | Comma-separated domains, e.g. `nptor.com,www.nptor.com`. |
| `DB_NAME` | Yes | Production MySQL database name, e.g. `nptorcom_db`. |
| `DB_USER` | Yes | Database user, e.g. `nptorcom_admin`. |
| `DB_PASSWORD` | Yes | Strong database password. |
| `DB_HOST` | Yes | Database host (`127.0.0.1` or socket). |
| `DB_PORT` | No | `3306` (default). |
| `BANK_DETAILS_ENCRYPTION_KEY` | Yes | 32-byte URL-safe base64-encoded Fernet AES key used to encrypt seller bank accounts in `VendorBankDetails`. Can be generated with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. |
| `BANK_DETAILS_ENCRYPTION_KEYS` | Optional | Comma-separated list of keys `primary_key,old_key_1,old_key_2` for zero-downtime key rotation. Decryption attempts keys in order; new encryptions use the primary key. |
| `PROTECTED_STORAGE_ROOT` | Yes | Absolute filesystem path outside webroot for secure digital downloads. Default on production cPanel: `/home3/nptorcom/protected_storage`. |
| `EMAIL_HOST_USER` | Yes | SMTP user for order confirmation emails (e.g., Gmail or Amazon SES). |
| `EMAIL_HOST_PASSWORD` | Yes | App password or SMTP password. |
| `DEFAULT_FROM_EMAIL` | No | Display sender: `NPTOR Store <store@nptor.com>`. |
| `SESSION_COOKIE_SECURE` | Yes | `True` for HTTPS. |
| `CSRF_COOKIE_SECURE` | Yes | `True` for HTTPS. |

---

## 3. Protected Storage Setup & Web Server Security

### Directory Location & Permissions
Digital products must NEVER be placed in public webroots like `/home3/nptorcom/public_html/media/` or `/home3/nptorcom/public_html/static/`.

```bash
# 1. Create protected storage directory outside public_html
mkdir -p /home3/nptorcom/protected_storage/store/digital_assets

# 2. Set restrictive directory permissions (accessible only by the application user)
chmod 750 /home3/nptorcom/protected_storage
chmod -R 750 /home3/nptorcom/protected_storage/store
```

### Web Server Direct-Access Prevention
Even though `ProtectedFileSystemStorage.url()` deliberately raises a `ValueError` to block public URL construction, defense-in-depth requires explicit web server denial.

#### Nginx Configuration Block
If Nginx sits in front of the application:
```nginx
# Explicitly block any request attempting to route to protected storage
location /protected_storage/ {
    deny all;
    return 404;
}
```

#### Apache `.htaccess` Block (in `/home3/nptorcom/protected_storage/.htaccess`)
```apache
<IfModule mod_authz_core.c>
    Require all denied
</IfModule>
<IfModule !mod_authz_core.c>
    Order deny,allow
    Deny from all
</IfModule>
```

---

## 4. Database Migration Order & Considerations

The store suite contains models across four interdependent applications. Run migrations in this verified order:

1. `vendors` (creates `VendorProfile`, `VendorBankDetails`, `VendorLedger`, `VendorPayoutBatch`, `VendorPayoutAllocation`)
2. `store` (creates `Category`, `Product`, `ProductVariant`, `ProductInventory`, `ProductImage`, `ProductDigitalAsset`)
3. `cart` (creates `Cart`, `CartItem`, `StockReservation`)
4. `orders` (creates `ShippingAddress`, `Order`, `SubOrder`, `OrderItem`, `OrderPayment`, `DigitalDelivery`, `OrderReturnRequest`)

### Data Safety & Idempotency Notes
- **No Table Overwrites**: Store migrations introduce completely isolated store tables with foreign keys to Django's `AUTH_USER_MODEL`. Existing educational and exam tables are untouched.
- **Encrypted Fields**: Existing vendor bank account numbers are stored as Fernet ciphertext in `bank_account_ciphertext`. Never run raw text inserts directly into MySQL without using `vendors.crypto.encrypt_bank_account`.
- **Constraint Check**: MySQL check constraints enforce non-negative quantities on `ProductInventory` (`quantity >= 0`, `reserved_quantity >= 0`).

---

## 5. Deployment Commands Sequence

Execute the following deployment steps on the production server within the virtual environment:

```bash
# Step 1: Activate application virtual environment
source /home3/nptorcom/virtualenv/nptor/3.12/bin/activate
cd /home3/nptorcom/repositories/nptor

# Step 2: Backup current database before making changes
mysqldump -u nptorcom_admin -p nptorcom_db > /home3/nptorcom/backups/db_backup_pre_store_$(date +%Y%m%d_%H%M%S).sql

# Step 3: Fetch latest release candidate branch
git fetch origin
git checkout feature/store-commerce-foundation  # Or release/store-mvp upon merge

# Step 4: Run system check to verify environment settings
python manage.py check --deploy

# Step 5: Execute database migrations
python manage.py migrate vendors
python manage.py migrate store
python manage.py migrate cart
python manage.py migrate orders

# Step 6: Collect static assets
python manage.py collectstatic --noinput

# Step 7: Create protected storage directory if not already existing
mkdir -p /home3/nptorcom/protected_storage/store/digital_assets
chmod 750 /home3/nptorcom/protected_storage

# Step 8: Gracefully reload WSGI/Passenger application server
touch /home3/nptorcom/tmp/restart.txt
```

---

## 6. Post-Deployment Verification Checklist (Smoke Tests)

Immediately following deployment, run through these smoke verifications:

1. **Catalog Browsing**:
   - Visit `/store/` (catalog index) and verify categories and products render.
   - Visit `/store/<product-slug>/` and check variant pricing, stock badges, and "Add to Cart" button.
2. **Cart & Reservation**:
   - Add items to cart as an anonymous visitor at `/store/cart/`.
   - Log in and verify guest cart seamlessly merges into the user cart.
   - Proceed to `/store/orders/checkout/` and verify cart items and subtotal match.
3. **Checkout Validation**:
   - Attempt physical order submission with a non-Nepal country (must be blocked).
   - Attempt digital-only order submission with Cash on Delivery (must be blocked).
   - Complete checkout with a valid Nepal address and select Cash on Delivery. Confirm redirect to customer order confirmation.
4. **Order Split & Seller Dashboard**:
   - Log in as the vendor account for the purchased item.
   - Navigate to `/store/vendors/suborders/` and verify the suborder is visible in the fulfillment queue.
   - Update shipping details: input carrier "Nepal Post" and tracking number "NP-SMOKE-1", submit "Mark as Shipped", and verify fulfillment status updates to `shipped`.
5. **Simulated Payment & Digital Delivery Streaming**:
   - Place an order with an e-book using online payment.
   - Click "Pay with Simulated Gateway" and complete the simulated return.
   - Confirm order status updates to `paid` and download link appears.
   - Click "Download Resource", verify browser streams the file, and verify download counter decrements.
6. **Platform Administration**:
   - Access `/store/orders/admin/` with staff credentials. Verify all placed test orders appear with accurate statuses.

---

## 7. Rollback Protocol

If an unexpected production defect occurs during launch, execute this procedure:

### Fast Rollback (Disable Store Routing)
If issues are isolated to store frontend traffic:
1. In `objective_exam/urls.py`, comment out the store routes:
   ```python
   # path("store/", include("store.urls", namespace="store")),
   # path("store/cart/", include("cart.urls", namespace="cart")),
   # path("store/orders/", include("orders.urls", namespace="orders")),
   # path("store/vendors/", include("vendors.urls", namespace="vendors")),
   ```
2. Reload application: `touch /home3/nptorcom/tmp/restart.txt`. The education and exam platform continues operating with zero disruption.

### Complete Rollback (Database & Code Revert)
If database changes or code must be completely reverted:
```bash
# Step 1: Revert migrations in reverse order
python manage.py migrate orders zero
python manage.py migrate cart zero
python manage.py migrate store zero
python manage.py migrate vendors zero

# Step 2: Checkout previous stable commit/branch
git checkout main

# Step 3: Re-collect static assets
python manage.py collectstatic --noinput

# Step 4: (Optional) If table state became inconsistent, restore database backup
mysql -u nptorcom_admin -p nptorcom_db < /home3/nptorcom/backups/db_backup_pre_store_<TIMESTAMP>.sql

# Step 5: Reload WSGI
touch /home3/nptorcom/tmp/restart.txt
```

---

## 8. Operational Runbook

### Daily Operations
1. **Fulfillment Tracking**:
   - Daily monitoring of unfulfilled suborders past 48 hours via `/store/orders/admin/`.
   - Sellers receive automated dashboard flags for pending physical orders.
2. **COD Remittance Reconciliation**:
   - When couriers deposit collected cash into NPTOR bank account, platform staff enters remittance reference via `OrderWorkflowService.reconcile_cod_remittance(suborder, courier_remittance_ref)`.
   - This automatically unlocks the gross sale and commission entries on the seller ledger.
3. **Digital Delivery Token Management**:
   - If a customer exhausts downloads legitimately (e.g., lost device), staff can inspect `DigitalDelivery` in Django admin and reset `download_count = 0` or extend `expires_at`.
   - If fraud or chargeback occurs, staff toggles `is_revoked = True`.

### Key Rotation Procedure
To rotate seller bank encryption keys without downtime:
1. Generate new 32-byte Fernet key: `NEW_KEY`.
2. Update environment variable `BANK_DETAILS_ENCRYPTION_KEYS="<NEW_KEY>,<OLD_KEY>"`.
3. Reload server. MultiFernet decrypts using `<OLD_KEY>` and re-encrypts any updated bank profiles using `<NEW_KEY>`.
4. (Optional) Run the batch key migration utility to re-encrypt all existing rows to `<NEW_KEY>`, then remove `<OLD_KEY>` from the environment.
