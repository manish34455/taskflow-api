from rest_framework import serializers
from .models import Project, Task, Tag, Comment
from accounts.models import User


# ─── Tag Serializer ───────────────────────────────────────────────────────────
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'color']


# ─── Simple User Serializer (used inside other serializers) ───────────────────
# We don't want to expose password or sensitive fields
# This is a "nested serializer" — used inside Project and Task
class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role']


# ─── Comment Serializer ───────────────────────────────────────────────────────
class CommentSerializer(serializers.ModelSerializer):
    # nested serializer — shows full author details not just ID
    author = SimpleUserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'author', 'body', 'created_at']
        read_only_fields = ['id', 'author', 'created_at']


# ─── Project Serializer ───────────────────────────────────────────────────────
class ProjectSerializer(serializers.ModelSerializer):
    # read_only nested: shows owner details in GET response
    owner = SimpleUserSerializer(read_only=True)

    # write_only: accepts member IDs when creating/updating
    member_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.all(),
        source='members',
        write_only=True,
        required=False
    )
    # read_only nested: shows member details in GET response
    members = SimpleUserSerializer(many=True, read_only=True)

    # extra computed field — not in model, calculated here
    task_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'status',
            'owner', 'members', 'member_ids',
            'task_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']

    def get_task_count(self, obj):
        # SerializerMethodField calls get_<fieldname>
        # obj = the Project instance
        return obj.tasks.count()

    def create(self, validated_data):
        # owner is set from the request user, not from input
        request = self.context['request']
        members = validated_data.pop('members', [])
        project = Project.objects.create(
            owner=request.user,
            **validated_data
        )
        project.members.set(members)
        return project


# ─── Task Serializer ─────────────────────────────────────────────────────────
class TaskSerializer(serializers.ModelSerializer):
    # nested read-only fields
    assigned_to = SimpleUserSerializer(read_only=True)
    created_by = SimpleUserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    # write-only fields to accept IDs
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='assigned_to',
        write_only=True,
        required=False,
        allow_null=True
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        source='tags',
        write_only=True,
        required=False
    )

    # computed field using @property on the model
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'status', 'priority',
            'project', 'assigned_to', 'assigned_to_id',
            'created_by', 'tags', 'tag_ids',
            'comments', 'is_overdue', 'due_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        request = self.context['request']
        tags = validated_data.pop('tags', [])
        task = Task.objects.create(
            created_by=request.user,
            **validated_data
        )
        task.tags.set(tags)
        return task