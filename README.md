# Scraper
With ssokz, users can efficiently discover, explore, and compare datasets, providing an interactive dashboard for data management and analysis. Registered users can search for datasets, triggering a smart web-scraping pipeline that collects relevant metadata such as title, domain, size, and download link from multiple online sources. The results are displayed in a dashboard that supports dataset comparison, personalized views, and at a later stage statistical visualizations and user-contributed dataset entries. The system will thus serve as an intelligent, user-centric hub for dataset exploration and organization.

## Test Coverage
This project uses Codecov for tracking test coverage. Public reports are available at:
[https://app.codecov.io/gh/syntaxsavr/scrapper](https://app.codecov.io/gh/syntaxsavr/scrapper)

## Quick Start with Docker
### Prerequisites
- Docker
- Docker Compose

### Running the Application

1. **Clone the repository**
```bash
   git clone <your-repo-url>
   cd scrapper
```

2. **Create Environment File**
Copy and rename ```.env.example``` to ```.env``` and change the files values.

3. **Start the application**
```bash
   docker compose up --build
```

4. **Access the application**
   - Web App: http://localhost:8000
   - Admin Panel: http://localhost:8000/admin

### Stopping the Application
Press `CTRL+C` in the terminal, then:
```bash
docker compose down
```

### Clean Reset (remove all data)
```bash
docker compose down -v
```