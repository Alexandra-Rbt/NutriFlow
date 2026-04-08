"""
importam alimente din Open Food Facts.
"""
from django.core.management.base import BaseCommand
from tracker.openfoodfacts_service import search_foods, get_product_by_barcode, import_product_to_db


# Lista de cautari predefinite pentru a popula baza de date initial
BULK_QUERIES = [
    ("piept de pui", 30),
    ("orez", 20),
    ("paste fainoase", 20),
    ("paine", 20),
    ("lapte", 15),
    ("iaurt", 15),
    ("ou", 10),
    ("somon", 15),
    ("ton conserva", 15),
    ("broccoli", 10),
    ("spanac", 10),
    ("tomate", 10),
    ("castravete", 10),
    ("banana", 10),
    ("mar", 10),
    ("portocala", 10),
    ("avocado", 10),
    ("migdale", 10),
    ("nuci", 10),
    ("unt de arahide", 10),
    ("fulgi de ovaz", 15),
    ("quinoa", 10),
    ("fasole", 10),
    ("linte", 10),
    ("cascaval", 10),
    ("branza", 10),
    ("ulei de masline", 8),
    ("ciocolata", 15),
    ("granola", 10),
    ("proteina zer", 10),
]


class Command(BaseCommand):
    help = 'Importa alimente din Open Food Facts in baza de date NutriFlow'

    def add_arguments(self, parser):
        parser.add_argument(
            '--query', '-q',
            type=str,
            help='Termen de cautare (ex: "piept de pui")',
        )
        parser.add_argument(
            '--count', '-c',
            type=int,
            default=20,
            help='Numarul de produse de importat per cautare (default: 20)',
        )
        parser.add_argument(
            '--barcode', '-b',
            type=str,
            help='Importa un singur produs dupa codul de bare',
        )
        parser.add_argument(
            '--bulk',
            action='store_true',
            help='Importa lista completa predefinita de alimente comune',
        )
        parser.add_argument(
            '--pages', '-p',
            type=int,
            default=1,
            help='Numarul de pagini de rezultate (fiecare pagina = 20 produse)',
        )

    def handle(self, *args, **options):
        if options['barcode']:
            self._import_barcode(options['barcode'])
        elif options['bulk']:
            self._import_bulk()
        elif options['query']:
            self._import_query(options['query'], options['count'], options['pages'])
        else:
            self.stdout.write(self.style.WARNING(
                'Specifica --query, --barcode sau --bulk.\n'
                'Exemplu: python manage.py import_off_foods --query "pui" --count 30\n'
                '         python manage.py import_off_foods --bulk'
            ))

    def _import_barcode(self, barcode):
        self.stdout.write(f'Caut produsul cu codul: {barcode}...')
        product = get_product_by_barcode(barcode)
        if not product:
            self.stdout.write(self.style.ERROR(f'  ✕ Produs negasit: {barcode}'))
            return
        food, created = import_product_to_db(product)
        status = self.style.SUCCESS('✓ Importat') if created else self.style.WARNING('~ Exista deja')
        self.stdout.write(f'  {status}: {food.name} — {food.kcal_per_100g} kcal/100g')

    def _import_query(self, query, count, pages):
        self.stdout.write(f'\nCautare: "{query}" — max {count * pages} produse...')
        imported = 0
        skipped  = 0
        errors   = 0

        for page in range(1, pages + 1):
            products = search_foods(query, page=page, page_size=min(count, 20))
            if not products:
                break

            for product in products[:count]:
                try:
                    food, created = import_product_to_db(product)
                    if created:
                        imported += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✓ {food.name} ({food.kcal_per_100g} kcal/100g)')
                        )
                    else:
                        skipped += 1
                except Exception as e:
                    errors += 1
                    self.stdout.write(self.style.ERROR(f'  ✕ Eroare: {e}'))

        self.stdout.write(
            f'\n  Importate: {imported} | Existente: {skipped} | Erori: {errors}'
        )
        return imported

    def _import_bulk(self):
        self.stdout.write(
            self.style.HTTP_INFO(
                f'\n=== Import bulk: {len(BULK_QUERIES)} categorii de alimente ===\n'
            )
        )
        total_imported = 0
        total_skipped  = 0

        for query, count in BULK_QUERIES:
            self.stdout.write(f'\n[{query}] — {count} produse')
            products = search_foods(query, page=1, page_size=count)
            imported = 0
            skipped  = 0

            for product in products:
                try:
                    food, created = import_product_to_db(product)
                    if created:
                        imported += 1
                        self.stdout.write(f'  ✓ {food.name}')
                    else:
                        skipped += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ✕ {e}'))

            total_imported += imported
            total_skipped  += skipped
            self.stdout.write(f'  → {imported} importate, {skipped} existente')

        self.stdout.write(
            self.style.SUCCESS(
                f'\n\n TOTAL: {total_imported} alimente importate, '
                f'{total_skipped} existau deja.'
            )
        )