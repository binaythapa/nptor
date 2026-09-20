from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from quiz.models import Category, Domain


@login_required
def practice_categories(request):
    """Return active practice categories for the selected domain."""
    domain_id = request.GET.get("domain_id")

    if not domain_id:
        return JsonResponse({"categories": []})

    try:
        domain_id = int(domain_id)
    except (TypeError, ValueError):
        return JsonResponse({"categories": []}, status=400)

    if not Domain.objects.filter(id=domain_id, is_active=True).exists():
        return JsonResponse({"categories": []}, status=404)

    categories = Category.objects.filter(
        domain_id=domain_id,
        is_active=True,
    ).order_by("name")

    return JsonResponse(
        {
            "categories": [
                {"id": category.pk, "name": str(category)}
                for category in categories
            ]
        }
    )
