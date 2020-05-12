# Generated by Django 3.0.6 on 2020-05-12 16:01

import autoslug.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0003_auto_20200509_0934"),
    ]

    operations = [
        migrations.AlterField(
            model_name="category",
            name="slug",
            field=autoslug.fields.AutoSlugField(
                default=None, editable=False, null=True, populate_from="name"
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="slug",
            field=autoslug.fields.AutoSlugField(
                default=None, editable=False, null=True, populate_from="id"
            ),
        ),
    ]