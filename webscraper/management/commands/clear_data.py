from django.core.management.base import BaseCommand
from webscraper.models import Dataset, Log


class Command(BaseCommand):
    help = "Clears all datasets and logs from the database. (Note: User accounts and authentication data are not affected.)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Skip confirmation prompt",
        )

    def handle(self, *args, **options):
        dataset_count = Dataset.objects.count()
        log_count = Log.objects.count()

        if dataset_count == 0 and log_count == 0:
            self.stdout.write(
                self.style.WARNING("Database is already empty!")
            )
            return

        self.stdout.write(
            self.style.WARNING(
                f"\nThis will delete:\n"
                f"  - {dataset_count} datasets\n"
                f"  - {log_count} logs\n"
            )
        )

        if not options["confirm"]:
            confirm = input("Are you sure you want to continue? (yes/no): ")
            if confirm.lower() not in ["yes", "y"]:
                self.stdout.write(
                    self.style.ERROR("Operation cancelled.")
                )
                return

        Dataset.objects.all().delete()
        Log.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully deleted:\n"
                f"  - {dataset_count} datasets\n"
                f"  - {log_count} logs\n"
            )
        )
