from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0002_userlead_phone'),
    ]

    operations = [
        migrations.AddField(
            model_name='userlead',
            name='session_id',
            field=models.CharField(blank=True, max_length=80, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='userlead',
            name='email_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='userlead',
            name='lead_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='userlead',
            name='lead_notification_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='userlead',
            name='email_sent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='userlead',
            name='lead_notification_sent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='userlead',
            name='last_activity',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
