from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import User, Task, TaskProgress, TaskFile, TaskStatus, Mahallah, BroadcastMessage, District
from .serializers import UserSerializer, TaskSerializer, TaskDetailSerializer, MahallahSerializer, DistrictSerializer
from django.db.models import Count, Q, Avg, F
from datetime import timedelta
import datetime

@api_view(['GET'])
def user_info(request):
    telegram_id = request.query_params.get('telegram_id')
    if not telegram_id:
        return Response({'message': 'Telegram ID is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(telegram_id=telegram_id)
        serializer = UserSerializer(user)
        return Response({'user': serializer.data})
    except User.DoesNotExist:
        return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def verify_user(request):
    phone = request.data.get('phone')
    jshir = request.data.get('jshir')
    telegram_id = request.data.get('telegram_id')

    if not all([phone, jshir, telegram_id]):
        return Response({'message': 'Phone, JSHIR, and Telegram ID are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(phone=phone, jshir=jshir)
        user.telegram_id = telegram_id
        user.save()

        serializer = UserSerializer(user)
        return Response({'user': serializer.data})
    except User.DoesNotExist:
        return Response({'message': 'User not found with the provided phone and JSHIR'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def user_tasks(request):
    telegram_id = request.query_params.get('telegram_id')
    if not telegram_id:
        return Response({'message': 'Telegram ID is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(telegram_id=telegram_id)

        tasks = Task.objects.filter(mahallahs=user.mahallah)

        for task in tasks:
            latest_status = task.status_history.order_by('-created_at').first()
            if latest_status:
                task.status = latest_status.status

        serializer = TaskSerializer(tasks, many=True)
        return Response({'tasks': serializer.data})
    except User.DoesNotExist:
        return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def task_detail(request, task_id):
    try:
        task = Task.objects.get(pk=task_id)

        latest_status = task.status_history.order_by('-created_at').first()
        if latest_status:
            task.status = latest_status.status

        serializer = TaskDetailSerializer(task, context={'request': request})
        return Response({'task': serializer.data})
    except Task.DoesNotExist:
        return Response({'message': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['PATCH'])
def update_task_status(request, task_id):
    telegram_id = request.data.get('telegram_id')
    new_status = request.data.get('status')
    rejection_reason = request.data.get('rejection_reason')

    if not all([telegram_id, new_status]):
        return Response({'message': 'Telegram ID and status are required'}, status=status.HTTP_400_BAD_REQUEST)

    if new_status not in [status for status, _ in TaskStatus._meta.get_field('status').choices]:
        return Response({'message': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(telegram_id=telegram_id)
        task = Task.objects.get(pk=task_id)

        if user.mahallah not in task.mahallahs.all():
            return Response({'message': 'Task not assigned to your mahallah'}, status=status.HTTP_403_FORBIDDEN)

        TaskStatus.objects.create(
            task=task,
            user=user,
            status=new_status,
            rejection_reason=rejection_reason if new_status == 'rejected' else None
        )

        task.status = new_status
        task.save()

        return Response({'message': 'Task status updated successfully'})
    except User.DoesNotExist:
        return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Task.DoesNotExist:
        return Response({'message': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def submit_task_progress(request):
    task_id = request.data.get('task_id')
    telegram_id = request.data.get('telegram_id')
    description = request.data.get('description')
    
    if not all([task_id, telegram_id, description]):
        return Response({'message': 'Task ID, Telegram ID, and description are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(telegram_id=telegram_id)
        task = Task.objects.get(pk=task_id)

        if user.mahallah not in task.mahallahs.all():
            return Response({'message': 'Task not assigned to your mahallah'}, status=status.HTTP_403_FORBIDDEN)

        progress = TaskProgress.objects.create(
            task=task,
            user=user,
            description=description
        )

        file_count = 0
        for key in request.FILES:
            if key.startswith('file_'):
                file = request.FILES[key]
                # Create TaskFile without task_progress field since it doesn't exist
                TaskFile.objects.create(
                    task=task,
                    file=file,
                    file_name=file.name,
                    file_type=file.content_type
                )
                file_count += 1

        return Response({
            'message': 'Task progress submitted successfully',
            'files_processed': file_count
        })
    except User.DoesNotExist:
        return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Task.DoesNotExist:
        return Response({'message': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def task_stats(request, task_id):
    try:
        task = Task.objects.get(pk=task_id)

        mahallahs = task.mahallahs.all()

        mahallah_stats = []
        total_users = 0
        completed_users = 0

        for mahallah in mahallahs:
            users_count = User.objects.filter(mahallah=mahallah).count()
            completed_count = TaskStatus.objects.filter(
                task=task,
                status='completed',
                user__mahallah=mahallah
            ).values('user').distinct().count()

            mahallah_stats.append({
                'id': mahallah.id,
                'name': mahalla.name,
                'total': users_count,
                'completed': completed_count
            })

            total_users += users_count
            completed_users += completed_count

        pending_users = total_users - completed_users

        return Response({
            'stats': {
                'total_users': total_users,
                'completed_users': completed_users,
                'pending_users': pending_users,
                'mahallah_stats': mahallah_stats
            }
        })
    except Task.DoesNotExist:
        return Response({'message': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def broadcast_webhook(request):
    title = request.data.get('title')
    message = request.data.get('message')
    telegram_ids = request.data.get('telegram_ids', [])
    sender_id = request.data.get('sender_id')

    if not all([title, message, telegram_ids, sender_id]):
        return Response({'message': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        sender = User.objects.get(telegram_id=sender_id)

        broadcast = BroadcastMessage.objects.create(
            title=title,
            message=message,
            created_by=sender,
            recipients_count=len(telegram_ids)
        )

        return Response({
            'message': 'Broadcast received successfully',
            'broadcast_id': broadcast.id
        })
    except User.DoesNotExist:
        return Response({'message': 'Sender not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def broadcast_status_webhook(request):
    broadcast_id = request.data.get('broadcast_id')
    delivered_count = request.data.get('delivered_count', 0)
    read_count = request.data.get('read_count', 0)

    if not broadcast_id:
        return Response({'message': 'Broadcast ID is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        broadcast = BroadcastMessage.objects.get(pk=broadcast_id)
        broadcast.delivered_count = delivered_count
        broadcast.read_count = read_count
        broadcast.save()

        return Response({'message': 'Broadcast status updated successfully'})
    except BroadcastMessage.DoesNotExist:
        return Response({'message': 'Broadcast not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def broadcast_message(request):
    title = request.data.get('title')
    message = request.data.get('message')
    target_type = request.data.get('target_type')
    target_id = request.data.get('target_id')
    admin_id = request.data.get('admin_id')
    
    if not title or not message or not target_type:
        return Response({
            'success': False,
            'message': 'Missing required fields'
        }, status=400)
    
    target_users = []
    
    if target_type == 'all':
        target_users = User.objects.filter(is_active=True, telegram_id__isnull=False)
    elif target_type == 'district' and target_id:
        target_users = User.objects.filter(
            is_active=True,
            telegram_id__isnull=False,
            mahallah__district_id=target_id
        )
    elif target_type == 'mahalla' and target_id:
        target_users = User.objects.filter(
            is_active=True,
            telegram_id__isnull=False,
            mahallah_id=target_id
        )
    else:
        return Response({
            'success': False,
            'message': 'Invalid target type or missing target ID'
        }, status=400)
    
    admin_user = None
    if admin_id:
        try:
            admin_user = User.objects.get(telegram_id=admin_id)
        except User.DoesNotExist:
            pass
    
    broadcast = BroadcastMessage.objects.create(
        title=title,
        message=message,
        created_by=admin_user,
        recipients_count=len(target_users)
    )
    
    telegram_ids = []
    for user in target_users:
        if user.telegram_id:
            telegram_ids.append(user.telegram_id)
    
    return Response({
        'success': True,
        'broadcast_id': broadcast.id,
        'sent_count': len(telegram_ids),
        'telegram_ids': telegram_ids
    })

@api_view(['GET'])
def get_statistics(request, period):
    today = timezone.now().date()

    if period == 'daily':
        start_date = today
        end_date = today
    elif period == 'monthly':
        start_date = today.replace(day=1)
        if today.month == 12:
            end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    else:
        start_date = None
        end_date = None

    task_filters = {}
    if start_date and end_date:
        task_filters['created_at__date__gte'] = start_date
        task_filters['created_at__date__lte'] = end_date

    completed_tasks = Task.objects.filter(status='completed', **task_filters).count()
    active_tasks = Task.objects.filter(status='active', **task_filters).count()
    rejected_tasks = Task.objects.filter(status='rejected', **task_filters).count()

    active_users = User.objects.filter(is_active=True).count()

    mahallas = Mahallah.objects.all()
    top_mahallas = []

    for mahalla in mahallas:
        mahalla_tasks = Task.objects.filter(mahallahs=mahalla, **task_filters)
        total_tasks = mahalla_tasks.count()
        completed_mahalla_tasks = mahalla_tasks.filter(status='completed').count()

        if total_tasks > 0:
            completion_rate = (completed_mahalla_tasks / total_tasks) * 100
        else:
            completion_rate = 0

        top_mahallas.append({
            'id': mahalla.id,
            'name': mahalla.name,
            'completion_rate': round(completion_rate, 1)
        })

    top_mahallas = sorted(top_mahallas, key=lambda x: x['completion_rate'], reverse=True)

    districts = District.objects.all()
    district_stats = []

    for district in districts:
        district_tasks = Task.objects.filter(mahallahs__district=district, **task_filters)
        total_tasks = district_tasks.count()
        completed_district_tasks = district_tasks.filter(status='completed').count()

        if total_tasks > 0:
            completion_rate = (completed_district_tasks / total_tasks) * 100
        else:
            completion_rate = 0

        district_stats.append({
            'id': district.id,
            'name': district.name,
            'completion_rate': round(completion_rate, 1)
        })

    data = {
        'completed_tasks': completed_tasks,
        'active_tasks': active_tasks,
        'rejected_tasks': rejected_tasks,
        'active_users': active_users,
        'top_mahallas': top_mahallas,
        'district_stats': district_stats
    }

    if period == 'monthly':
        daily_stats = []
        current_date = start_date

        while current_date <= end_date:
            day_completed = Task.objects.filter(
                status='completed',
                updated_at__date=current_date
            ).count()

            daily_stats.append({
                'date': current_date.strftime('%d.%m.%Y'),
                'completed_tasks': day_completed
            })

            current_date += timedelta(days=1)

        data['daily_stats'] = daily_stats

    return Response(data)

@api_view(['GET'])
def get_districts(request):
    districts = District.objects.all()
    serializer = DistrictSerializer(districts, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_mahallas(request):
    mahallas = Mahallah.objects.all()
    serializer = MahallahSerializer(mahallas, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_telegram_ids(request):
    users = User.objects.filter(telegram_id__isnull=False)
    telegram_ids = users.values_list('telegram_id', flat=True)
    return Response({'telegram_ids': list(telegram_ids)})

@api_view(['POST'])
def grade_task(request):
    task_id = request.data.get('task_id')
    percentage = request.data.get('percentage')
    status = request.data.get('status')
    admin_id = request.data.get('admin_id')
    
    if not task_id or percentage is None or not status:
        return Response({
            'success': False,
            'message': 'Missing required fields'
        }, status=400)
    
    try:
        percentage = int(percentage)
        if percentage < 0 or percentage > 100:
            return Response({
                'success': False,
                'message': 'Percentage must be between 0 and 100'
            }, status=400)
    except (ValueError, TypeError):
        return Response({
            'success': False,
            'message': 'Invalid percentage value'
        }, status=400)
    
    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Task not found'
        }, status=404)
    
    admin_user = None
    if admin_id:
        try:
            admin_user = User.objects.get(telegram_id=admin_id)
        except User.DoesNotExist:
            pass
    
    if not admin_user:
        admin_user = User.objects.filter(is_superuser=True).first()
    
    task_status = 'active'
    if status == 'green':
        task_status = 'completed'
    elif status == 'red':
        task_status = 'rejected'
    
    TaskStatus.objects.create(
        task=task,
        user=admin_user,
        status=task_status,
        rejection_reason=f"Graded with {percentage}% completion" if task_status == 'rejected' else None
    )
    
    for mahalla in task.mahallahs.all():
        if percentage >= 85:
            mahalla.status = 'green'
        elif percentage >= 55:
            mahalla.status = 'yellow'
        else:
            mahalla.status = 'red'
        mahalla.save()
    
    return Response({
        'success': True,
        'message': 'Task graded successfully',
        'task_id': task.id,
        'percentage': percentage,
        'status': status
    })

@api_view(['GET'])
def get_task_detail(request, task_id):
    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Task not found'
        }, status=404)
    
    # Get all files associated with this task
    files = []
    task_files = TaskFile.objects.filter(task=task)
    for file in task_files:
        files.append({
            'id': file.id,
            'name': file.file_name,
            'url': request.build_absolute_uri(file.file.url) if file.file else None,
            'file_type': file.file_type,
            'uploaded_at': file.uploaded_at.strftime('%d.%m.%Y %H:%M'),
            'uploaded_by': 'Unknown'  # Since we don't have user info in TaskFile
        })
    
    mahallas = []
    for mahalla in task.mahallahs.all():
        mahallas.append({
            'id': mahalla.id,
            'name': mahalla.name,
            'district_name': mahalla.district.name if mahalla.district else None,
            'status': mahalla.status
        })
    
    submissions = []
    for progress in task.progress.all():
        # We can't directly get files for this progress, so we'll leave it empty
        submissions.append({
            'id': progress.id,
            'user': {
                'id': progress.user.id,
                'name': progress.user.full_name or progress.user.username,
                'telegram_id': progress.user.telegram_id
            },
            'description': progress.description,
            'files': [],  # Empty list since we can't link files to progress
            'created_at': progress.created_at.strftime('%d.%m.%Y %H:%M')
        })
    
    latest_status = task.status_history.order_by('-created_at').first()
    status_info = None
    if latest_status:
        status_info = {
            'status': latest_status.status,
            'updated_by': {
                'id': latest_status.user.id,
                'name': latest_status.user.full_name or latest_status.user.username
            },
            'updated_at': latest_status.created_at.strftime('%d.%m.%Y %H:%M'),
            'rejection_reason': latest_status.rejection_reason
        }
    
    completion_rate = task.get_completion_rate()
    
    task_data = {
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'status': task.status,
        'completion_percentage': int(completion_rate),
        'deadline': task.deadline.strftime('%d.%m.%Y') if task.deadline else None,
        'created_at': task.created_at.strftime('%d.%m.%Y %H:%M'),
        'updated_at': task.updated_at.strftime('%d.%m.%Y %H:%M'),
        'files': files,
        'mahallas': mahallas,
        'submissions': submissions,
        'status_info': status_info
    }
    
    return Response({
        'success': True,
        'task': task_data
    })

@api_view(['GET'])
def get_tasks(request):
    from api.models import Task, User
    
    user_id = request.GET.get('user_id')
    mahalla_id = request.GET.get('mahalla_id')
    district_id = request.GET.get('district_id')
    status = request.GET.get('status')
    
    tasks_query = Task.objects.all()
    
    if user_id:
        try:
            user = User.objects.get(telegram_id=user_id)
            tasks_query = tasks_query.filter(mahallahs=user.mahallah)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=404)
    
    if mahalla_id:
        tasks_query = tasks_query.filter(mahallahs__id=mahalla_id)
    
    if district_id:
        tasks_query = tasks_query.filter(mahallahs__district_id=district_id)
    
    if status:
        tasks_query = tasks_query.filter(status=status)
    
    tasks = []
    for task in tasks_query.distinct():
        # Use TaskFile model to count files
        files_count = TaskFile.objects.filter(task=task).count()
        
        mahallas = []
        for mahalla in task.mahallahs.all():
            mahallas.append({
                'id': mahalla.id,
                'name': mahalla.name
            })
        
        tasks.append({
            'id': task.id,
            'title': task.title,
            'status': task.status,
            'completion_percentage': task.completion_percentage if hasattr(task, 'completion_percentage') else 0,
            'deadline': task.deadline.strftime('%d.%m.%Y') if task.deadline else None,
            'created_at': task.created_at.strftime('%d.%m.%Y'),
            'files_count': files_count,
            'mahallas': mahallas
        })
    
    return Response({
        'success': True,
        'tasks': tasks
    })


def simple_page(request):
    response_text = """
    <h1>Welcome to the Homepage</h1>
    <p>Here are the available pages:</p>
    <ul>
        <li><a href="/admin/">Admin Panel</a></li>
        <li><a href="/api/">API</a></li>
    </ul>
    """
    return HttpResponse(response_text)
