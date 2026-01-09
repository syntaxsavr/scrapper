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

Regarding load tests:
Locust was used, however be VERY careful when doing this yourself, because you might rate-limit your IP from huggingfacehub - meaning you need to make an account/pay
Avoid using paths that use scrapers (self.client.get("/api/search/?q=world")) when adding more then 10 users, or leaving it to run for longer, also the first reply may take longer than subsequent replys, due to stored results in the db (the first one usually takes more like ~100ms)
locust --headless --users 8 --spawn-rate 2 -H http://127.0.0.1:8000/
<img width="1233" height="238" alt="image" src="https://github.com/user-attachments/assets/5acceada-d565-4271-9946-29ee89df45f8" />

locust --headless --users 1000 --spawn-rate 50 -H http://127.0.0.1:8000/
<img width="1237" height="205" alt="image" src="https://github.com/user-attachments/assets/c5514845-50ee-4f4b-8e69-2b910ecd6234" />
