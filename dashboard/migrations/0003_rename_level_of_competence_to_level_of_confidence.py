from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0002_alter_files_file"),
    ]

    operations = [
        migrations.RenameField(
            model_name="fieldofexpertise",
            old_name="level_of_competence",
            new_name="level_of_confidence",
        ),
        migrations.AlterField(
            model_name="fieldofexpertise",
            name="level_of_confidence",
            field=models.CharField(blank=True, default="Confidence Level", max_length=1000, null=True),
        ),
    ]
