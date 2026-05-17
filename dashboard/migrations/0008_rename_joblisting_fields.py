from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0007_joblisting_requirements_and_qualifications'),
    ]

    operations = [
        migrations.RenameField(
            model_name='joblisting',
            old_name='required_skills',
            new_name='required_skills_and_tools',
        ),
        migrations.RenameField(
            model_name='joblisting',
            old_name='requirements_and_qualifications',
            new_name='level_of_confidence',
        ),
    ]
