from rest_framework import serializers
from .models import User, Task, TaskProgress, TaskFile, TaskStatus, Mahallah, District

class UserSerializer(serializers.ModelSerializer):
    job_title_name = serializers.CharField(source='job_title.name', read_only=True)
    mahalla_name = serializers.CharField(source='mahallah.name', read_only=True)
    tuman_name = serializers.CharField(source='mahallah.district.name', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'full_name', 'phone', 'telegram_id', 'job_title', 'job_title_name',
                  'mahallah', 'mahalla_name', 'tuman_name')

class TaskSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    completed_at = serializers.SerializerMethodField()
    rejected_at = serializers.SerializerMethodField()
    rejection_reason = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ('id', 'title', 'description', 'deadline', 'status',
                  'created_at', 'updated_at', 'completed_at', 'rejected_at', 'rejection_reason')

    def get_completed_at(self, obj):
        completed_status = obj.status_history.filter(status='completed').order_by('-created_at').first()
        return completed_status.created_at if completed_status else None

    def get_rejected_at(self, obj):
        rejected_status = obj.status_history.filter(status='rejected').order_by('-created_at').first()
        return rejected_status.created_at if rejected_status else None

    def get_rejection_reason(self, obj):
        rejected_status = obj.status_history.filter(status='rejected').order_by('-created_at').first()
        return rejected_status.rejection_reason if rejected_status else None

class TaskFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = TaskFile
        fields = ('id', 'file_name', 'file_type', 'uploaded_at', 'file_url')

    def get_file_url(self, obj):
        request = self.context.get('request')
        if request and obj.file:
            return request.build_absolute_uri(obj.file.url)
        return None

class TaskProgressSerializer(serializers.ModelSerializer):
    files = TaskFileSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = TaskProgress
        fields = ('id', 'description', 'created_at', 'user_name', 'files')

class TaskDetailSerializer(TaskSerializer):
    progress = TaskProgressSerializer(many=True, read_only=True)

    class Meta(TaskSerializer.Meta):
        fields = TaskSerializer.Meta.fields + ('progress',)

class MahallahSerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(source='district.name', read_only=True)

    class Meta:
        model = Mahallah
        fields = ('id', 'name', 'district', 'district_name')

class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ['id', 'name', 'region']
