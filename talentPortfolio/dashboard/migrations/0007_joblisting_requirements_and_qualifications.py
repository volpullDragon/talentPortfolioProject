from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0006_project_git_link'),
    ]

    operations = [
        migrations.AddField(
            model_name='joblisting',
            name='requirements_and_qualifications',
            field=models.CharField(blank=True, default='', max_length=1500, null=True),
        ),
    ]
