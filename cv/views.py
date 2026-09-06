from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from urllib.parse import quote

# ... existing imports and view definitions remain unchanged ...

@login_required
@xframe_options_sameorigin
def cv_preview(request, pk):
    cv = get_object_or_404(CV.objects.select_related("profile", "template"), pk=pk, owner=request.user)
    embedded = request.GET.get("embed") == "1"
    return render(
        request,
        "cv/preview.html",
        {"cv": cv, "embedded": embedded, **build_cv_render_context(cv)},
    )
