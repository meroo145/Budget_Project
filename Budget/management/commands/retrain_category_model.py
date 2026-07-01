# Budget/management/commands/retrain_category_model.py
"""
Django management command wrapping ai/train.py's train_model().

Usage:
    python manage.py retrain_category_model
    python manage.py retrain_category_model --threshold 0.8 --max-iter 15

Because this runs inside the Django process (unlike calling `python -m
ai.train` directly), django.setup() has already happened -- ai/data_prep.py
calling it again is a harmless no-op (Django's apps.populate() short-circuits
if already ready).

NOTE ON HOT-RELOAD: this command runs as its own separate process from
`python manage.py runserver`. It does NOT need to (and cannot) push the new
model into the running server's memory directly. Instead, ai/model_loader.py
checks model_bundle.pkl's modification time on every prediction request --
so the running server picks up the freshly retrained model automatically
on its very next request. No restart needed.
"""

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Retrain the ML transaction-category prediction model (semi-supervised)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold', type=float, default=0.75,
            help="Minimum confidence required to accept a pseudo-label during "
                 "self-training on unlabeled transactions (default: 0.75).",
        )
        parser.add_argument(
            '--max-iter', type=int, default=10,
            help="Maximum self-training iterations (default: 10).",
        )

    def handle(self, *args, **options):
        # Imported lazily (inside handle, not at module top level) so that
        # `python manage.py help` and other unrelated commands don't pay
        # the cost of importing scikit-learn/pandas just to list commands.
        from ai.train import train_model

        self.stdout.write(self.style.NOTICE("Starting retraining..."))

        try:
            summary = train_model(
                confidence_threshold=options['threshold'],
                max_iterations=options['max_iter'],
                verbose=True,
            )
        except ValueError as e:
            # train_model raises ValueError for "not enough labeled data" --
            # surface it as a clean CommandError instead of a traceback.
            raise CommandError(str(e))

        self.stdout.write(self.style.SUCCESS(
            f"\nRetraining complete.\n"
            f"  Labeled transactions used:   {summary['labeled_count']}\n"
            f"  Unlabeled transactions seen: {summary['unlabeled_count']}\n"
            f"  Pseudo-labeled confidently:  {summary['pseudo_labeled_count']}\n"
            f"  Held-out test accuracy:      {summary['test_accuracy']:.1%}\n"
            f"  Saved to:                    {summary['save_path']}\n\n"
            f"The running server (if any) will pick up this model "
            f"automatically on its next prediction request -- no restart needed."
        ))