from django.urls import path
from . import views

urlpatterns = [
    path('verify-user/', views.verify_user, name='verify_user'),
    path('user-info/', views.user_info, name='user_info'),
    path('tasks/<int:task_id>/', views.get_task_detail, name='get_task_detail'),
    path('tasks/', views.get_tasks, name='get_tasks'),
    path('tasks/<int:task_id>/status/', views.update_task_status, name='update_task_status'),
    path('submit-progress/', views.submit_task_progress, name='submit_progress'),
    path('tasks/<int:task_id>/stats/', views.task_stats, name='task_stats'),
    path('webhook/broadcast/', views.broadcast_webhook, name='broadcast_webhook'),
    path('webhook/broadcast-status/', views.broadcast_status_webhook, name='broadcast_status_webhook'),
    path('statistics/<str:period>/', views.get_statistics, name='get_statistics'),
    path('broadcast/', views.broadcast_message, name='broadcast_message'),
    path('districts/', views.get_districts, name='get_districts'),
    path('mahallas/', views.get_mahallas, name='get_mahallas'),
    path('users/telegram-ids/', views.get_telegram_ids, name='get_telegram_ids'),
    path('grade-task/', views.grade_task, name='grade_task'),
]




