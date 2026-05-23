from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet, TaskViewSet, TagViewSet

# Router auto-generates all URLs from a ViewSet
# One line replaces 10+ manual url patterns
router = DefaultRouter()
router.register('projects', ProjectViewSet, basename='project')
router.register('tasks',    TaskViewSet,    basename='task')
router.register('tags',     TagViewSet,     basename='tag')

urlpatterns = [
    path('', include(router.urls)),
]