# Generated by Django 2.0.5 on 2018-05-08 09:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0003_category_href'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='text_type',
            field=models.CharField(choices=[('md', 'markdown'), ('h5', 'HTML5')], default='md', max_length=10, verbose_name='正文文本类型'),
        ),
    ]
