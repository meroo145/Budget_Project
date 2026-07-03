# =============================================================================
#  views.py — BudgetTracker
#  All view functions grouped by feature area.
#  Every function is protected with @login_required where appropriate.
# =============================================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from .models import Category, Budget, Transaction, Goal, Notification, AIInsight
import csv

# ML category prediction — the model itself is loaded once by
# Budget/apps.py:BudgetConfig.ready(), this import just gives us the
# function that runs inference against the already-cached model.
from ai.model_loader import predict_category_with_confidence

# AI Financial Advisor — all orchestration (analyzer -> insights -> Gemini
# -> caching) lives in the service layer; the views below just call it.
from ai.advisor import get_advice, refresh_advice


# =============================================================================
#  HOME & AUTHENTICATION
# =============================================================================

def home_page(request):
    """Show the landing page; redirect logged-in users straight to dashboard."""
    if request.user.is_authenticated:
        return redirect('dashboard_url')
    return render(request, 'home.html')


def signup_page(request):
    """Register a new user account using email as the username."""
    if request.method == 'POST':
        name     = request.POST.get('name', '').strip()
        email    = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm  = request.POST.get('confirmPassword', '')

        # Validate passwords match
        if password != confirm:
            messages.error(request, 'Passwords do not match!')
            return redirect('signup_url')

        # Prevent duplicate accounts
        if User.objects.filter(username=email).exists():
            messages.error(request, 'Email already registered!')
            return redirect('signup_url')

        # Create the user and log them in immediately
        user = User.objects.create_user(
            username=email, email=email,
            password=password, first_name=name
        )
        login(request, user)
        return redirect('dashboard_url')

    return render(request, 'sign.html')


def login_page(request):
    """Authenticate an existing user by email and password."""
    if request.user.is_authenticated:
        return redirect('dashboard_url')

    if request.method == 'POST':
        email    = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        # Django uses 'username' internally; we store email there
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard_url')

        messages.error(request, 'Invalid email or password!')

    return render(request, 'login.html')


def logout_view(request):
    """Log the user out and send them back to the home page."""
    logout(request)
    return redirect('home')


# =============================================================================
#  DASHBOARD & PROFILE
# =============================================================================

@login_required(login_url='login_url')
def dashboard_page(request):
    """
    Main dashboard: totals, recent transactions, active goals,
    and any unread budget notifications.
    """
    user_tx  = Transaction.objects.filter(user=request.user)
    total_in = user_tx.filter(type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    total_ex = user_tx.filter(type='expense').aggregate(Sum('amount'))['amount__sum'] or 0

    # Fetch unread notifications so we can show them as warnings
    notifications = Notification.objects.filter(
        user=request.user, is_read=False
    ).order_by('-created')

    # Pass each notification message through Django's messages framework
    # so the existing template {% if messages %} block picks them up
    for notif in notifications:
        messages.warning(request, notif.message)
        notif.is_read = True   # Mark as read after showing once
        notif.save()

    context = {
        'total_income':   round(total_in, 2),
        'total_expenses': round(total_ex, 2),
        'balance':        round(total_in - total_ex, 2),
        # Last 5 transactions for the "Recent" table
        'recent':         user_tx.order_by('-date')[:5],
        # Only show incomplete goals in the progress widget
        'goals':          Goal.objects.filter(
                              user=request.user,
                              saved_amount__lt=F('target_amount')
                          )[:3],
    }
    return render(request, 'dashboard.html', context)


@login_required(login_url='login_url')
def profile_page(request):
    """
    User profile: update name/email, change password, or delete account.
    Also shows a summary of the user's financial stats.
    """
    if request.method == 'POST':
        action = request.POST.get('action')

        # ── Update name and email ──────────────────────────────────────────
        if action == 'update_info':
            request.user.first_name = request.POST.get('name', '').strip()
            request.user.email      = request.POST.get('email', '').strip()
            request.user.username   = request.user.email   # keep username in sync
            request.user.save()
            messages.success(request, 'Profile updated successfully!')

        # ── Change password ────────────────────────────────────────────────
        elif action == 'change_password':
            old_pass     = request.POST.get('old_password', '')
            new_pass     = request.POST.get('new_password', '')
            confirm_pass = request.POST.get('confirm_password', '')

            if not request.user.check_password(old_pass):
                messages.error(request, 'Current password is incorrect!')
            elif new_pass != confirm_pass:
                messages.error(request, 'New passwords do not match!')
            elif len(new_pass) < 8:
                messages.error(request, 'Password must be at least 8 characters!')
            else:
                request.user.set_password(new_pass)
                request.user.save()
                # Keep the user logged in after a password change
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Password changed successfully!')

        # ── Delete account ─────────────────────────────────────────────────
        elif action == 'delete_account':
            password = request.POST.get('confirm_delete_password', '')
            if not request.user.check_password(password):
                messages.error(request, 'Incorrect password. Account not deleted.')
                return redirect('profile_url')
            request.user.delete()
            logout(request)
            return redirect('home')

        return redirect('profile_url')

    # ── GET: build stats for the profile summary cards ─────────────────────
    user_tx  = Transaction.objects.filter(user=request.user)
    total_in = user_tx.filter(type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    total_ex = user_tx.filter(type='expense').aggregate(Sum('amount'))['amount__sum'] or 0

    context = {
        'total_income':   round(total_in, 2),
        'total_expenses': round(total_ex, 2),
        'balance':        round(total_in - total_ex, 2),
        'total_tx':       user_tx.count(),
        'total_goals':    Goal.objects.filter(user=request.user).count(),
        'total_budgets':  Budget.objects.filter(user=request.user).count(),
    }
    return render(request, 'profile.html', context)


# =============================================================================
#  TRANSACTIONS
# =============================================================================

@login_required(login_url='login_url')
def add_expense_view(request):
    """Save a new expense transaction and check budget alerts afterwards."""
    categories = Category.objects.all()

    if request.method == 'POST':
        # Validate amount and date before saving
        error = validate_transaction(request.POST.get('amount'), request.POST.get('date'))
        if error:
            messages.error(request, error)
            return redirect('add_expense_url')   # FIX: was 'add.expense_url'

        category_id = request.POST.get('category')

        # The '__new__' sentinel means the user typed a brand-new category
        # via the inline AJAX form; it should already be saved by the time
        # this POST fires (the JS blocks submission until saved), but we
        # handle it defensively here too.
        if category_id == '__new__':
            messages.error(request, 'Please select or create a category first.')
            return redirect('add_expense_url')

        # The '__skip__' sentinel means the user chose "Not sure -- let AI
        # categorize it later". This saves the transaction with category=None,
        # which is the genuine "unlabeled" data the semi-supervised training
        # pipeline (ai/train.py) uses for self-training. It is intentionally
        # NOT an error case.
        if category_id == '__skip__':
            category_id = None
        elif not category_id:
            messages.error(request, 'Please select a category, or choose "Not sure" to skip.')
            return redirect('add_expense_url')

        Transaction.objects.create(
            user=request.user,
            amount=request.POST.get('amount'),
            date=request.POST.get('date'),
            type='expense',
            category_id=category_id,
            description=request.POST.get('description', '')
        )

        # Check if any budget thresholds were crossed and create notifications
        check_budget_alerts(request.user)
        return redirect('history_url')

    return render(request, 'add.expense.html', {'categories': categories})


@login_required(login_url='login_url')
def add_income_view(request):
    """Save a new income transaction."""
    categories = Category.objects.all()

    if request.method == 'POST':
        error = validate_transaction(request.POST.get('amount'), request.POST.get('date'))
        if error:
            messages.error(request, error)
            return redirect('add_income_url')    # FIX: was 'add.income_url'

        category_id = request.POST.get('category')

        if category_id == '__new__':
            messages.error(request, 'Please select or create a category first.')
            return redirect('add_income_url')

        # See add_expense_view for the full explanation of this sentinel --
        # it produces genuine unlabeled data for semi-supervised training.
        if category_id == '__skip__':
            category_id = None
        elif not category_id:
            messages.error(request, 'Please select a category, or choose "Not sure" to skip.')
            return redirect('add_income_url')

        Transaction.objects.create(
            user=request.user,
            amount=request.POST.get('amount'),
            date=request.POST.get('date'),
            type='income',
            category_id=category_id,
            description=request.POST.get('description', '')
        )
        return redirect('history_url')

    return render(request, 'add.income.html', {'categories': categories})


@login_required(login_url='login_url')
def history_page(request):
    """
    Paginated transaction history with search (description / category)
    and type filter (income / expense).
    """
    tx          = Transaction.objects.filter(user=request.user).order_by('-date')
    search      = request.GET.get('search', '').strip()
    filter_type = request.GET.get('type', '')

    if search:
        tx = tx.filter(
            Q(description__icontains=search) |
            Q(category__name__icontains=search)
        )

    if filter_type in ['income', 'expense']:
        tx = tx.filter(type=filter_type)

    page_obj = Paginator(tx, 10).get_page(request.GET.get('page', 1))

    return render(request, 'history.html', {
        'page_obj':    page_obj,
        'search':      search,
        'filter_type': filter_type,
    })


@login_required(login_url='login_url')
def edit_transaction(request, pk):
    """Edit amount, description, date, and category of an existing transaction."""
    tx         = get_object_or_404(Transaction, pk=pk, user=request.user)
    categories = Category.objects.all()

    if request.method == 'POST':
        # Same validation the add-transaction forms use, so an edit can't
        # write a blank/negative amount or empty date straight into the DB.
        error = validate_transaction(request.POST.get('amount'), request.POST.get('date'))
        if error:
            messages.error(request, error)
            return redirect('edit_transaction', pk=pk)

        tx.amount      = request.POST.get('amount')
        tx.description = request.POST.get('description', '')
        tx.date        = request.POST.get('date')
        tx.category_id = request.POST.get('category') or None
        tx.save()
        messages.success(request, 'Transaction updated successfully!')
        return redirect('history_url')

    return render(request, 'edit_transaction.html', {'tx': tx, 'categories': categories})


@login_required(login_url='login_url')
def delete_transaction(request, pk):
    """Delete a single transaction (POST only for CSRF safety)."""
    if request.method == 'POST':
        get_object_or_404(Transaction, pk=pk, user=request.user).delete()
        messages.success(request, 'Transaction deleted.')
    return redirect('history_url')


@login_required(login_url='login_url')
def create_category(request):
    """
    AJAX endpoint: POST a category name, receive JSON {id, name, created}.
    Used by the inline category creator on the Add Expense / Add Income pages.
    FIX: replaced get_or_create(name__iexact=...) which caused a FieldError;
         now we filter first, then create if not found.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    name = request.POST.get('name', '').strip()

    if not name:
        return JsonResponse({'error': 'Category name cannot be empty.'}, status=400)

    if len(name) > 100:
        return JsonResponse({'error': 'Category name is too long (max 100 chars).'}, status=400)

    # Case-insensitive duplicate check, then create
    existing = Category.objects.filter(name__iexact=name).first()
    if existing:
        return JsonResponse({'id': existing.id, 'name': existing.name, 'created': False})

    category = Category.objects.create(name=name)
    return JsonResponse({'id': category.id, 'name': category.name, 'created': True})


# =============================================================================
#  ML — LIVE CATEGORY PREDICTION
# =============================================================================

# Suggestions below this confidence are still shown as a hint, but the
# frontend will NOT auto-select the dropdown for the user — too likely
# to be wrong and just annoying. Tune this once you've seen real
# predict_proba distributions on your trained model.
AUTO_APPLY_CONFIDENCE_THRESHOLD = 0.55

# Very short descriptions ("a", "gy") don't carry enough signal for TF-IDF
# to say anything meaningful — skip the model call entirely below this length.
MIN_DESCRIPTION_LENGTH = 3


@login_required(login_url='login_url')
def predict_category_ajax(request):
    """
    AJAX endpoint called (debounced) while the user types a transaction
    description on the Add Expense / Add Income pages.

    GET params: description, amount, type ('income' | 'expense')
    Returns: {"suggestion": {"id", "name", "confidence", "auto_apply"}} or
             {"suggestion": null} if no confident/available prediction.

    Read-only (GET) — no CSRF token needed, no state is modified.
    Never raises to the client: any model/lookup failure just means
    "no suggestion", so a missing/untrained model can't break the form.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    description = request.GET.get('description', '').strip()
    tx_type     = request.GET.get('type', 'expense')

    if len(description) < MIN_DESCRIPTION_LENGTH:
        return JsonResponse({'suggestion': None})

    try:
        amount = float(request.GET.get('amount') or 0)
    except ValueError:
        amount = 0.0

    try:
        label, confidence = predict_category_with_confidence(description, amount, tx_type)
    except FileNotFoundError:
        # Model hasn't been trained yet — fail silently, form still works manually.
        return JsonResponse({'suggestion': None})
    except Exception:
        # Any unexpected inference error — never let this break the Add Expense page.
        return JsonResponse({'suggestion': None})

    # The model predicts a category NAME (its training label); map it to an
    # actual Category row so the frontend can select the right <option>.
    category = Category.objects.filter(name__iexact=label).first()
    if not category:
        # Model predicts a label that no longer exists as a Category
        # (renamed/deleted since training) — nothing safe to suggest.
        return JsonResponse({'suggestion': None})

    return JsonResponse({
        'suggestion': {
            'id':         category.id,
            'name':       category.name,
            'confidence': round(confidence * 100, 1),
            'auto_apply': confidence >= AUTO_APPLY_CONFIDENCE_THRESHOLD,
        }
    })


# =============================================================================
#  AI FINANCIAL ADVISOR
# =============================================================================

@login_required(login_url='login_url')
def advisor_page(request):
    """
    Show the user's AI advice plus recent history.

    Uses the CACHED advice (get_advice) — this never calls Gemini on a normal
    page load; it only regenerates if the cache is stale. All logic lives in
    ai/advisor.py, keeping this view a thin controller.
    """
    insight = get_advice(request.user)
    history = AIInsight.objects.filter(user=request.user).order_by('-created')[:5]

    return render(request, 'advisor.html', {
        'insight': insight,
        'history': history,
    })


@login_required(login_url='login_url')
def refresh_advisor(request):
    """Manually force a fresh Gemini call (POST only), then show the result."""
    if request.method == 'POST':
        refresh_advice(request.user)
        messages.success(request, 'AI insights refreshed.')
    return redirect('advisor_url')


# =============================================================================
#  ANALYSIS & EXPORT
# =============================================================================

@login_required(login_url='login_url')
def analysis_page(request):
    """
    Financial analysis page: total income vs expenses,
    and a breakdown of expenses per category for the pie chart.
    """
    user_tx  = Transaction.objects.filter(user=request.user)
    total_in = user_tx.filter(type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    total_ex = user_tx.filter(type='expense').aggregate(Sum('amount'))['amount__sum'] or 0

    # Build category → total mapping for the doughnut chart
    expense_by_category = {}
    for t in user_tx.filter(type='expense'):
        cat_name = t.category.name if t.category else 'Other'
        expense_by_category[cat_name] = round(
            expense_by_category.get(cat_name, 0) + float(t.amount), 2
        )

    context = {
        'total_income':      round(total_in, 2),
        'total_expenses':    round(total_ex, 2),
        'balance':           round(total_in - total_ex, 2),
        'categories_labels': list(expense_by_category.keys()),
        'categories_values': list(expense_by_category.values()),
    }
    return render(request, 'analysis.html', context)


@login_required(login_url='login_url')
def export_csv(request):
    """Download all of the user's transactions as a CSV file."""
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
    response     = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transactions.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Description', 'Category', 'Amount', 'Type'])

    for t in transactions:
        writer.writerow([
            t.date,
            t.description,
            t.category.name if t.category else 'N/A',
            t.amount,
            t.type,
        ])

    return response


# =============================================================================
#  BUDGETS
# =============================================================================

@login_required(login_url='login_url')
def budgets_page(request):
    """
    Show all budgets for the current user with spending progress,
    alert flags, and over-limit detection.
    """
    budgets     = Budget.objects.filter(user=request.user)
    budget_data = []

    for b in budgets:
        # Total expenses in this budget's category
        spent = Transaction.objects.filter(
            user=request.user, category=b.category, type='expense'
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        real_percent = (spent / b.amount) * 100 if b.amount > 0 else 0
        percent      = min(real_percent, 100)   # cap bar at 100 % visually

        budget_data.append({
            'id':        b.id,
            'category':  b.category,
            'amount':    b.amount,
            'spent':     round(spent, 2),
            'remaining': round(max(b.amount - spent, 0), 2),
            'over_by':   round(max(spent - b.amount, 0), 2),
            'percent':   round(percent, 1),
            'overlimit': spent > b.amount,
            # Alert fires only when not already over the limit
            'alert':     (not spent > b.amount) and (real_percent >= b.alert_percentage),
        })

    return render(request, 'budgets.html', {'budget_data': budget_data})


@login_required(login_url='login_url')
def create_budget_view(request):
    """Create a new budget for a selected category."""
    categories = Category.objects.all()

    if request.method == 'POST':
        category_id = request.POST.get('category')

        # Validate before hitting the DB so a bad/blank value returns a clean
        # message instead of a 500 from FloatField/IntegerField coercion.
        if not category_id:
            messages.error(request, 'Please select a category.')
            return redirect('create_budget_url')

        try:
            amount = float(request.POST.get('amount'))
            if amount <= 0:
                raise ValueError
        except (TypeError, ValueError):
            messages.error(request, 'Budget amount must be a number greater than zero.')
            return redirect('create_budget_url')

        try:
            alert = int(request.POST.get('alert', 80))
            if not 0 <= alert <= 100:
                raise ValueError
        except (TypeError, ValueError):
            alert = 80   # fall back to the model default on bad input

        Budget.objects.create(
            user=request.user,
            category_id=category_id,
            amount=amount,
            alert_percentage=alert,
        )
        messages.success(request, 'Budget created successfully!')
        return redirect('budgets_url')

    return render(request, 'create_budget.html', {'categories': categories})


@login_required(login_url='login_url')
def delete_budget(request, pk):
    """Delete a budget (POST only)."""
    if request.method == 'POST':
        get_object_or_404(Budget, pk=pk, user=request.user).delete()
        messages.success(request, 'Budget deleted.')
    return redirect('budgets_url')


# =============================================================================
#  GOALS
# =============================================================================

@login_required(login_url='login_url')
def goals_page(request):
    """List all financial goals for the current user, newest first."""
    goals = Goal.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'goals.html', {'goals': goals})


@login_required(login_url='login_url')
def create_goal(request):
    """Create a new savings goal from the inline form on the goals page."""
    if request.method == 'POST':
        Goal.objects.create(
            user=request.user,
            name=request.POST.get('name'),
            target_amount=request.POST.get('target_amount'),
            deadline=request.POST.get('deadline') or None  # blank → NULL
        )
        messages.success(request, 'Goal created successfully!')
    return redirect('goals_url')


@login_required(login_url='login_url')
def add_savings(request, pk):
    """Add a savings amount to an existing goal."""
    goal = get_object_or_404(Goal, pk=pk, user=request.user)

    if request.method == 'POST':
        # Guard the float() conversion: a non-numeric string would otherwise
        # raise ValueError and 500 the page (the old `if amount:` only caught
        # the empty case).
        try:
            amount = float(request.POST.get('amount'))
        except (TypeError, ValueError):
            amount = 0

        if amount > 0:
            goal.saved_amount += amount
            goal.save()
            messages.success(request, f'${amount:.2f} added to "{goal.name}"!')
        else:
            messages.error(request, 'Please enter a valid amount to add.')

    return redirect('goals_url')


@login_required(login_url='login_url')
def delete_goal(request, pk):
    """Delete a goal (POST only)."""
    if request.method == 'POST':
        get_object_or_404(Goal, pk=pk, user=request.user).delete()
        messages.success(request, 'Goal deleted.')
    return redirect('goals_url')


# =============================================================================
#  HELPER FUNCTIONS
# =============================================================================

def validate_transaction(amount, date_str):
    """
    Validate amount and date for both income and expense forms.
    Returns an error string or None if everything is valid.
    """
    try:
        amount = float(amount)
        if amount <= 0:
            return 'Amount must be greater than zero.'
    except (TypeError, ValueError):
        return 'Invalid amount value.'

    if not date_str:
        return 'Date is required.'

    return None   # No error


def check_budget_alerts(user):
    """
    Called after every expense is saved.
    Checks all of the user's budgets and creates a Notification if a
    threshold (alert_percentage or 100 %) is crossed — but only once per day
    to avoid flooding.
    """
    budgets = Budget.objects.filter(user=user)

    for budget in budgets:
        if budget.amount <= 0:
            continue   # Skip zero-amount budgets to avoid division by zero

        spent = Transaction.objects.filter(
            user=user, category=budget.category, type='expense'
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        percent = (spent / budget.amount) * 100

        # Choose the appropriate alert message
        if percent >= 100:
            msg = (
                f'⚠️ Over budget! {budget.category} — '
                f'spent ${spent:.0f} of ${budget.amount:.0f}'
            )
        elif percent >= budget.alert_percentage:
            msg = (
                f'🔔 Budget alert! {budget.category} at {percent:.0f}% — '
                f'${spent:.0f} of ${budget.amount:.0f}'
            )
        else:
            continue   # Under threshold — no notification needed

        # Avoid duplicate notifications on the same day
        already_sent = Notification.objects.filter(
            user=user,
            message=msg,
            created__date=timezone.now().date()
        ).exists()

        if not already_sent:
            Notification.objects.create(user=user, message=msg)