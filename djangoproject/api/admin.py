from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.urls import path
from django.shortcuts import render, redirect
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
import csv
import xlsxwriter
from io import BytesIO
import requests
import json
from .models import (
    Region, District, Mahallah, JobTitle, EmployeeType,
    User, DeviceSession, Task, TaskProgress, TaskFile, TaskStatus, BroadcastMessage,
    MAHALLA_STATUS_CHOICES, TaskSubmission, SubmissionFile, TaskGrade
)



class CustomAdminSite(admin.AdminSite):
    site_header = 'Oltinsoy tuman hokimligi'
    site_title = 'Oltinsoy tuman hokimligi'
    index_title = 'Boshqaruv paneli'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(self.dashboard_view), name='dashboard'),
            path('api/dashboard/stats/', self.admin_view(self.dashboard_stats_api), name='dashboard_stats_api'),
            path('api/dashboard/mahalla-stats/<int:mahalla_id>/', self.admin_view(self.mahalla_stats_api), name='mahalla_stats_api'),
            path('export/tasks/', self.admin_view(self.export_tasks), name='export_tasks'),
            path('export/users/', self.admin_view(self.export_users), name='export_users'),
            path('export/mahallas/', self.admin_view(self.export_mahallas), name='export_mahallas'),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        mahallahs = Mahallah.objects.all()

        context = {
            'title': 'Statistika paneli',
            'mahallahs': mahallahs,
        }
        return render(request, 'admin/dashboard.html', context)

    def dashboard_stats_api(self, request):
        days = int(request.GET.get('days', 30))

        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        tasks = Task.objects.filter(created_at__gte=start_date)
        total_tasks = tasks.count()

        mahalla_stats = []
        for mahalla in Mahallah.objects.all():
            mahalla_tasks = tasks.filter(mahallahs=mahalla)
            total = mahalla_tasks.count()
            if total == 0:
                continue

            completed = mahalla_tasks.filter(status='completed').count()
            active = mahalla_tasks.filter(status='active').count()
            rejected = mahalla_tasks.filter(status='rejected').count()

            completion_rate = (completed / total) * 100 if total > 0 else 0

            mahalla_stats.append({
                'id': mahalla.id,
                'name': mahalla.name,
                'district': mahalla.district.name,
                'status': mahalla.status,
                'total': total,
                'completed': completed,
                'active': active,
                'rejected': rejected,
                'completion_rate': round(completion_rate, 1)
            })

        mahalla_stats.sort(key=lambda x: x['completion_rate'], reverse=True)

        daily_stats = []
        current_date = start_date.date()
        end_date_date = end_date.date()

        while current_date <= end_date_date:
            next_date = current_date + timedelta(days=1)

            day_tasks = tasks.filter(
                created_at__date__gte=current_date,
                created_at__date__lt=next_date
            )

            total = day_tasks.count()
            completed = day_tasks.filter(status='completed').count()
            active = day_tasks.filter(status='active').count()
            rejected = day_tasks.filter(status='rejected').count()

            daily_stats.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'date_display': current_date.strftime('%d/%m'),
                'total': total,
                'completed': completed,
                'active': active,
                'rejected': rejected
            })

            current_date = next_date

        return JsonResponse({
            'total_tasks': total_tasks,
            'completed_tasks': tasks.filter(status='completed').count(),
            'active_tasks': tasks.filter(status='active').count(),
            'rejected_tasks': tasks.filter(status='rejected').count(),
            'mahalla_stats': mahalla_stats,
            'daily_stats': daily_stats
        })

    def mahalla_stats_api(self, request, mahalla_id):
        try:
            mahalla = Mahallah.objects.get(pk=mahalla_id)

            monthly_stats = mahalla.get_monthly_stats(6)
            daily_stats = mahalla.get_daily_stats(30)

            users = User.objects.filter(mahallah=mahalla)
            user_stats = []

            for user in users:
                tasks = Task.objects.filter(mahallahs=mahalla)
                total = tasks.count()
                if total == 0:
                    continue

                completed = TaskStatus.objects.filter(
                    task__in=tasks,
                    user=user,
                    status='completed'
                ).count()

                completion_rate = (completed / total) * 100 if total > 0 else 0

                user_stats.append({
                    'id': user.id,
                    'name': user.full_name or user.username,
                    'job_title': user.job_title.name if user.job_title else '',
                    'total': total,
                    'completed': completed,
                    'completion_rate': round(completion_rate, 1)
                })

            return JsonResponse({
                'mahalla': {
                    'id': mahalla.id,
                    'name': mahalla.name,
                    'district': mahalla.district.name,
                    'status': mahalla.status
                },
                'monthly_stats': monthly_stats,
                'daily_stats': daily_stats,
                'user_stats': user_stats
            })
        except Mahallah.DoesNotExist:
            return JsonResponse({'error': 'Mahalla not found'}, status=404)

    def broadcast_view(self, request):
        broadcasts = BroadcastMessage.objects.all()

        context = {
            'title': 'Ommaviy xabar yuborish',
            'broadcasts': broadcasts,
        }
        return render(request, 'admin/broadcast.html', context)

    def send_broadcast(self, request):
        if request.method == 'POST':
            title = request.POST.get('title')
            message = request.POST.get('message')
            target_type = request.POST.get('target_type')

            if not title or not message:
                messages.error(request, 'Sarlavha va xabar matni to\'ldirilishi shart')
                return redirect('admin:broadcast')

            telegram_ids = []

            if target_type == 'all':
                users = User.objects.filter(telegram_id__isnull=False)
            elif target_type == 'mahalla':
                mahalla_id = request.POST.get('mahalla_id')
                if not mahalla_id:
                    messages.error(request, 'Mahalla tanlanishi shart')
                    return redirect('admin:broadcast')
                users = User.objects.filter(mahallah_id=mahalla_id, telegram_id__isnull=False)
            elif target_type == 'district':
                district_id = request.POST.get('district_id')
                if not district_id:
                    messages.error(request, 'Tuman tanlanishi shart')
                    return redirect('admin:broadcast')
                users = User.objects.filter(mahallah__district_id=district_id, telegram_id__isnull=False)
            else:
                messages.error(request, 'Noto\'g\'ri qabul qiluvchilar turi')
                return redirect('admin:broadcast')

            telegram_ids = list(users.values_list('telegram_id', flat=True))

            if not telegram_ids:
                messages.error(request, 'Telegram ID ga ega foydalanuvchilar topilmadi')
                return redirect('admin:broadcast')

            broadcast = BroadcastMessage.objects.create(
                title=title,
                message=message,
                created_by=request.user,
                recipients_count=len(telegram_ids)
            )

            try:
                webhook_url = request.build_absolute_uri('/').rstrip('/') + '/api/webhook/broadcast'

                payload = {
                    'broadcast_id': broadcast.id,
                    'title': title,
                    'message': message,
                    'telegram_ids': telegram_ids
                }

                response = requests.post(
                    webhook_url,
                    json=payload,
                    timeout=10
                )

                if response.status_code != 200:
                    messages.error(request, f'Xabar yuborishda xatolik: {response.text}')
                else:
                    messages.success(request, f'Xabar {len(telegram_ids)} ta foydalanuvchiga yuborildi')
            except Exception as e:
                messages.error(request, f'Xatolik yuz berdi: {str(e)}')

            return redirect('admin:broadcast')

        return redirect('admin:broadcast')

    def export_tasks(self, request):
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="topshiriqlar.xlsx"'

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Topshiriqlar')

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#3498db',
            'color': 'white',
            'border': 1
        })

        date_format = workbook.add_format({'num_format': 'dd/mm/yyyy hh:mm'})

        headers = [
            'ID', 'Sarlavha', 'Tavsif', 'Muddat', 'Holat',
            'Yaratilgan sana', 'Mahallalar', 'Bajarilish %'
        ]

        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        tasks = Task.objects.all().order_by('-created_at')

        for row, task in enumerate(tasks, start=1):
            mahallas = ', '.join([m.name for m in task.mahallahs.all()])
            completion_rate = task.get_completion_rate()

            worksheet.write(row, 0, task.id)
            worksheet.write(row, 1, task.title)
            worksheet.write(row, 2, task.description)
            if task.deadline:
                worksheet.write_datetime(row, 3, task.deadline.replace(tzinfo=None), date_format)
            else:
                worksheet.write(row, 3, 'Belgilanmagan')
            worksheet.write(row, 4, dict(TASK_STATUS_CHOICES).get(task.status))
            worksheet.write_datetime(row, 5, task.created_at.replace(tzinfo=None), date_format)
            worksheet.write(row, 6, mahallas)
            worksheet.write(row, 7, f"{completion_rate:.1f}%")

        worksheet.set_column(0, 0, 5)
        worksheet.set_column(1, 1, 30)
        worksheet.set_column(2, 2, 40)
        worksheet.set_column(3, 5, 20)
        worksheet.set_column(6, 6, 30)
        worksheet.set_column(7, 7, 15)

        workbook.close()
        output.seek(0)

        response.write(output.read())
        return response

    def export_users(self, request):
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="foydalanuvchilar.xlsx"'

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Foydalanuvchilar')

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#3498db',
            'color': 'white',
            'border': 1
        })

        headers = [
            'ID', 'Foydalanuvchi nomi', 'To\'liq ism', 'Telefon', 'JSHIR',
            'Telegram ID', 'Lavozim', 'Xodim turi', 'Mahalla', 'Tuman'
        ]

        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        users = User.objects.all().order_by('username')

        for row, user in enumerate(users, start=1):
            worksheet.write(row, 0, user.id)
            worksheet.write(row, 1, user.username)
            worksheet.write(row, 2, user.full_name)
            worksheet.write(row, 3, user.phone)
            worksheet.write(row, 4, user.jshir)
            worksheet.write(row, 5, user.telegram_id if user.telegram_id else '')
            worksheet.write(row, 6, user.job_title.name if user.job_title else '')
            worksheet.write(row, 7, user.employee_type.name if user.employee_type else '')
            worksheet.write(row, 8, user.mahallah.name if user.mahallah else '')
            worksheet.write(row, 9, user.mahallah.district.name if user.mahallah else '')

        worksheet.set_column(0, 0, 5)
        worksheet.set_column(1, 2, 25)
        worksheet.set_column(3, 4, 15)
        worksheet.set_column(5, 5, 15)
        worksheet.set_column(6, 9, 20)

        workbook.close()
        output.seek(0)

        response.write(output.read())
        return response

    def export_mahallas(self, request):
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="mahallalar.xlsx"'

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Mahallalar')

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#3498db',
            'color': 'white',
            'border': 1
        })

        headers = [
            'ID', 'Nomi', 'Tuman', 'Viloyat', 'Holati',
            'Topshiriqlar soni', 'Bajarilgan', 'Bajarilish %'
        ]

        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        mahallas = Mahallah.objects.all().order_by('district__region__name', 'district__name', 'name')

        for row, mahalla in enumerate(mahallas, start=1):
            tasks = Task.objects.filter(mahallahs=mahalla)
            total_tasks = tasks.count()
            completed_tasks = tasks.filter(status='completed').count()
            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

            worksheet.write(row, 0, mahalla.id)
            worksheet.write(row, 1, mahalla.name)
            worksheet.write(row, 2, mahalla.district.name)
            worksheet.write(row, 3, mahalla.district.region.name)
            worksheet.write(row, 4, dict(MAHALLA_STATUS_CHOICES).get(mahalla.status))
            worksheet.write(row, 5, total_tasks)
            worksheet.write(row, 6, completed_tasks)
            worksheet.write(row, 7, f"{completion_rate:.1f}%")

        worksheet.set_column(0, 0, 5)
        worksheet.set_column(1, 3, 25)
        worksheet.set_column(4, 4, 15)
        worksheet.set_column(5, 6, 15)
        worksheet.set_column(7, 7, 15)

        workbook.close()
        output.seek(0)

        response.write(output.read())
        return response

admin_site = CustomAdminSite(name='admin')

@admin.register(Region, site=admin_site)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(District, site=admin_site)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('name', 'region')
    list_filter = ('region',)
    search_fields = ('name', 'region__name')

class MahallaStatusFilter(admin.SimpleListFilter):
    title = 'Holat'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return MAHALLA_STATUS_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset

@admin.register(Mahallah, site=admin_site)
class MahallahAdmin(admin.ModelAdmin):
    list_display = ('name', 'district', 'status', 'get_task_count', 'get_completion_rate')
    list_filter = ('district__region', 'district', MahallaStatusFilter)
    search_fields = ('name', 'district__name', 'district__region__name')
    actions = ['mark_as_green', 'mark_as_yellow', 'mark_as_red']

    def get_task_count(self, obj):
        return obj.tasks.count()
    get_task_count.short_description = 'Topshiriqlar soni'

    def get_completion_rate(self, obj):
        return f"{obj.get_completion_rate():.1f}%"
    get_completion_rate.short_description = 'Bajarilish darajasi'

    def mark_as_green(self, request, queryset):
        queryset.update(status='green')
    mark_as_green.short_description = 'Yashil holatga o\'tkazish'

    def mark_as_yellow(self, request, queryset):
        queryset.update(status='yellow')
    mark_as_yellow.short_description = 'Sariq holatga o\'tkazish'

    def mark_as_red(self, request, queryset):
        queryset.update(status='red')
    mark_as_red.short_description = 'Qizil holatga o\'tkazish'

@admin.register(JobTitle, site=admin_site)
class JobTitleAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(EmployeeType, site=admin_site)
class EmployeeTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class DeviceSessionInline(admin.TabularInline):
    model = DeviceSession
    extra = 0

@admin.register(User, site=admin_site)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'full_name', 'phone', 'telegram_id', 'job_title', 'mahallah', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'job_title', 'employee_type', 'mahallah__district')
    search_fields = ('username', 'full_name', 'phone', 'jshir', 'telegram_id')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Shaxsiy ma\'lumotlar', {'fields': ('full_name', 'phone', 'jshir', 'telegram_id', 'email')}),
        ('Ish ma\'lumotlari', {'fields': ('job_title', 'employee_type', 'mahallah')}),
        ('Huquqlar', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Muhim sanalar', {'fields': ('last_login', 'date_joined')}),
    )
    inlines = [DeviceSessionInline]
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'full_name', 'phone', 'jshir', 'telegram_id', 'job_title', 'employee_type', 'mahallah'),
        }),
    )

class TaskFileInline(admin.TabularInline):
    model = TaskFile
    extra = 1

@admin.register(TaskProgress, site=admin_site)
class TaskProgressAdmin(admin.ModelAdmin):
    list_display = ('task', 'user', 'created_at')
    list_filter = ('task', 'user', 'created_at')
    search_fields = ('task__title', 'user__full_name', 'description')

@admin.register(TaskStatus, site=admin_site)
class TaskStatusAdmin(admin.ModelAdmin):
    list_display = ('task', 'user', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('task__title', 'user__full_name', 'rejection_reason')

class TaskProgressInline(admin.TabularInline):
    model = TaskProgress
    extra = 0

class TaskStatusInline(admin.TabularInline):
    model = TaskStatus
    extra = 0

@admin.register(Task, site=admin_site)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'completion_percentage')
    list_filter = ('status', 'created_at', 'deadline')
    search_fields = ('title', 'description')
    date_hierarchy = 'created_at'
    filter_horizontal = ('mahallahs',)
    inlines = [TaskFileInline, TaskProgressInline, TaskStatusInline]
    actions = ['mark_as_completed', 'mark_as_rejected', 'mark_mahallas_green', 'mark_mahallas_yellow']

    def get_completion_rate(self, obj):
        return f"{obj.get_completion_rate():.1f}%"
    get_completion_rate.short_description = 'Bajarilish darajasi'

    def mark_as_completed(self, request, queryset):
        for task in queryset:
            TaskStatus.objects.create(
                task=task,
                user=request.user,
                status='completed'
            )
    mark_as_completed.short_description = 'Bajarilgan deb belgilash'

    def mark_as_rejected(self, request, queryset):
        for task in queryset:
            TaskStatus.objects.create(
                task=task,
                user=request.user,
                status='rejected'
            )
    mark_as_rejected.short_description = 'Rad etilgan deb belgilash'

    def mark_mahallas_green(self, request, queryset):
        for task in queryset:
            task.mahallahs.update(status='green')
    mark_mahallas_green.short_description = 'Mahallalarni yashil holatga o\'tkazish'

    def mark_mahallas_yellow(self, request, queryset):
        for task in queryset:
            task.mahallahs.update(status='yellow')
    mark_mahallas_yellow.short_description = 'Mahallalarni sariq holatga o\'tkazish'


@admin.register(BroadcastMessage, site=admin_site)
class BroadcastMessageAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'created_by', 'recipients_count', 'delivered_count', 'read_count')
    list_filter = ('created_at',)
    search_fields = ('title', 'message', 'created_by__username')
    readonly_fields = ('created_at', 'created_by', 'recipients_count', 'delivered_count', 'read_count')


class SubmissionFileInline(admin.TabularInline):
    model = SubmissionFile
    extra = 1

@admin.register(TaskSubmission)
class TaskSubmissionAdmin(admin.ModelAdmin):
    list_display = ('task', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('task__title', 'user__username', 'comment')
    date_hierarchy = 'created_at'
    inlines = [SubmissionFileInline]

@admin.register(TaskGrade)
class TaskGradeAdmin(admin.ModelAdmin):
    list_display = ('task', 'percentage', 'status', 'graded_by', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('task__title', 'graded_by__username')
    date_hierarchy = 'created_at'

@admin.register(BroadcastMessage)
class BroadcastMessageAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'created_at', 'delivered_count', 'read_count', 'recipients_count')
    list_filter = ('created_at',)
    search_fields = ('title', 'message', 'created_by__username')
    readonly_fields = ('delivered_count', 'read_count', 'recipients_count')
    date_hierarchy = 'created_at'




admin.site.register(Task, TaskAdmin)