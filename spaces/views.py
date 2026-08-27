from django.views.generic import ListView

from .models import Space


class SpaceListView(ListView):
    model = Space
    template_name = "spaces/space_list.html"
    context_object_name = "spaces"

    def get_queryset(self):
        return Space.objects.filter(is_active=True)
