from decimal import Decimal
from django import forms
from django.utils.text import slugify

from store.models import (
    Category,
    ProductReview,
    ProductReviewReport,
    Product,
    ProductDigitalAsset,
    ProductInventory,
    ProductVariant,
)


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "title",
            "category",
            "product_type",
            "description",
            "is_cod_eligible",
            "is_internationally_available",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "input", "placeholder": "Product title"}),
            "category": forms.Select(attrs={"class": "select"}),
            "product_type": forms.Select(attrs={"class": "select"}),
            "description": forms.Textarea(attrs={"class": "textarea", "rows": 4}),
            "is_cod_eligible": forms.CheckboxInput(attrs={"class": "checkbox"}),
            "is_internationally_available": forms.CheckboxInput(attrs={"class": "checkbox"}),
        }

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        if not title:
            raise forms.ValidationError("Title cannot be blank.")
        return title

    def save(self, vendor=None, commit=True):
        product = super().save(commit=False)
        product.vendor = vendor
        if not product.slug:
            base_slug = slugify(product.title)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=product.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            product.slug = slug
        if commit:
            product.save()
        return product


class ProductVariantForm(forms.ModelForm):
    weight_grams = forms.IntegerField(required=False, initial=0, widget=forms.NumberInput(attrs={"class": "input"}))

    class Meta:
        model = ProductVariant
        fields = [
            "sku",
            "variant_name",
            "price",
            "compare_at_price",
            "weight_grams",
        ]
        widgets = {
            "sku": forms.TextInput(attrs={"class": "input", "placeholder": "Unique SKU code"}),
            "variant_name": forms.TextInput(attrs={"class": "input", "placeholder": "e.g. Standard, Hardcover, PDF"}),
            "price": forms.NumberInput(attrs={"class": "input", "step": "0.01"}),
            "compare_at_price": forms.NumberInput(attrs={"class": "input", "step": "0.01"}),
            "weight_grams": forms.NumberInput(attrs={"class": "input"}),
        }

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price is not None and price < Decimal("0.00"):
            raise forms.ValidationError("Price must be non-negative.")
        return price

    def clean_weight_grams(self):
        weight = self.cleaned_data.get("weight_grams")
        return weight or 0


class ProductInventoryForm(forms.ModelForm):
    class Meta:
        model = ProductInventory
        fields = [
            "quantity",
            "low_stock_threshold",
            "allow_backorder",
        ]
        widgets = {
            "quantity": forms.NumberInput(attrs={"class": "input"}),
            "low_stock_threshold": forms.NumberInput(attrs={"class": "input"}),
            "allow_backorder": forms.CheckboxInput(attrs={"class": "checkbox"}),
        }

    def clean_quantity(self):
        qty = self.cleaned_data.get("quantity")
        if qty is not None and qty < 0:
            raise forms.ValidationError("Quantity cannot be negative.")
        return qty


class ProductDigitalAssetForm(forms.ModelForm):
    class Meta:
        model = ProductDigitalAsset
        fields = [
            "file",
            "max_downloads_per_purchase",
            "download_validity_days",
        ]
        widgets = {
            "max_downloads_per_purchase": forms.NumberInput(attrs={"class": "input"}),
            "download_validity_days": forms.NumberInput(attrs={"class": "input"}),
        }


class ProductReviewActionForm(forms.Form):
    ACTION_APPROVE = "approve"
    ACTION_CHANGES_REQUIRED = "changes_required"
    ACTION_REJECT = "reject"

    ACTION_CHOICES = (
        (ACTION_APPROVE, "Approve and Publish to Storefront"),
        (ACTION_CHANGES_REQUIRED, "Request Changes from Seller"),
        (ACTION_REJECT, "Reject Product"),
    )

    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.RadioSelect)
    review_notes = forms.CharField(
        widget=forms.Textarea(attrs={"class": "textarea", "rows": 3, "placeholder": "Feedback for seller..."}),
        required=False,
    )

class MultipleFileInput(forms.FileInput):
    allow_multiple_selected = True


class ProductCustomerReviewForm(forms.ModelForm):
    review_images = forms.FileField(
        required=False,
        widget=MultipleFileInput(attrs={"multiple": True, "accept": "image/*", "class": "input"}),
        help_text="Optional photos (up to 3)"
    )

    class Meta:
        model = ProductReview
        fields = ["rating", "title", "content"]
        widgets = {
            "rating": forms.HiddenInput(),
            "title": forms.TextInput(attrs={"class": "input", "placeholder": "What's most important to know? (e.g. Great fitting shoes)", "maxlength": "150", "required": "required"}),
            "content": forms.Textarea(attrs={"class": "textarea", "rows": 4, "placeholder": "What did you like or dislike? How does it perform in daily use?", "required": "required"}),
        }


class ProductReviewReportForm(forms.ModelForm):
    class Meta:
        model = ProductReviewReport
        fields = ["reason"]
        widgets = {
            "reason": forms.TextInput(attrs={"class": "input", "placeholder": "Describe why this review is misleading or inappropriate", "required": "required"}),
        }

