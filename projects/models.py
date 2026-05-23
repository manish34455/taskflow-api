from django.db import models
from django.conf import settings


# ─── Custom Manager for Tasks ─────────────────────────────────────────────────
# Instead of Task.objects.filter(status='pending') scattered everywhere,
# use Task.objects.pending() — readable, reusable.

class TaskManager(models.Manager):

    def pending(self):
        return self.get_queryset().filter(status=Task.PENDING)

    def in_progress(self):
        return self.get_queryset().filter(status=Task.IN_PROGRESS)

    def done(self):
        return self.get_queryset().filter(status=Task.DONE)

    def overdue(self):
        from django.utils import timezone
        return self.get_queryset().filter(
            due_date__lt=timezone.now(),
            status__in=[Task.PENDING, Task.IN_PROGRESS]
        )

    def assigned_to(self, user):
        return self.get_queryset().filter(assigned_to=user)


# ─── Tag model ────────────────────────────────────────────────────────────────
# Simple label. Tasks will have a ManyToMany relationship with tags.

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default='#3B82F6')  # hex color

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'tags'
        ordering = ['name']


# ─── Project model ────────────────────────────────────────────────────────────

class Project(models.Model):
    ACTIVE = 'active'
    ARCHIVED = 'archived'
    COMPLETED = 'completed'

    STATUS_CHOICES = [
        (ACTIVE, 'Active'),
        (ARCHIVED, 'Archived'),
        (COMPLETED, 'Completed'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=ACTIVE,
        db_index=True,   # we filter by status a lot
    )

    # ForeignKey = many projects → one owner (Many-to-one)
    # settings.AUTH_USER_MODEL is safer than importing User directly
    # on_delete=CASCADE: delete project if owner is deleted
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_projects'  # user.owned_projects.all()
    )

    # ManyToMany: a project can have many members, a user can be in many projects
    # Django creates a junction table automatically
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='joined_projects',
        blank=True  # blank=True: OK to have no members
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name} [{self.status}]'

    class Meta:
        db_table = 'projects'
        ordering = ['-created_at']  # newest first


# ─── Task model ───────────────────────────────────────────────────────────────

class Task(models.Model):
    # Status choices
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    IN_REVIEW = 'in_review'
    DONE = 'done'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (IN_PROGRESS, 'In Progress'),
        (IN_REVIEW, 'In Review'),
        (DONE, 'Done'),
    ]

    # Priority choices
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'

    PRIORITY_CHOICES = [
        (LOW, 'Low'),
        (MEDIUM, 'Medium'),
        (HIGH, 'High'),
        (CRITICAL, 'Critical'),
    ]

    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, default='')

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        db_index=True,   # filtered often
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default=MEDIUM,
    )

    # ForeignKey: many tasks → one project
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='tasks'   # project.tasks.all()
    )

    # ForeignKey: many tasks → one assignee
    # null=True + blank=True: task can be unassigned
    # on_delete=SET_NULL: if user deleted, task stays but assignee becomes null
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks'
    )

    # Who created this task
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tasks'
    )

    # ManyToMany: a task can have many tags, a tag can be on many tasks
    tags = models.ManyToManyField(Tag, blank=True, related_name='tasks')

    due_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Attach our custom manager
    objects = TaskManager()

    def __str__(self):
        return f'{self.title} [{self.status}]'

    # @property: call as task.is_overdue (no brackets) — reads like an attribute
    @property
    def is_overdue(self):
        from django.utils import timezone
        if self.due_date and self.status not in [self.DONE]:
            return timezone.now() > self.due_date
        return False

    class Meta:
        db_table = 'tasks'
        ordering = ['-created_at']
        indexes = [
            # Composite index: queries like filter(project=X, status=Y) are fast
            models.Index(fields=['project', 'status']),
            models.Index(fields=['assigned_to', 'status']),
        ]


# ─── Comment model ────────────────────────────────────────────────────────────

class Comment(models.Model):
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='comments'   # task.comments.all()
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Comment by {self.author.username} on Task#{self.task.id}'

    class Meta:
        db_table = 'comments'
        ordering = ['created_at']  # oldest first (chat-like order)