from quiz.models import PaymentRecord

class PaymentService:

    @staticmethod
    def record_payment(
        user, amount, *,
        exam=None, track=None,
        method="upi", reference_id=None
    ):
        return PaymentRecord.objects.create(
            user=user,
            exam=exam,
            track=track,
            amount=amount,
            payment_method=method,
            reference_id=reference_id,
            created_by_admin=False
        )
