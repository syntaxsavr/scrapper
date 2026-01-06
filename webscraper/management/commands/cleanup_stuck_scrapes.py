from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from webscraper.models import UserScrape

class Command(BaseCommand):
    help = 'Mark old pending scrapes as failed (cleanup stuck scrapes)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--minutes',
            type=int,
            default=30,
            help='Mark scrapes as failed if pending for more than this many minutes (default: 30)'
        )

    def handle(self, *args, **options):
        minutes_ago = timezone.now() - timedelta(minutes=options['minutes'])
        
        # find scrapes that have been pending for too long
        stuck_scrapes = UserScrape.objects.filter(
            status__in=['pending', 'running'],
            started_at__lt=minutes_ago
        )
        
        count = stuck_scrapes.count()
        
        if count > 0:
            # update them to failed status
            stuck_scrapes.update(
                status='failed',
                error_message=f'Scrape timed out after {options["minutes"]} minutes',
                completed_at=timezone.now()
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully marked {count} stuck scrape(s) as failed')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('No stuck scrapes found')
            )
