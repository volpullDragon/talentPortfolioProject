# Talent Portfolio - Django Assessment Project

A Django portfolio management system for students and faculty.

## Requirements

- Python 3.10 to 3.13
- Windows, macOS, or Linux

## Fastest Setup (Recommended)

### 1. Extract the zip

Extract the submission folder to a local directory.

### 2. Run the setup script from the project root

macOS or Linux:

```bash
./setup.sh
```

If needed:

```bash
chmod +x setup.sh
./setup.sh
```

Windows (PowerShell or Command Prompt):

```powershell
.\setup.bat
```

### 3. Follow prompts

The setup script will:

- Detect a supported Python version automatically
- Create `.venv`
- Install dependencies from `talentPortfolio/requirements.txt`
- Create `talentPortfolio/.env` if missing
- Run migrations
- Optionally generate stress test data
- Optionally create a superuser
- Start the development server

Application URLs:

- App: <http://127.0.0.1:8000/>
- Admin: <http://127.0.0.1:8000/admin/>
