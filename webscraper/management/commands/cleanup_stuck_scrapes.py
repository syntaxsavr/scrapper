from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from webscraper.models import UserScrape
from celery.result import AsyncResult

class Command(BaseCommand):
    help = 'Mark old pending scrapes as failed (cleanup stuck scrapes)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--minutes',
            type=int,
            default=30,
            help='Mark scrapes as failed if pending for more than this many minutes (default: 30)'
        )
        parser.add_argument(
            '--check-celery',
            action='store_true',
            help='Check Celery task status for running scrapes'
        )

    def handle(self, *args, **options):
        minutes_ago = timezone.now() - timedelta(minutes=options['minutes'])
        
        # find scrapes that have been pending/running for too long
        stuck_scrapes = UserScrape.objects.filter(
            status__in=['pending', 'running'],
            started_at__lt=minutes_ago
        )
        
        count = 0
        checked_count = 0
        
        for scrape in stuck_scrapes:
            # If check-celery flag is set, verify with Celery
            if options['check_celery'] and scrape.celery_task_id:
                checked_count += 1
                try:
                    task = AsyncResult(scrape.celery_task_id)
                    if task.ready():
                        if task.successful():
                            scrape.status = 'completed'
                            scrape.completed_at = timezone.now()
                            if scrape.started_at:
                                scrape.duration_seconds = (timezone.now() - scrape.started_at).total_seconds()
                            scrape.save()
                            count += 1
                            self.stdout.write(f'Fixed stuck completed scrape: {scrape.id} - {scrape.query}')
                        else:
                            scrape.status = 'failed'
                            scrape.error_message = f'Task failed: {str(task.info)}'
                            scrape.completed_at = timezone.now()
                            if scrape.started_at:
                                scrape.duration_seconds = (timezone.now() - scrape.started_at).total_seconds()
                            scrape.save()
                            count += 1
                            self.stdout.write(f'Marked failed scrape: {scrape.id} - {scrape.query}')
                    else:
                        # Task still running according to Celery
                        self.stdout.write(
                            self.style.WARNING(f'Scrape {scrape.id} task is still running in Celery')
                        )
                except Exception as e:
                    # Error checking task, mark as failed
                    scrape.status = 'failed'
                    scrape.error_message = f'Task check failed: {str(e)}'
                    scrape.completed_at = timezone.now()
                    if scrape.started_at:
                        scrape.duration_seconds = (timezone.now() - scrape.started_at).total_seconds()
                    scrape.save()
                    count += 1
                    self.stdout.write(f'Marked lost scrape: {scrape.id} - {scrape.query}')
            else:
                # No Celery check, just mark as failed by time
                scrape.status = 'failed'
                scrape.error_message = f'Scrape timed out after {options["minutes"]} minutes'
                scrape.completed_at = timezone.now()
                if scrape.started_at:
                    scrape.duration_seconds = (timezone.now() - scrape.started_at).total_seconds()
                scrape.save()
                count += 1
        
        if count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully processed {count} stuck scrape(s)')
            )
            if options['check_celery']:
                self.stdout.write(f'Checked {checked_count} scrapes against Celery')
        else:
            self.stdout.write(
                self.style.SUCCESS('No stuck scrapes found')
            )
