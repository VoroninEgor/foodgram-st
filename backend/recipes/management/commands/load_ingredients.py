import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings

from recipes.models import Ingredient


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            'file',
            type=str,
        )

    def handle(self, *args, **options):
        file_path = Path(options['file'])
        
        if not file_path.is_absolute():
            data_dir = settings.BASE_DIR.parent / 'data'
            file_path = data_dir / file_path

        if not file_path.exists():
            self.stdout.write(
                self.style.ERROR(f'Файл {file_path} не найден')
            )
            return

        try:
            with open(file_path, encoding='utf-8') as file:
                reader = csv.reader(file)
                ingredients = []
                for row in reader:
                    if len(row) != 2:
                        continue
                    name, measurement_unit = row
                    ingredients.append(
                        Ingredient(
                            name=name.strip(),
                            measurement_unit=measurement_unit.strip()
                        )
                    )
                
                if ingredients:
                    Ingredient.objects.bulk_create(
                        ingredients,
                        ignore_conflicts=True
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Успешно загружено {len(ingredients)} ингредиентов'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING('Файл не содержит данных')
                    )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка при загрузке файла: {e}')
            ) 