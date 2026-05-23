from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Q

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Project, Task, Tag, Comment
from .serializers import (
    ProjectSerializer, TaskSerializer,
    TagSerializer, CommentSerializer
)
from .permissions import (
    IsManagerOrAdmin,
    IsProjectMember,
    IsAssignedDeveloperOrManager
)


# ─── Tag ViewSet ──────────────────────────────────────────────────────────────
class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]


# ─── Project ViewSet ──────────────────────────────────────────────────────────
class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def get_queryset(self):
        user = self.request.user

        # ── select_related fixes N+1 for ForeignKey (owner) ──────────────────
        # Without this: fetching 10 projects = 11 queries
        # (1 for projects + 1 for each owner)
        # With this: fetching 10 projects = 1 query (SQL JOIN)
        base_qs = Project.objects.select_related('owner')

        # ── prefetch_related fixes N+1 for ManyToMany (members) ──────────────
        # select_related won't work for M2M — use prefetch_related instead
        # It does 2 queries total regardless of how many projects
        base_qs = base_qs.prefetch_related('members')

        if user.role == 'admin':
            return base_qs.all()

        return base_qs.filter(owner=user) | base_qs.filter(members=user)

    def get_permissions(self):
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsProjectMember()]
        return [IsAuthenticated(), IsManagerOrAdmin()]

    # ── Custom action: list tasks for a project ───────────────────────────────
    @action(detail=True, methods=['get'], url_path='tasks')
    def tasks(self, request, pk=None):
        project = self.get_object()

        # select_related for all ForeignKey fields in one query
        tasks = project.tasks.select_related(
            'assigned_to',
            'created_by',
            'project'
        ).prefetch_related(
            'tags',       # M2M
            'comments',   # reverse FK
            'comments__author'  # nested FK inside comments
        )

        serializer = TaskSerializer(
            tasks, many=True, context={'request': request}
        )
        return Response(serializer.data)

    # ── Cached stats endpoint ─────────────────────────────────────────────────
    @action(detail=True, methods=['get'], url_path='stats')
    def stats(self, request, pk=None):
        project = self.get_object()

        # Cache key is unique per project
        cache_key = f'project_stats_{project.id}'

        # Step 1: check if result is already in cache
        cached_data = cache.get(cache_key)
        if cached_data:
            # Cache HIT — return instantly, no DB query
            cached_data['from_cache'] = True
            return Response(cached_data)

        # Step 2: cache MISS — query the database
        # annotate() does the counting IN SQL (faster than Python loops)
        # One query instead of 5 separate .count() calls
        tasks = project.tasks.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='pending')),
            in_progress=Count('id', filter=Q(status='in_progress')),
            in_review=Count('id', filter=Q(status='in_review')),
            done=Count('id', filter=Q(status='done')),
        )

        data = {
            'project_id':  project.id,
            'project_name': project.name,
            **tasks,
            'from_cache': False
        }

        # Step 3: store in cache for 5 minutes (300 seconds)
        # Next request in 5 mins = instant, no DB hit
        cache.set(cache_key, data, timeout=300)

        return Response(data)


# ─── Task ViewSet ─────────────────────────────────────────────────────────────
class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Always use select_related for FK fields
        # Always use prefetch_related for M2M fields
        base_qs = Task.objects.select_related(
            'project',
            'assigned_to',
            'created_by'
        ).prefetch_related('tags', 'comments', 'comments__author')

        if user.role == 'admin':
            return base_qs.all()
        if user.role == 'manager':
            return base_qs.filter(project__owner=user)
        return base_qs.filter(assigned_to=user)

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsManagerOrAdmin()]
        if self.action in ['update', 'partial_update']:
            return [IsAuthenticated(), IsAssignedDeveloperOrManager()]
        if self.action == 'destroy':
            return [IsAuthenticated(), IsManagerOrAdmin()]
        return [IsAuthenticated()]

    # ── Bulk assign tasks using @transaction.atomic ───────────────────────────
    @action(detail=False, methods=['post'], url_path='bulk-assign')
    @transaction.atomic
    def bulk_assign(self, request):
        """
        Assign multiple tasks to a user at once.
        @transaction.atomic means: if ANY task fails to update,
        ALL updates are rolled back. No partial data.

        Example body:
        {
            "task_ids": [1, 2, 3],
            "assigned_to_id": 2
        }
        """
        task_ids = request.data.get('task_ids', [])
        assigned_to_id = request.data.get('assigned_to_id')

        if not task_ids or not assigned_to_id:
            return Response(
                {'error': 'task_ids and assigned_to_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from accounts.models import User
        try:
            assignee = User.objects.get(id=assigned_to_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # This runs inside a transaction
        # If any update fails → ALL updates roll back automatically
        tasks = Task.objects.filter(id__in=task_ids)
        updated_count = tasks.update(assigned_to=assignee)

        return Response({
            'message': f'{updated_count} tasks assigned to {assignee.username}',
            'assigned_to': assignee.username,
            'task_ids': task_ids
        })

    # ── Comments endpoint ─────────────────────────────────────────────────────
    @action(detail=True, methods=['get', 'post'], url_path='comments')
    def comments(self, request, pk=None):
        task = self.get_object()

        if request.method == 'GET':
            # only() fetches ONLY these columns — not all columns
            # much faster when you have wide tables with many fields
            comments = task.comments.select_related(
                'author'
            ).only(
                'id', 'body', 'created_at',
                'author__id', 'author__username'
            )
            serializer = CommentSerializer(comments, many=True)
            return Response(serializer.data)

        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=request.user, task=task)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )