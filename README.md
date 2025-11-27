# Scrapper
With ssokz, users can efficiently discover, explore, and compare datasets, providing an interactive dashboard for data management and analysis. Registered users can search for datasets, triggering a smart web-scraping pipeline that collects relevant metadata such as title, domain, size, and download link from multiple online sources. The results are displayed in a dashboard that supports dataset comparison, personalized views, and at a later stage statistical visualizations and user-contributed dataset entries. The system will thus serve as an intelligent, user-centric hub for dataset exploration and organization.

## PostgreSQL
### Install
#### Windows
Download from here: https://www.postgresql.org/download/windows/

#### macOS (Homebrew)
Install via Homebrew
```bash
brew install postgresql
brew services start postgresql
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### Setup
Connect to PostgreSQL:
```bash
# Windows & Linux
psql -U postgres

# macOS (Homebrew)
psql postgres

# Linux (Ubuntu/Debian)
sudo -u postgres psql
```

Once you are connected to the psql console:
```bash
CREATE DATABASE database_name;
CREATE USER user_name WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE database_name TO user_name;
```

You can setup different databases for different environments. Currently only development is supported. Be sure to create a .env.development file with the following parameters:
```bash
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=
```

### Run Migrations
After setting up the database and environment file:
```bash
python manage.py migrate

## Test Coverage
This project uses Codecov for tracking test coverage. Public reports are available at:
[https://app.codecov.io/gh/syntaxsavr/scrapper](https://app.codecov.io/gh/syntaxsavr/scrapper)
