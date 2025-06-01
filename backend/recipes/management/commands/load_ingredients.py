import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings

from recipes.models import Ingredient


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='ingredients.csv',
        )
    
    def handle(self, *args, **options):
        file_path = options['file']
        
        if not os.path.isabs(file_path):
            data_dir = os.path.join(settings.BASE_DIR.parent, 'data')
            file_path = os.path.join(data_dir, file_path)
        
        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.ERROR(f'Файл {file_path} не найден')
            )
            return
        
        ingredients_created = 0
        ingredients_updated = 0
        
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            
            for row in reader:
                if len(row) >= 2:
                    name = row[0].strip()
                    measurement_unit = row[1].strip()
                    
                    ingredient, created = Ingredient.objects.get_or_create(
                        name=name,
                        measurement_unit=measurement_unit
                    )
                    
                    if created:
                        ingredients_created += 1
                    else:
                        ingredients_updated += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Загрузка завершена. '
                f'Создано: {ingredients_created}, '
                f'Обновлено: {ingredients_updated}'
            )
        ) 