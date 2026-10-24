import threading
from decimal import Decimal
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TransactionTestCase
from django.utils import timezone

from cart.models import Cart, StockReservation
from orders.models import Order, OrderPayment
from store.models import Category, Product, ProductInventory, ProductVariant

User = get_user_model()


class StoreConcurrencyTests(TransactionTestCase):
    """
    Concurrency and lock ordering tests executed against actual database engine
    to verify row locking (select_for_update) and idempotency deduplication.
    """

    def setUp(self):
        self.user = User.objects.create_user(username="concur_buyer", email="cb@example.com", password="pass")
        self.category = Category.objects.create(name="Concurrency Gear", slug="concurrency-gear")
        self.product = Product.objects.create(
            title="Limited Edition Lab Kit",
            slug="limited-edition-lab-kit",
            category=self.category,
            product_type=Product.TYPE_PHYSICAL,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="LE-KIT-001",
            price=Decimal("5000.00"),
            currency="NPR",
        )
        self.inventory = ProductInventory.objects.create(
            variant=self.variant,
            quantity=5,  # Only 5 units total
            reserved_quantity=0,
        )

    def test_concurrent_stock_reservation_race_condition(self):
        """
        Two concurrent checkout attempts competing for stock where only 1 can succeed.
        Total available: 5. Thread A asks for 4, Thread B asks for 4.
        Exactly one thread must succeed and one must fail.
        """
        cart_a = Cart.objects.create(user=self.user, currency="NPR")
        cart_b = Cart.objects.create(session_key="guest_sess_concur", currency="NPR")

        results = []
        errors = []

        def reserve_stock(cart, requested_units):
            from django.db import connection
            connection.close()
            try:
                with transaction.atomic():
                    # Explicit lock ordering with select_for_update
                    inv = (
                        ProductInventory.objects
                        .select_for_update()
                        .get(variant_id=self.variant.id)
                    )
                    available = inv.quantity - inv.reserved_quantity
                    if available >= requested_units:
                        inv.reserved_quantity += requested_units
                        inv.save(update_fields=["reserved_quantity"])
                        res = StockReservation.objects.create(
                            cart=cart,
                            variant=self.variant,
                            reserved_units=requested_units,
                            expires_at=timezone.now() + timedelta(minutes=15),
                        )
                        results.append((cart.id, True))
                    else:
                        results.append((cart.id, False))
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=reserve_stock, args=(cart_a, 4))
        t2 = threading.Thread(target=reserve_stock, args=(cart_b, 4))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 2)
        success_count = sum(1 for _, success in results if success)
        failure_count = sum(1 for _, success in results if not success)
        self.assertEqual(success_count, 1)
        self.assertEqual(failure_count, 1)

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.reserved_quantity, 4)
        self.assertEqual(self.inventory.available_quantity, 1)

    def test_concurrent_duplicate_checkout_idempotency(self):
        """
        Verify that concurrent duplicate checkout requests with the same idempotency key
        result in exactly one Order being created without race conditions.
        """
        idempotency_key = "IDEM_CONCUR_CHECKOUT_999"
        created_orders = []
        exceptions = []

        def place_order(order_num):
            from django.db import connection
            connection.close()
            try:
                order = Order.objects.create(
                    order_number=order_num,
                    user=self.user,
                    total_items_amount=Decimal("1500.00"),
                    grand_total=Decimal("1500.00"),
                    idempotency_key=idempotency_key,
                )
                created_orders.append(order)
            except IntegrityError as exc:
                exceptions.append(exc)

        t1 = threading.Thread(target=place_order, args=("NPTOR-ORD-T1",))
        t2 = threading.Thread(target=place_order, args=("NPTOR-ORD-T2",))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(len(created_orders), 1)
        self.assertEqual(len(exceptions), 1)
        self.assertEqual(Order.objects.filter(idempotency_key=idempotency_key).count(), 1)

    def test_concurrent_webhook_deduplication(self):
        """
        Verify that two duplicate gateway webhook notifications hitting the server simultaneously
        are deduplicated by the database unique constraint on idempotency_key.
        """
        order = Order.objects.create(
            order_number="NPTOR-ORD-WH-001",
            user=self.user,
            total_items_amount=Decimal("2000.00"),
            grand_total=Decimal("2000.00"),
        )
        webhook_idempotency_key = "WEBHOOK_EVENT_TXN_8888"
        created_payments = []
        rejected_duplicates = []

        def process_webhook():
            from django.db import connection
            connection.close()
            try:
                payment = OrderPayment.objects.create(
                    order=order,
                    amount=Decimal("2000.00"),
                    currency="NPR",
                    status=OrderPayment.STATUS_SUCCESSFUL,
                    gateway_name="esewa",
                    gateway_payment_id="ESEWA-TXN-8888",
                    idempotency_key=webhook_idempotency_key,
                )
                created_payments.append(payment)
            except IntegrityError as exc:
                rejected_duplicates.append(exc)

        t1 = threading.Thread(target=process_webhook)
        t2 = threading.Thread(target=process_webhook)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(len(created_payments), 1)
        self.assertEqual(len(rejected_duplicates), 1)
        self.assertEqual(OrderPayment.objects.filter(idempotency_key=webhook_idempotency_key).count(), 1)
