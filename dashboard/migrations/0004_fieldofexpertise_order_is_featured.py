from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0003_rename_level_of_competence_to_level_of_confidence"),
    ]

    operations = [
        migrations.AddField(
            model_name="fieldofexpertise",
            name="order",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="fieldofexpertise",
            name="is_featured",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterModelOptions(
            name="fieldofexpertise",
            options={"ordering": ["portfolio", "order"]},
        ),
    ]
