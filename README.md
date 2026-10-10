# ACEest Fitness & Gym

A Flask web application for fitness and gym management, built as part of the
Introduction to DevOps assignment. The app logic is ported from the ACEest
desktop versions (v1.0 to v3.2.4) and exposes a JSON API for programs,
clients, weekly progress, BMI, workouts, membership and CSV export.

## Project structure

- app.py - Flask application
- test_app.py - Pytest unit tests
- requirements.txt - Python dependencies
- Dockerfile - container image definition
- .github/workflows/main.yml - GitHub Actions CI pipeline

## Run locally

    git clone https://github.com/Rishi0611-ui/access-fitness.git
    cd access-fitness
    pip3 install -r requirements.txt
    python3 app.py

Open http://localhost:5000/programs in a browser.

## Main endpoints

- GET /health - health check
- GET /programs, GET /programs/<FL|MG|BG> - workout and diet programs
- GET /generate-program/<code> - random program suggestion
- POST /clients, GET /clients, GET /clients/<name> - client management
- POST /clients/<name>/progress, GET /clients/<name>/summary - weekly adherence
- GET /clients/<name>/bmi - BMI and risk info
- POST/GET /clients/<name>/workouts - workout log
- GET /clients/<name>/membership - membership status
- GET /export/clients.csv - CSV export

## Run the tests manually

    python3 -m pytest -v

## Run with Docker

    docker build -t aceest-fitness .
    docker run -d -p 5000:5000 --name aceest aceest-fitness
    docker run --rm aceest-fitness python -m pytest -q

## CI/CD overview

### GitHub Actions
The workflow in .github/workflows/main.yml runs on every push and pull
request. It checks out the code, installs dependencies, lints with flake8,
builds the Docker image and runs the Pytest suite inside the container.

### Jenkins
A Freestyle Jenkins project pulls the latest code from this GitHub repository
(branch main) and performs a clean build. The build script creates a Python
virtual environment, installs requirements.txt and runs Pytest. A build is
successful when all tests pass.

### Version control
Work is committed in small steps with clear messages and pushed to the main
branch on GitHub.
