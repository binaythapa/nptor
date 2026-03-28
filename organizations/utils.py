from django.shortcuts import get_object_or_404


def org_qs(model, request):
    return model.objects.filter(organization=request.organization)


def org_get(model, request, **kwargs):
    return get_object_or_404(
        model,
        organization=request.organization,
        **kwargs
    )