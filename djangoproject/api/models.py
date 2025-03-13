from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from datetime import datetime, timedelta
from django.conf import settings


TASK_STATUS_CHOICES = [
    ('active', 'Faol'),
    ('completed', 'Bajarilgan'),
    ('rejected', 'Rad etilgan'),
]

MAHALLA_STATUS_CHOICES = [
    ('green', 'Yashil'),
    ('yellow', 'Sariq'),
    ('red', 'Qizil'),
]

class Region(models.Model):
    name = models.CharField('Nomi', max_length=100)

    class Meta:
        verbose_name = 'Viloyat'
        verbose_name_plural = 'Viloyatlar'

    def __str__(self):
        return self.name

class District(models.Model):
    name = models.CharField('Nomi', max_length=100)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='districts', verbose_name='Viloyat')

    class Meta:
        verbose_name = 'Tuman'
        verbose_name_plural = 'Tumanlar'

    def __str__(self):
        return f"{self.name} ({self.region.name})"

class Mahallah(models.Model):
    name = models.CharField('Nomi', max_length=100)
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='mahallahs', verbose_name='Tuman')
    status = models.CharField('Holati', max_length=10, choices=MAHALLA_STATUS_CHOICES, default='green')

    class Meta:
        verbose_name = 'Mahalla'
        verbose_name_plural = 'Mahallalar'

    def __str__(self):
        return f"{self.name} ({self.district.name})"

    def get_completion_rate(self, days=30):
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        tasks = Task.objects.filter(
            mahallahs=self,
            created_at__gte=start_date,
            created_at__lte=end_date
        )

        total_tasks = tasks.count()
        if total_tasks == 0:
            return 0

        completed_on_time = 0
        for task in tasks:
            if task.is_completed_on_time():
                completed_on_time += 1

        return (completed_on_time / total_tasks) * 100

    def get_daily_stats(self, days=30):
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        stats = []
        current_date = start_date

        while current_date <= end_date:
            next_date = current_date + timedelta(days=1)

            tasks = Task.objects.filter(
                mahallahs=self,
                created_at__date__gte=current_date,
                created_at__date__lt=next_date
            )

            total = tasks.count()
            completed = tasks.filter(status='completed').count()
            rejected = tasks.filter(status='rejected').count()
            active = tasks.filter(status='active').count()

            stats.append({
                'date': current_date,
                'total': total,
                'completed': completed,
                'rejected': rejected,
                'active': active,
                'completion_rate': (completed / total * 100) if total > 0 else 0
            })

            current_date = next_date

        return stats


    def get_monthly_stats(self, months=12):
        end_date = timezone.now().date().replace(day=1)
        stats = []

        for i in range(months):
            if i > 0:
                last_day = end_date.replace(day=1) - timedelta(days=1)
            else:
                last_day = timezone.now().date()

            first_day = end_date.replace(day=1)

            tasks = Task.objects.filter(
                mahallahs=self,
                created_at__date__gte=first_day,
                created_at__date__lte=last_day
            )

            total = tasks.count()
            completed = tasks.filter(status='completed').count()
            rejected = tasks.filter(status='rejected').count()
            active = tasks.filter(status='active').count()

            stats.append({
                'month': first_day.strftime('%Y-%m'),
                'month_name': first_day.strftime('%B %Y'),
                'total': total,
                'completed': completed,
                'rejected': rejected,
                'active': active,
                'completion_rate': (completed / total * 100) if total > 0 else 0
            })

            if first_day.month == 1:
                end_date = end_date.replace(year=end_date.year-1, month=12)
            else:
                end_date = end_date.replace(month=end_date.month-1)

        return list(reversed(stats))

class JobTitle(models.Model):
    name = models.CharField('Nomi', max_length=100)

    class Meta:
        verbose_name = 'Lavozim'
        verbose_name_plural = 'Lavozimlar'

    def __str__(self):
        return self.name

class EmployeeType(models.Model):
    name = models.CharField('Nomi', max_length=100)

    class Meta:
        verbose_name = 'Xodim turi'
        verbose_name_plural = 'Xodim turlari'

    def __str__(self):
        return self.name

class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('Foydalanuvchi nomi kiritilishi shart')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser is_staff=True bo\'lishi kerak.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser is_superuser=True bo\'lishi kerak.')

        return self.create_user(username, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField('Foydalanuvchi nomi', max_length=150, unique=True)
    email = models.EmailField('Elektron pochta', blank=True)
    full_name = models.CharField('To\'liq ism', max_length=255, blank=True)
    phone = models.CharField('Telefon raqami', max_length=20, blank=True)
    jshir = models.CharField('JSHIR', max_length=14, blank=True)
    telegram_id = models.BigIntegerField('Telegram ID', null=True, blank=True, unique=True)
    job_title = models.ForeignKey(JobTitle, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Lavozim')
    employee_type = models.ForeignKey(EmployeeType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Xodim turi')
    mahallah = models.ForeignKey(Mahallah, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Mahalla')

    is_staff = models.BooleanField(
        'Admin holati',
        default=False,
        help_text='Foydalanuvchining admin paneliga kirish huquqi bor-yo\'qligini belgilaydi.',
    )
    is_active = models.BooleanField(
        'Faol',
        default=True,
        help_text='Foydalanuvchi faol yoki faol emasligini belgilaydi. Foydalanuvchini o\'chirish o\'rniga bu parametrni o\'zgartiring.',
    )
    date_joined = models.DateTimeField('Ro\'yxatdan o\'tgan sana', default=timezone.now)
    last_login = models.DateTimeField('So\'nggi kirish', null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'Foydalanuvchi'
        verbose_name_plural = 'Foydalanuvchilar'

    def __str__(self):
        return self.full_name or self.username

    def get_task_completion_rate(self):
        tasks = Task.objects.filter(mahallahs=self.mahallah)
        total = tasks.count()
        if total == 0:
            return 0

        completed = TaskStatus.objects.filter(
            task__in=tasks,
            user=self,
            status='completed'
        ).count()

        return (completed / total) * 100

class DeviceSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_sessions', verbose_name='Foydalanuvchi')
    device_id = models.CharField('Qurilma ID', max_length=255)
    device_name = models.CharField('Qurilma nomi', max_length=255)
    ip_address = models.GenericIPAddressField('IP manzil')
    last_login = models.DateTimeField('So\'nggi kirish', auto_now=True)

    class Meta:
        verbose_name = 'Qurilma sessiyasi'
        verbose_name_plural = 'Qurilma sessiyalari'

    def __str__(self):
        return f"{self.user} - {self.device_name}"

class Task(models.Model):
    title = models.CharField('Sarlavha', max_length=255)
    description = models.TextField('Tavsif')
    deadline = models.DateTimeField('Muddat', null=True, blank=True)
    created_at = models.DateTimeField('Yaratilgan sana', auto_now_add=True)
    updated_at = models.DateTimeField('Yangilangan sana', auto_now=True)
    status = models.CharField('Holat', max_length=20, choices=TASK_STATUS_CHOICES, default='active')

    mahallahs = models.ManyToManyField(Mahallah, related_name='tasks', verbose_name='Mahallalar')

    class Meta:
        verbose_name = 'Topshiriq'
        verbose_name_plural = 'Topshiriqlar'

    def __str__(self):
        return self.title

    def is_completed_on_time(self):
        if not self.deadline:
            return True

        completed_status = self.status_history.filter(status='completed').order_by('-created_at').first()
        if not completed_status:
            return False

        return completed_status.created_at <= self.deadline

    def get_completion_rate(self):
        mahalla_count = self.mahallahs.count()
        if mahalla_count == 0:
            return 0

        completed_count = 0
        for mahalla in self.mahallahs.all():
            users = User.objects.filter(mahallah=mahalla)
            user_completed = TaskStatus.objects.filter(
                task=self,
                user__in=users,
                status='completed'
            ).exists()

            if user_completed:
                completed_count += 1

        return (completed_count / mahalla_count) * 100

    @property
    def completion_percentage(self):
        return self.get_completion_rate()

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            TaskStatus.objects.create(
                task=self,
                user=User.objects.filter(is_superuser=True).first(),
                status='active'
            )

        if self.deadline and self.status == 'active' and self.deadline < timezone.now():
            for mahalla in self.mahallahs.all():
                users_in_mahalla = User.objects.filter(mahallah=mahalla)
                task_completed = TaskStatus.objects.filter(
                    task=self,
                    user__in=users_in_mahalla,
                    status='completed'
                ).exists()

                if not task_completed:
                    mahalla.status = 'red'
                    mahalla.save()



                    
def task_file_path(instance, filename):
    return f'tasks/{instance.task.id}/{filename}'



class TaskProgress(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='progress', verbose_name='Topshiriq')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='task_progress', verbose_name='Foydalanuvchi')
    description = models.TextField('Tavsif')
    created_at = models.DateTimeField('Yaratilgan sana', auto_now_add=True)

    class Meta:
        verbose_name = 'Topshiriq jarayoni'
        verbose_name_plural = 'Topshiriq jarayonlari'

    def __str__(self):
        return f"{self.task.title} - {self.user.full_name}"


class TaskSubmission(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='submissions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_submissions')
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.task.title}"

def submission_file_path(instance, filename):
    return f'submissions/{instance.submission.id}/{filename}'


import os


class SubmissionFile(models.Model):
    submission = models.ForeignKey(TaskSubmission, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to=submission_file_path)
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.file_name
    
    @property
    def file_extension(self):
        return os.path.splitext(self.file_name)[1].lower()


class TaskFile(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to=task_file_path)
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.file_name
    
    @property
    def file_extension(self):
        return os.path.splitext(self.file_name)[1].lower()

class TaskStatus(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='status_history', verbose_name='Topshiriq')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='task_status_updates', verbose_name='Foydalanuvchi')
    status = models.CharField('Holat', max_length=20, choices=TASK_STATUS_CHOICES)
    rejection_reason = models.TextField('Rad etish sababi', blank=True, null=True)
    created_at = models.DateTimeField('Yaratilgan sana', auto_now_add=True)

    class Meta:
        verbose_name = 'Topshiriq holati'
        verbose_name_plural = 'Topshiriq holatlari'

    def __str__(self):
        return f"{self.task.title} - {self.status}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        self.task.status = self.status
        self.task.save(update_fields=['status'])

        if self.status == 'completed' and self.task.deadline and self.created_at <= self.task.deadline:
            mahalla = self.user.mahallah
            if mahalla and mahalla.status == 'red':
                mahalla.status = 'yellow'
                mahalla.save()

class BroadcastMessage(models.Model):
    title = models.CharField('Sarlavha', max_length=255)
    message = models.TextField('Xabar matni')
    created_at = models.DateTimeField('Yuborilgan sana', auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_broadcasts', verbose_name='Yuboruvchi')

    recipients_count = models.IntegerField('Qabul qiluvchilar soni', default=0)
    delivered_count = models.IntegerField('Yetkazilganlar soni', default=0)
    read_count = models.IntegerField('O\'qilganlar soni', default=0)

    class Meta:
        verbose_name = 'Ommaviy xabar'
        verbose_name_plural = 'Ommaviy xabarlar'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class Broadcast(models.Model):
    TARGET_CHOICES = (
        ('all', 'All Users'),
        ('district', 'District'),
        ('mahalla', 'Mahalla'),
    )

    title = models.CharField(max_length=255)
    message = models.TextField()
    target_type = models.CharField(max_length=20, choices=TARGET_CHOICES)
    target_id = models.IntegerField(null=True, blank=True)
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='api_broadcasts'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_count = models.IntegerField(default=0)
    read_count = models.IntegerField(default=0)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']



def task_file_path(instance, filename):
    return f'tasks/{instance.task.id}/{filename}'

class TaskGrade(models.Model):
    STATUS_CHOICES = (
        ('green', 'Green'),
        ('yellow', 'Yellow'),
        ('red', 'Red'),
    )
    
    task = models.OneToOneField(Task, on_delete=models.CASCADE, related_name='grade')
    percentage = models.IntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='task_grades'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.task.title} - {self.percentage}% ({self.status})"