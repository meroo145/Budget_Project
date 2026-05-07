from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from .models import Category, Budget, Transaction, Goal, Notification
import csv


# ==================== Home & Auth ====================
def home_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard_url')
    return render(request, 'home.html')

def signup_page(request):
    if request.method == 'POST':
        name     = request.POST.get('name', '').strip()
        email    = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm  = request.POST.get('confirmPassword', '')
        if password != confirm:
            messages.error(request, 'Passwords do not match!')
            return redirect('signup_url')
        if User.objects.filter(username=email).exists():
            messages.error(request, 'Email already registered!')
            return redirect('signup_url')
        user = User.objects.create_user(
            username=email, email=email,
            password=password, first_name=name
        )
        login(request, user)
        return redirect('dashboard_url')
    return render(request, 'sign.html')

def login_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard_url')
    if request.method == 'POST':
        email    = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user     = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard_url')
        messages.error(request, 'Invalid email or password!')
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('home')


# ==================== Profile & Dashboard ====================
@login_required(login_url='login_url')
def profile_page(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_info':
            request.user.first_name = request.POST.get('name', '').strip()
            request.user.email      = request.POST.get('email', '').strip()
            request.user.username   = request.user.email
            request.user.save()
            messages.success(request, 'Profile updated!')

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
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Password changed successfully!')

        return redirect('profile_url')

    user_tx  = Transaction.objects.filter(user=request.user)
    total_in = user_tx.filter(type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    total_ex = user_tx.filter(type='expense').aggregate(Sum('amount'))['amount__sum'] or 0
    context  = {
        'total_income':   round(total_in, 2),
        'total_expenses': round(total_ex, 2),
        'balance':        round(total_in - total_ex, 2),
        'total_tx':       user_tx.count(),
        'total_goals':    Goal.objects.filter(user=request.user).count(),
        'total_budgets':  Budget.objects.filter(user=request.user).count(),
    }
    return render(request, 'profile.html', context)


@login_required(login_url='login_url')
def dashboard_page(request):
    user_tx  = Transaction.objects.filter(user=request.user)
    total_in = user_tx.filter(type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    total_ex = user_tx.filter(type='expense').aggregate(Sum('amount'))['amount__sum'] or 0
    context  = {
        'total_income':   round(total_in, 2),
        'total_expenses': round(total_ex, 2),
        'balance':        round(total_in - total_ex, 2),
        'recent':         user_tx.order_by('-date')[:5],
        'goals':          Goal.objects.filter(
                              user=request.user,
                              saved_amount__lt=F('target_amount')
                          )[:3],
    }
    return render(request, 'dashboard.html', context)


# ==================== Transactions ====================
@login_required(login_url='login_url')
def add_expense_view(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        error = validate_transaction(request.POST.get('amount'), request.POST.get('date'))
        if error:
            messages.error(request, error)
            return redirect('add_expense_url')
        Transaction.objects.create(
            user=request.user,
            amount=request.POST.get('amount'),
            date=request.POST.get('date'),
            type='expense',
            category_id=request.POST.get('category'),
            description=request.POST.get('description', '')
        )
        check_budget_alerts(request.user)
        return redirect('history_url')
    return render(request, 'add.expense.html', {'categories': categories})

@login_required(login_url='login_url')
def add_income_view(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        error = validate_transaction(request.POST.get('amount'), request.POST.get('date'))
        if error:
            messages.error(request, error)
            return redirect('add.income_url')
        Transaction.objects.create(
            user=request.user,
            amount=request.POST.get('amount'),
            date=request.POST.get('date'),
            type='income',
            category_id=request.POST.get('category'),
            description=request.POST.get('description', '')
        )
        return redirect('history_url')
    return render(request, 'add.income.html', {'categories': categories})

@login_required(login_url='login_url')
def history_page(request):
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
def delete_transaction(request, pk):
    if request.method == 'POST':
        get_object_or_404(Transaction, pk=pk, user=request.user).delete()
    return redirect('history_url')

@login_required(login_url='login_url')
def edit_transaction(request, pk):
    tx         = get_object_or_404(Transaction, pk=pk, user=request.user)
    categories = Category.objects.all()
    if request.method == 'POST':
        tx.amount      = request.POST.get('amount')
        tx.description = request.POST.get('description', '')
        tx.date        = request.POST.get('date')
        tx.category_id = request.POST.get('category')
        tx.save()
        messages.success(request, 'Transaction updated!')
        return redirect('history_url')
    return render(request, 'edit_transaction.html', {'tx': tx, 'categories': categories})

@login_required(login_url='login_url')
def create_category(request):
    """
    Create a new category via AJAX request.
    Returns JSON response for frontend dynamic update.
    """

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    name = request.POST.get('name', '').strip()

    # validate empty name
    if not name:
        return JsonResponse({'error': 'Category name cannot be empty.'}, status=400)

    # prevent very long names
    if len(name) > 100:
        return JsonResponse({'error': 'Category name is too long.'}, status=400)

    # prevent duplicates (case-insensitive)
    category, created = Category.objects.get_or_create(
        name__iexact=name,
        defaults={'name': name}
    )

    return JsonResponse({
        'id': category.id,
        'name': category.name,
        'created': created
    })


# ==================== Analysis & Export ====================
@login_required(login_url='login_url')
def analysis_page(request):
    user_tx  = Transaction.objects.filter(user=request.user)
    total_in = user_tx.filter(type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    total_ex = user_tx.filter(type='expense').aggregate(Sum('amount'))['amount__sum'] or 0

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
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
    response     = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Description', 'Category', 'Amount', 'Type'])
    for t in transactions:
        writer.writerow([
            t.date, t.description,
            t.category.name if t.category else 'N/A',
            t.amount, t.type
        ])
    return response


# ==================== Budgets ====================
@login_required(login_url='login_url')
def budgets_page(request):
    budgets     = Budget.objects.filter(user=request.user)
    budget_data = []
    for b in budgets:
        spent   = Transaction.objects.filter(
            user=request.user, category=b.category, type='expense'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        percent = min((spent / b.amount) * 100, 100) if b.amount > 0 else 0
        real_percent = (spent / b.amount) * 100 if b.amount > 0 else 0
        budget_data.append({
            'id':        b.id,
            'category':  b.category,
            'amount':    b.amount,
            'spent':     round(spent, 2),
            'remaining': round(max(b.amount - spent, 0), 2),
            'over_by':   round(max(spent - b.amount, 0), 2),
            'percent':   round(percent, 1),
            'overlimit': spent > b.amount,
            'alert':     (not spent > b.amount) and (real_percent >= b.alert_percentage),
        })
    return render(request, 'budgets.html', {'budget_data': budget_data})

@login_required(login_url='login_url')
def create_budget_view(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        Budget.objects.create(
            user=request.user,
            category_id=request.POST.get('category'),
            amount=request.POST.get('amount'),
            alert_percentage=request.POST.get('alert', 80)
        )
        return redirect('budgets_url')
    return render(request, 'create_budget.html', {'categories': categories})

@login_required(login_url='login_url')
def delete_budget(request, pk):
    if request.method == 'POST':
        get_object_or_404(Budget, pk=pk, user=request.user).delete()
    return redirect('budgets_url')


# ==================== Goals ====================
@login_required(login_url='login_url')
def goals_page(request):
    goals = Goal.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'goals.html', {'goals': goals})

@login_required(login_url='login_url')
def create_goal(request):
    if request.method == 'POST':
        Goal.objects.create(
            user=request.user,
            name=request.POST.get('name'),
            target_amount=request.POST.get('target_amount'),
            deadline=request.POST.get('deadline') or None
        )
    return redirect('goals_url')

@login_required(login_url='login_url')
def add_savings(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    if request.method == 'POST':
        amount = request.POST.get('amount')
        if amount:
            goal.saved_amount += float(amount)
            goal.save()
    return redirect('goals_url')

@login_required(login_url='login_url')
def delete_goal(request, pk):
    if request.method == 'POST':
        get_object_or_404(Goal, pk=pk, user=request.user).delete()
    return redirect('goals_url')


# ==================== Helpers ====================
def validate_transaction(amount, date_str):
    try:
        amount = float(amount)
        if amount <= 0:
            return 'Amount must be greater than zero.'
    except (TypeError, ValueError):
        return 'Invalid amount.'
    if not date_str:
        return 'Date is required.'
    return None

def check_budget_alerts(user):
    budgets = Budget.objects.filter(user=user)
    for budget in budgets:
        spent = Transaction.objects.filter(
            user=user, category=budget.category, type='expense'
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        if budget.amount <= 0:
            continue

        percent = (spent / budget.amount) * 100

        if percent >= 100:
            msg = f'⚠️ Over budget! {budget.category} — spent ${spent:.0f} of ${budget.amount:.0f}'
        elif percent >= budget.alert_percentage:
            msg = f'🔔 Budget alert! {budget.category} at {percent:.0f}% — ${spent:.0f} of ${budget.amount:.0f}'
        else:
            continue

        already_sent = Notification.objects.filter(
            user=user, message=msg, created__date=timezone.now().date()
        ).exists()

        if not already_sent:
            Notification.objects.create(user=user, message=msg)