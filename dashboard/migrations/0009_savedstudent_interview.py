from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0008_rename_joblisting_fields'),
        ('userManagement', '0017_remove_portfolio_bio_portfolio_about_me_and_more'),  # Adjust to latest userManagement migration
    ]

    operations = [
        migrations.CreateModel(
            name='SavedStudent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('saved_at', models.DateTimeField(auto_now_add=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('faculty_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_students', to='userManagement.profile')),
                ('student_portfolio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_by_faculties', to='userManagement.portfolio')),
            ],
            options={
                'ordering': ['-saved_at'],
                'unique_together': {('faculty_profile', 'student_portfolio')},
            },
        ),
        migrations.CreateModel(
            name='Interview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('interview_type', models.CharField(choices=[('video', 'Video'), ('phone', 'Phone'), ('in_person', 'In Person')], default='video', max_length=20)),
                ('scheduled_date', models.DateField()),
                ('scheduled_time', models.TimeField()),
                ('location', models.CharField(blank=True, max_length=500, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('video_link', models.URLField(blank=True, max_length=200, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('job_listing', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='interviews', to='dashboard.joblisting')),
                ('student_portfolio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='interviews', to='userManagement.portfolio')),
            ],
            options={
                'ordering': ['scheduled_date', 'scheduled_time'],
            },
        ),
    ]
