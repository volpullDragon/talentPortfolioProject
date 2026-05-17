#!/bin/bash
set -e

echo "🚀 Talent Portfolio - Automated Setup"
echo "======================================"
echo ""

choose_python() {
    local candidates=(python3.13 python3.12 python3.11 python3.10 python3 python)
    local cmd
    for cmd in "${candidates[@]}"; do
        if command -v "$cmd" >/dev/null 2>&1; then
            if "$cmd" -c "import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] < (3, 14) else 1)" >/dev/null 2>&1; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

# Find supported Python version (3.10 to 3.13)
if ! PY_CMD=$(choose_python); then
    echo "❌ No supported Python version found."
    echo "   Required: Python >=3.10 and <3.14"
    echo "   Installed versions checked: python3.13, python3.12, python3.11, python3.10, python3, python"
    exit 1
fi

echo "✅ Python selected: $($PY_CMD --version)"
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
"$PY_CMD" -m venv .venv
source .venv/bin/activate
PYTHON_BIN="$(pwd)/.venv/bin/python"

# Upgrade pip
echo "📦 Upgrading pip..."
"$PYTHON_BIN" -m pip install --upgrade pip

# Install dependencies
echo "📦 Installing dependencies..."
"$PYTHON_BIN" -m pip install -r talentPortfolio/requirements.txt

# Create .env file if it doesn't exist
cd talentPortfolio
if [ ! -f .env ]; then
    echo ""
    echo "🔐 Creating .env file..."
    "$PYTHON_BIN" -c "from django.core.management.utils import get_random_secret_key; print(f'SECRET_KEY={get_random_secret_key()}')" > .env
    echo "DEBUG=True" >> .env
    echo "✅ .env file created with a generated SECRET_KEY"
else
    echo "✅ .env file already exists"
fi

# Run migrations
echo ""
echo "🗄️  Applying database migrations..."
"$PYTHON_BIN" manage.py migrate

# Generate test data
echo ""
echo "📊 Populate database with users? (2 student users per course & 1 faculty user per course total courses: 229) (y/n)"
read -r generate_data
if [ "$generate_data" = "y" ] || [ "$generate_data" = "Y" ]; then
    echo ""
    echo "🎓 Generating student test data (2 student per course)..."
    "$PYTHON_BIN" manage.py generate_student_stress_test_data --students-per-course 2

    echo ""
    echo "👨‍💼 Generating faculty test data (1 faculty per course)..."
    "$PYTHON_BIN" manage.py generate_faculty_stress_test_data

    echo "✅ Test data generated successfully!"
fi

# Create superuser prompt
echo ""
echo "👤 Create a superuser account for admin access? (y/n)"
read -r create_superuser
if [ "$create_superuser" = "y" ] || [ "$create_superuser" = "Y" ]; then
    "$PYTHON_BIN" manage.py createsuperuser
fi

# Start the server
echo ""
echo "🎉 Setup complete! Starting development server..."
echo ""
echo "📍 Application: http://127.0.0.1:8000/"
echo "📍 Admin Panel: http://127.0.0.1:8000/admin/"
echo ""
"$PYTHON_BIN" manage.py collectstatic --noinput
"$PYTHON_BIN" manage.py runserver
