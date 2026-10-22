
# Django Quiz App

A web-based quiz application built with Django, Python, HTML, CSS, and JavaScript.

## Features

- User registration and login
- Quiz categories
- Interactive quiz attempts
- Automatic score calculation
- Quiz results
- Attempt history
- Admin dashboard with quiz statistics
- Django admin integration

## Tech Stack

- Backend: Python, Django
- Frontend: HTML, CSS, JavaScript
- Database: SQLite
- Version Control: Git and GitHub

## Installation and Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/sudhakarbhardwaj540/django-quiz-app.git
   cd django-quiz-app
   ```

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install Django:

   ```bash
   pip install django
   ```

4. Apply database migrations:

   ```bash
   python manage.py migrate
   ```

5. Create an administrator account:

   ```bash
   python manage.py createsuperuser
   ```

6. Start the development server:

   ```bash
   python manage.py runserver
   ```

7. Open http://127.0.0.1:8000 in your browser.

## Testing

Run the test suite:

```bash
python manage.py test core
```

## Author

Sudhakar Kumar
