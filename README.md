
# ACEest Fitness & Gym

A Flask web application for fitness and gym management, built for the
Introduction to DevOps assignment. It exposes a JSON API for workout/diet
programs, clients, weekly progress, BMI, workout logs, membership and CSV
export. The logic is ported from the ACEest desktop versions (v1.0 to v3.2.4).

The project also demonstrates a complete DevOps workflow: Git/GitHub, Pytest,
Docker, a Jenkins build and a GitHub Actions CI pipeline.

## Prerequisites

- Python 3.9 or newer (with pip)
- Git
- Docker (only needed for the Docker steps)

On Windows use python and pip instead of python3 and pip3.

## Project structure

- app.py - Flask application
- test_app.py - Pytest unit tests (23 tests)
- requirements.txt - Python dependencies (Flask, pytest, flake8)
- Dockerfile - container image definition
- .github/workflows/main.yml - GitHub Actions CI pipeline

## Run locally

git clone https://github.com/Rishi0611-ui/access-fitness.git
cd access-fitness
pip3 install -r requirements.txt
python3 app.py

The app starts on port 5000. Open http://localhost:5000/programs in a browser.
If you see the three programs (FL, MG, BG), the app is working. Press Ctrl+C
in the terminal to stop it. Data is stored in a local SQLite file
(aceest_fitness.db), which is created automatically.

## Try the API

With the app running, open a second terminal:

curl http://localhost:5000/health
curl http://localhost:5000/programs/FL

curl -X POST http://localhost:5000/clients \
-H "Content-Type: application/json" \
-d '{"name": "Ravi", "age": 25, "height": 170, "weight": 70, "program": "FL"}'

curl -X POST http://localhost:5000/clients/Ravi/progress \
-H "Content-Type: application/json" \
-d '{"week": "W1", "adherence": 80}'

curl http://localhost:5000/clients/Ravi/summary
curl http://localhost:5000/clients/Ravi/bmi

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| GET | /version | App name and version |
| GET | /programs | List programs (FL, MG, BG) |
| GET | /programs/<code> | Workout, diet and calorie factor |
| GET | /generate-program/<code> | Random program suggestion |
| POST | /clients | Add a client (calories are calculated) |
| GET | /clients, /clients/<name> | List clients / get one client |
| DELETE | /clients/<name> | Delete a client |
| POST | /clients/<name>/progress | Log weekly adherence (0-100) |
| GET | /clients/<name>/summary | Weeks logged and average adherence |
| GET | /clients/<name>/bmi | BMI, category and risk note |
| POST, GET | /clients/<name>/workouts | Log and list workouts |
| GET | /clients/<name>/membership | Membership status |
| GET | /export/clients.csv | Download all clients as CSV |

## Run the tests manually

pip3 install -r requirements.txt
python3 -m pytest -v

All 23 tests should pass. Each test uses its own temporary database, so your
local data is never touched.

## Run with Docker

docker build -t aceest-fitness .
docker run -d -p 5000:5000 --name aceest aceest-fitness

Open http://localhost:5000/health to check it. Run the tests inside the
container and clean up:

docker run --rm aceest-fitness python -m pytest -q
docker stop aceest && docker rm aceest

The image is based on python:3.12-slim, installs dependencies before copying
the code (better layer caching) and runs as a non-root user.

## CI/CD overview

### GitHub Actions
The workflow .github/workflows/main.yml runs on every push and pull request:

1. Check out the code and set up Python.
2. Install dependencies and lint with flake8 (build and lint stage).
3. Build the Docker image.
4. Run the Pytest suite inside the container.

The run must be green before a pull request is merged into main.

### Jenkins
A Freestyle Jenkins project acts as a second, independent build check:

1. Source Code Management: Git, repository
https://github.com/Rishi0611-ui/access-fitness.git, branch */main.
2. Build step (Execute shell):
   python3 -m venv venv
        . venv/bin/activate
        pip install -r requirements.txt
        python -m pytest -q

3. Click Build Now. The build is successful when the console output ends with
   all tests passed and Finished: SUCCESS.

A virtual environment is used so the build does not depend on packages
installed on the Jenkins server.

### Version control
Changes are committed in small steps with descriptive messages. New work is
done on a feature branch (for example feature-add-version), pushed to
GitHub, checked by GitHub Actions in a pull request and then merged into
main.
   
