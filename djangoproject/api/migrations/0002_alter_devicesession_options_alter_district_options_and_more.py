# Generated by Django 5.1.7 on 2025-03-10 16:24

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='devicesession',
            options={'verbose_name': 'Qurilma sessiyasi', 'verbose_name_plural': 'Qurilma sessiyalari'},
        ),
        migrations.AlterModelOptions(
            name='district',
            options={'verbose_name': 'Tuman', 'verbose_name_plural': 'Tumanlar'},
        ),
        migrations.AlterModelOptions(
            name='employeetype',
            options={'verbose_name': 'Xodim turi', 'verbose_name_plural': 'Xodim turlari'},
        ),
        migrations.AlterModelOptions(
            name='jobtitle',
            options={'verbose_name': 'Lavozim', 'verbose_name_plural': 'Lavozimlar'},
        ),
        migrations.AlterModelOptions(
            name='mahallah',
            options={'verbose_name': 'Mahalla', 'verbose_name_plural': 'Mahallalar'},
        ),
        migrations.AlterModelOptions(
            name='region',
            options={'verbose_name': 'Viloyat', 'verbose_name_plural': 'Viloyatlar'},
        ),
        migrations.AlterModelOptions(
            name='task',
            options={'verbose_name': 'Topshiriq', 'verbose_name_plural': 'Topshiriqlar'},
        ),
        migrations.AlterModelOptions(
            name='taskfile',
            options={'verbose_name': 'Topshiriq fayli', 'verbose_name_plural': 'Topshiriq fayllari'},
        ),
        migrations.AlterModelOptions(
            name='taskprogress',
            options={'verbose_name': 'Topshiriq jarayoni', 'verbose_name_plural': 'Topshiriq jarayonlari'},
        ),
        migrations.AlterModelOptions(
            name='taskstatus',
            options={'verbose_name': 'Topshiriq holati', 'verbose_name_plural': 'Topshiriq holatlari'},
        ),
        migrations.AlterModelOptions(
            name='user',
            options={'verbose_name': 'Foydalanuvchi', 'verbose_name_plural': 'Foydalanuvchilar'},
        ),
        migrations.AddField(
            model_name='mahallah',
            name='status',
            field=models.CharField(choices=[('green', 'Yashil'), ('yellow', 'Sariq'), ('red', 'Qizil')], default='green', max_length=10, verbose_name='Holati'),
        ),
        migrations.AlterField(
            model_name='devicesession',
            name='device_id',
            field=models.CharField(max_length=255, verbose_name='Qurilma ID'),
        ),
        migrations.AlterField(
            model_name='devicesession',
            name='device_name',
            field=models.CharField(max_length=255, verbose_name='Qurilma nomi'),
        ),
        migrations.AlterField(
            model_name='devicesession',
            name='ip_address',
            field=models.GenericIPAddressField(verbose_name='IP manzil'),
        ),
        migrations.AlterField(
            model_name='devicesession',
            name='last_login',
            field=models.DateTimeField(auto_now=True, verbose_name="So'nggi kirish"),
        ),
        migrations.AlterField(
            model_name='devicesession',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='device_sessions', to=settings.AUTH_USER_MODEL, verbose_name='Foydalanuvchi'),
        ),
        migrations.AlterField(
            model_name='district',
            name='name',
            field=models.CharField(max_length=100, verbose_name='Nomi'),
        ),
        migrations.AlterField(
            model_name='district',
            name='region',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='districts', to='api.region', verbose_name='Viloyat'),
        ),
        migrations.AlterField(
            model_name='employeetype',
            name='name',
            field=models.CharField(max_length=100, verbose_name='Nomi'),
        ),
        migrations.AlterField(
            model_name='jobtitle',
            name='name',
            field=models.CharField(max_length=100, verbose_name='Nomi'),
        ),
        migrations.AlterField(
            model_name='mahallah',
            name='district',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mahallahs', to='api.district', verbose_name='Tuman'),
        ),
        migrations.AlterField(
            model_name='mahallah',
            name='name',
            field=models.CharField(max_length=100, verbose_name='Nomi'),
        ),
        migrations.AlterField(
            model_name='region',
            name='name',
            field=models.CharField(max_length=100, verbose_name='Nomi'),
        ),
        migrations.AlterField(
            model_name='task',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan sana'),
        ),
        migrations.AlterField(
            model_name='task',
            name='deadline',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Muddat'),
        ),
        migrations.AlterField(
            model_name='task',
            name='description',
            field=models.TextField(verbose_name='Tavsif'),
        ),
        migrations.AlterField(
            model_name='task',
            name='mahallahs',
            field=models.ManyToManyField(related_name='tasks', to='api.mahallah', verbose_name='Mahallalar'),
        ),
        migrations.AlterField(
            model_name='task',
            name='status',
            field=models.CharField(choices=[('active', 'Faol'), ('completed', 'Bajarilgan'), ('rejected', 'Rad etilgan')], default='active', max_length=20, verbose_name='Holat'),
        ),
        migrations.AlterField(
            model_name='task',
            name='title',
            field=models.CharField(max_length=255, verbose_name='Sarlavha'),
        ),
        migrations.AlterField(
            model_name='task',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Yangilangan sana'),
        ),
        migrations.AlterField(
            model_name='taskfile',
            name='file',
            field=models.FileField(upload_to='task_files/%Y/%m/%d/', verbose_name='Fayl'),
        ),
        migrations.AlterField(
            model_name='taskfile',
            name='file_name',
            field=models.CharField(max_length=255, verbose_name='Fayl nomi'),
        ),
        migrations.AlterField(
            model_name='taskfile',
            name='file_type',
            field=models.CharField(max_length=100, verbose_name='Fayl turi'),
        ),
        migrations.AlterField(
            model_name='taskfile',
            name='task_progress',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='files', to='api.taskprogress', verbose_name='Topshiriq jarayoni'),
        ),
        migrations.AlterField(
            model_name='taskfile',
            name='uploaded_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Yuklangan sana'),
        ),
        migrations.AlterField(
            model_name='taskprogress',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan sana'),
        ),
        migrations.AlterField(
            model_name='taskprogress',
            name='description',
            field=models.TextField(verbose_name='Tavsif'),
        ),
        migrations.AlterField(
            model_name='taskprogress',
            name='task',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progress', to='api.task', verbose_name='Topshiriq'),
        ),
        migrations.AlterField(
            model_name='taskprogress',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='task_progress', to=settings.AUTH_USER_MODEL, verbose_name='Foydalanuvchi'),
        ),
        migrations.AlterField(
            model_name='taskstatus',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan sana'),
        ),
        migrations.AlterField(
            model_name='taskstatus',
            name='rejection_reason',
            field=models.TextField(blank=True, null=True, verbose_name='Rad etish sababi'),
        ),
        migrations.AlterField(
            model_name='taskstatus',
            name='status',
            field=models.CharField(choices=[('active', 'Faol'), ('completed', 'Bajarilgan'), ('rejected', 'Rad etilgan')], max_length=20, verbose_name='Holat'),
        ),
        migrations.AlterField(
            model_name='taskstatus',
            name='task',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='status_history', to='api.task', verbose_name='Topshiriq'),
        ),
        migrations.AlterField(
            model_name='taskstatus',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='task_status_updates', to=settings.AUTH_USER_MODEL, verbose_name='Foydalanuvchi'),
        ),
        migrations.AlterField(
            model_name='user',
            name='date_joined',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name="Ro'yxatdan o'tgan sana"),
        ),
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(blank=True, max_length=254, verbose_name='Elektron pochta'),
        ),
        migrations.AlterField(
            model_name='user',
            name='employee_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.employeetype', verbose_name='Xodim turi'),
        ),
        migrations.AlterField(
            model_name='user',
            name='full_name',
            field=models.CharField(blank=True, max_length=255, verbose_name="To'liq ism"),
        ),
        migrations.AlterField(
            model_name='user',
            name='is_active',
            field=models.BooleanField(default=True, help_text="Foydalanuvchi faol yoki faol emasligini belgilaydi. Foydalanuvchini o'chirish o'rniga bu parametrni o'zgartiring.", verbose_name='Faol'),
        ),
        migrations.AlterField(
            model_name='user',
            name='is_staff',
            field=models.BooleanField(default=False, help_text="Foydalanuvchining admin paneliga kirish huquqi bor-yo'qligini belgilaydi.", verbose_name='Admin holati'),
        ),
        migrations.AlterField(
            model_name='user',
            name='job_title',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.jobtitle', verbose_name='Lavozim'),
        ),
        migrations.AlterField(
            model_name='user',
            name='jshir',
            field=models.CharField(blank=True, max_length=14, verbose_name='JSHIR'),
        ),
        migrations.AlterField(
            model_name='user',
            name='last_login',
            field=models.DateTimeField(blank=True, null=True, verbose_name="So'nggi kirish"),
        ),
        migrations.AlterField(
            model_name='user',
            name='mahallah',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.mahallah', verbose_name='Mahalla'),
        ),
        migrations.AlterField(
            model_name='user',
            name='phone',
            field=models.CharField(blank=True, max_length=20, verbose_name='Telefon raqami'),
        ),
        migrations.AlterField(
            model_name='user',
            name='telegram_id',
            field=models.BigIntegerField(blank=True, null=True, unique=True, verbose_name='Telegram ID'),
        ),
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(max_length=150, unique=True, verbose_name='Foydalanuvchi nomi'),
        ),
        migrations.CreateModel(
            name='BroadcastMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='Sarlavha')),
                ('message', models.TextField(verbose_name='Xabar matni')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Yuborilgan sana')),
                ('recipients_count', models.IntegerField(default=0, verbose_name='Qabul qiluvchilar soni')),
                ('delivered_count', models.IntegerField(default=0, verbose_name='Yetkazilganlar soni')),
                ('read_count', models.IntegerField(default=0, verbose_name="O'qilganlar soni")),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sent_broadcasts', to=settings.AUTH_USER_MODEL, verbose_name='Yuboruvchi')),
            ],
            options={
                'verbose_name': 'Ommaviy xabar',
                'verbose_name_plural': 'Ommaviy xabarlar',
                'ordering': ['-created_at'],
            },
        ),
    ]
