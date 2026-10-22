
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from .models import Category, Quiz, Question, Option, Attempt, Answer


class QuizAppTests(TestCase):
    def setUp(self):
        # Create a regular student account.
        self.user = User.objects.create_user(
            username="teststudent",
            email="student@example.com",
            password="StrongTestPass2026!",
        )

        # Create a second account for duplicate-email testing.
        self.other_user = User.objects.create_user(
            username="existingstudent",
            email="existing@example.com",
            password="OtherStrongPass2026!",
        )

        # Create quiz data.
        self.category = Category.objects.create(name="Python")

        self.quiz = Quiz.objects.create(
            title="Python Basics Quiz",
            category=self.category,
        )

        self.question = Question.objects.create(
            quiz=self.quiz,
            text="Which data structure follows FIFO?",
        )

        self.correct_option = Option.objects.create(
            question=self.question,
            text="Queue",
            is_correct=True,
        )

        self.wrong_option = Option.objects.create(
            question=self.question,
            text="Stack",
            is_correct=False,
        )

    # 1. Registration page loads.
    def test_register_page_loads(self):
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)

    # 2. Login page loads.
    def test_login_page_loads(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    # 3. A new user can register.
    def test_registration_success(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "newstudent",
                "email": "newstudent@example.com",
                "password": "NewStrongPass2026!",
                "confirm_password": "NewStrongPass2026!",
            },
        )

        self.assertRedirects(response, reverse("login"))

        new_user = User.objects.get(username="newstudent")
        self.assertEqual(new_user.email, "newstudent@example.com")
        self.assertTrue(
            new_user.check_password("NewStrongPass2026!")
        )

    # 4. Duplicate usernames are rejected.
    def test_duplicate_username_rejected(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "teststudent",
                "email": "different@example.com",
                "password": "AnotherStrongPass2026!",
                "confirm_password": "AnotherStrongPass2026!",
            },
        )

        self.assertRedirects(response, reverse("register"))
        self.assertEqual(
            User.objects.filter(username="teststudent").count(),
            1,
        )

    # 5. Duplicate email addresses are rejected.
    def test_duplicate_email_rejected(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "anotherstudent",
                "email": "student@example.com",
                "password": "AnotherStrongPass2026!",
                "confirm_password": "AnotherStrongPass2026!",
            },
        )

        self.assertRedirects(response, reverse("register"))

        self.assertFalse(
            User.objects.filter(
                username="anotherstudent"
            ).exists()
        )

    # 6. Mismatched passwords are rejected.
    def test_password_mismatch_rejected(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "mismatchstudent",
                "email": "mismatch@example.com",
                "password": "FirstStrongPass2026!",
                "confirm_password": "DifferentStrongPass2026!",
            },
        )

        self.assertRedirects(response, reverse("register"))
        self.assertFalse(
            User.objects.filter(username="mismatchstudent").exists()
        )

    # 7. A user can log in.
    def test_login_success(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "teststudent",
                "password": "StrongTestPass2026!",
            },
        )

        self.assertRedirects(response, reverse("home"))
        self.assertIn("_auth_user_id", self.client.session)

    # 8. Invalid login credentials are rejected.
    def test_invalid_login_rejected(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "teststudent",
                "password": "IncorrectPassword2026!",
            },
        )

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    # 9. Quiz attempt pages require login.
    def test_quiz_attempt_requires_login(self):
        response = self.client.get(reverse("attempt_quiz"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    # 10. My Attempts requires login.
    def test_my_attempts_requires_login(self):
        response = self.client.get(reverse("my_attempts"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    # 11. Ordinary users cannot access the admin dashboard.
    def test_admin_dashboard_requires_staff(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 302)

    # 12. Staff users can access the admin dashboard.
    def test_staff_can_access_admin_dashboard(self):
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])

        self.client.force_login(self.user)

        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 200)

    # 13. Starting a quiz requires authentication.
    def test_start_quiz_requires_login(self):
        response = self.client.get(
            reverse("start_quiz", args=[self.quiz.id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    # 14. A logged-in user can start a quiz.
    def test_logged_in_user_can_start_quiz(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("start_quiz", args=[self.quiz.id])
        )

        self.assertRedirects(response, reverse("attempt_quiz"))

        session = self.client.session
        self.assertEqual(session["quiz_id"], self.quiz.id)
        self.assertEqual(session["question_index"], 0)
        self.assertEqual(session["score"], 0)

    # 15. A logged-in user can view their own attempt history.
    def test_my_attempts_page_loads(self):
        Attempt.objects.create(
            user=self.user,
            quiz=self.quiz,
            score=1,
            total=1,
        )

        self.client.force_login(self.user)

        response = self.client.get(reverse("my_attempts"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Basics Quiz")

    # 16. Attempt history does not expose another user's attempts.
    def test_users_only_see_their_own_attempts(self):
        Attempt.objects.create(
            user=self.other_user,
            quiz=self.quiz,
            score=1,
            total=1,
        )

        self.client.force_login(self.user)

        response = self.client.get(reverse("my_attempts"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Python Basics Quiz")

    # 17. Logout ends the authenticated session.
    def test_logout_ends_session(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    # 18. A user cannot submit an option belonging to another question.
    def test_option_must_belong_to_current_question(self):
        self.client.force_login(self.user)

        # Create another question in the same quiz.
        other_question = Question.objects.create(
            quiz=self.quiz,
            text="What is Python?",
        )

        Option.objects.create(
            question=other_question,
            text="A programming language",
            is_correct=True,
        )

        session = self.client.session
        session["quiz_id"] = self.quiz.id
        session["question_index"] = 0
        session["score"] = 0
        session["answers"] = {}
        session.save()

        response = self.client.post(
            reverse("attempt_quiz"),
            {"option": Option.objects.get(
                question=other_question
            ).id},
        )

        self.assertEqual(response.status_code, 404)

