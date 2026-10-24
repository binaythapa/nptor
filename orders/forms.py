import re
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from orders.models import Order, ShippingAddress


class CheckoutForm(forms.ModelForm):
    payment_method = forms.ChoiceField(
        choices=Order.PAYMENT_METHOD_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "radio"}),
        initial=Order.PAYMENT_METHOD_COD,
    )
    idempotency_key = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
    )

    class Meta:
        model = ShippingAddress
        fields = [
            "full_name",
            "phone",
            "street_address_1",
            "street_address_2",
            "city",
            "district",
            "province",
            "postal_code",
            "country",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "input", "placeholder": "Recipient Full Name"}),
            "phone": forms.TextInput(attrs={"class": "input", "placeholder": "e.g. 9800000000"}),
            "street_address_1": forms.TextInput(attrs={"class": "input", "placeholder": "Street / Ward / Tole"}),
            "street_address_2": forms.TextInput(attrs={"class": "input", "placeholder": "Apartment / Landmark (Optional)"}),
            "city": forms.TextInput(attrs={"class": "input", "placeholder": "City / Municipality"}),
            "district": forms.TextInput(attrs={"class": "input", "placeholder": "District (e.g. Kathmandu, Kaski)"}),
            "province": forms.TextInput(attrs={"class": "input", "placeholder": "Province (e.g. Bagmati)"}),
            "postal_code": forms.TextInput(attrs={"class": "input", "placeholder": "Postal Code (Optional)"}),
            "country": forms.HiddenInput(),
        }

    def __init__(self, *args, requires_shipping=True, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.requires_shipping = requires_shipping
        self.user = user
        self.fields["country"].initial = "NP"
        self.fields["country"].required = False

        # In Day-1 release, default initial payment method to Cash on Delivery
        allow_online = bool(
            (user and user.is_staff) or getattr(settings, "ENABLE_DUMMY_PAYMENT_GATEWAY", False)
        )
        if not allow_online:
            self.fields["payment_method"].initial = Order.PAYMENT_METHOD_COD

        if not requires_shipping:
            # Digital-only order; all shipping address fields are optional
            for name, field in self.fields.items():
                if name not in ["payment_method", "idempotency_key"]:
                    field.required = False

    def clean_payment_method(self):
        pm = self.cleaned_data.get("payment_method")
        allow_online = bool(
            (self.user and self.user.is_staff) or getattr(settings, "ENABLE_DUMMY_PAYMENT_GATEWAY", False)
        )
        if pm == Order.PAYMENT_METHOD_ONLINE and not allow_online:
            raise ValidationError("Online payments are currently disabled for public orders. Please select Cash on Delivery.")
        return pm

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if self.requires_shipping:
            clean_digits = re.sub(r"[^\d+]", "", phone)
            if len(clean_digits) < 7:
                raise ValidationError("Please enter a valid telephone or mobile number.")
        return phone

    def clean_country(self):
        country = self.cleaned_data.get("country") or "NP"
        if self.requires_shipping and country != "NP":
            raise ValidationError("Physical shipping is currently available only within Nepal (NP).")
        return country
