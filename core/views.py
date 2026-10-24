
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.hashers import make_password
from django.db.models import Count

from .models import Category, Quiz, Question, Option, Attempt, Answer


# -----------------------------
# USER REGISTRATION
# -----------------------------
def register(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not username or not email or not password:
            messages.error(request, "Please fill in all required fields.")
            return redirect("register")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("register")

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("register")

        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, "Email already exists.")
            return redirect("register")

        User.objects.create(
            username=username,
            email=email,
            password=make_password(password),
        )

        messages.success(
            request,
            "Account created successfully. Please log in."
        )
        return redirect("login")

    return render(request, "core/register.html")


# -----------------------------
# USER LOGIN
# -----------------------------
def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome {user.username}!")
            return redirect("home")

        messages.error(request, "Invalid username or password.")
        return redirect("login")

    return render(request, "core/login.html")


# -----------------------------
# USER LOGOUT
# -----------------------------
@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("login")


# -----------------------------
# HOME PAGE
# -----------------------------
def home(request):
    categories = Category.objects.all()

    return render(
        request,
        "core/home.html",
        {"categories": categories},
    )


# -----------------------------
# QUIZZES BY CATEGORY
# -----------------------------
def category_quizzes(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    quizzes = Quiz.objects.filter(category=category)

    return render(
        request,
        "core/quizzes_by_category.html",
        {
            "category": category,
            "quizzes": quizzes,
        },
    )


# -----------------------------
# START QUIZ
# -----------------------------
@login_required
def start_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)

    if not quiz.question_set.exists():
        messages.warning(request, "This quiz has no questions yet.")
        return redirect("home")

    # Initialize a fresh quiz session.
    request.session["quiz_id"] = quiz.id
    request.session["question_index"] = 0
    request.session["score"] = 0
    request.session["answers"] = {}
    request.session.modified = True

    return redirect("attempt_quiz")


# -----------------------------
# ATTEMPT QUIZ
# -----------------------------
@login_required
def attempt_quiz(request):
    quiz_id = request.session.get("quiz_id")

    if not quiz_id:
        messages.warning(request, "Please select a quiz first.")
        return redirect("home")

    quiz = get_object_or_404(Quiz, pk=quiz_id)
    questions = quiz.question_set.all()
    total_questions = questions.count()

    if total_questions == 0:
        messages.warning(request, "This quiz has no questions.")
        return redirect("home")

    question_index = request.session.get("question_index", 0)

    if question_index >= total_questions:
        return redirect("quiz_result")

    current_question = questions[question_index]
    options = current_question.options.all()

    if request.method == "POST":
        selected_option_id = request.POST.get("option")
        answers = request.session.get("answers", {})

        # If the timer expires, no option may be selected.
        # In that case, skip the current question.
        if selected_option_id:
            selected_option = get_object_or_404(
                Option,
                pk=selected_option_id,
                question=current_question,
            )
            answers[str(current_question.id)] = selected_option.id

        request.session["answers"] = answers

        # Recalculate score from answers to avoid double-counting.
        score = 0

        for question in questions:
            option_id = answers.get(str(question.id))

            if not option_id:
                continue

            is_correct = Option.objects.filter(
                pk=option_id,
                question=question,
                is_correct=True,
            ).exists()

            if is_correct:
                score += 1

        request.session["score"] = score
        request.session["question_index"] = question_index + 1
        request.session.modified = True

        return redirect("attempt_quiz")

    return render(
        request,
        "core/quiz_attempt.html",
        {
            "quiz": quiz,
            "question": current_question,
            "options": options,
            "question_number": question_index + 1,
            "total_questions": total_questions,
        },
    )


# -----------------------------
# QUIZ RESULT AND PERSISTENCE
# -----------------------------
@login_required
def quiz_result(request):
    quiz_id = request.session.get("quiz_id")

    if not quiz_id:
        messages.warning(request, "No active quiz was found.")
        return redirect("home")

    quiz = get_object_or_404(Quiz, pk=quiz_id)
    questions = quiz.question_set.all()
    answers = request.session.get("answers", {})

    score = 0
    valid_answers = []

    # Validate each stored answer against its question.
    for question in questions:
        option_id = answers.get(str(question.id))

        if not option_id:
            continue

        option = Option.objects.filter(
            pk=option_id,
            question=question,
        ).first()

        if option is None:
            continue

        valid_answers.append((question, option))

        if option.is_correct:
            score += 1

    total_questions = questions.count()

    # Save a persistent attempt for the logged-in user.
    attempt = Attempt.objects.create(
        user=request.user,
        quiz=quiz,
        score=score,
        total=total_questions,
    )

    # Save the answers associated with this attempt.
    for question, option in valid_answers:
        Answer.objects.create(
            attempt=attempt,
            question=question,
            selected_option=option,
        )

    # Clear quiz state after saving.
    for key in (
        "score",
        "quiz_id",
        "question_index",
        "answers",
    ):
        request.session.pop(key, None)

    request.session.modified = True

    return render(
    request,
    "core/quiz_result.html",
    {
        "attempt": attempt,
        "score": score,
        "total_questions": total_questions,
        "quiz": quiz,
        "incorrect_answers": max(0, total_questions - score),
    },
)


# -----------------------------
# MY QUIZ ATTEMPTS
# -----------------------------
@login_required
def my_attempts(request):
    attempts = (
        Attempt.objects
        .filter(user=request.user)
        .select_related("quiz")
        .order_by("-completed_at")
    )

    return render(
        request,
        "core/my_attempts.html",
        {"attempts": attempts},
    )


# -----------------------------
# ADMIN DASHBOARD
# -----------------------------

@staff_member_required
def admin_dashboard(request):
    context = {
        "total_users": User.objects.count(),
        "total_quizzes": Quiz.objects.count(),
        "total_questions": sum(
            quiz.question_set.count()
            for quiz in Quiz.objects.all()
        ),
        "total_attempts": Attempt.objects.count(),
        "top_quizzes": (
            Quiz.objects.annotate(
                attempts=Count("attempt")
            ).order_by("-attempts")[:5]
        ),
    }

    return render(
        request,
        "core/admin_dashboard.html",
        context,
    )

