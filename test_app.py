import pytest

from app import calculate_bmi, create_app, estimate_calories, membership_state


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    return app.test_client()


def add_ravi(client, **extra):
    data = {"name": "Ravi", "age": 25, "height": 170, "weight": 70, "program": "FL"}
    data.update(extra)
    return client.post("/clients", json=data)


# ---------- pure functions ----------
def test_estimate_calories():
    assert estimate_calories(70, "FL") == 1540
    assert estimate_calories(80, "MG") == 2800
    assert estimate_calories(60, "BG") == 1560


def test_estimate_calories_invalid():
    assert estimate_calories(0, "FL") is None
    assert estimate_calories(70, "XX") is None


def test_bmi_categories():
    assert calculate_bmi(170, 50)[1] == "Underweight"
    assert calculate_bmi(170, 70)[1] == "Normal"
    assert calculate_bmi(170, 80)[1] == "Overweight"
    assert calculate_bmi(170, 100)[1] == "Obese"


def test_bmi_invalid():
    with pytest.raises(ValueError):
        calculate_bmi(0, 70)


def test_membership_state():
    assert membership_state("Active", None) == "Active"
    assert membership_state("Active", "2000-01-01") == "Expired"
    assert membership_state("Active", "2999-01-01") == "Active"
    assert membership_state("Suspended", None) == "Suspended"


# ---------- general + programs ----------
def test_index_and_health(client):
    assert client.get("/").status_code == 200
    assert client.get("/health").json == {"status": "healthy"}


def test_list_programs(client):
    res = client.get("/programs")
    assert res.status_code == 200
    assert set(res.json) == {"FL", "MG", "BG"}


def test_get_program(client):
    res = client.get("/programs/fl")
    assert res.status_code == 200
    assert res.json["calorie_factor"] == 22


def test_program_not_found(client):
    assert client.get("/programs/XX").status_code == 404


def test_generate_program(client):
    res = client.get("/generate-program/MG")
    assert res.status_code == 200
    assert res.json["program"] == "MG"
    assert client.get("/generate-program/XX").status_code == 404


# ---------- clients ----------
def test_add_and_get_client(client):
    res = add_ravi(client)
    assert res.status_code == 201
    assert res.json["calories"] == 1540
    assert client.get("/clients/Ravi").json["program"] == "FL"
    assert len(client.get("/clients").json) == 1


def test_add_client_validation(client):
    assert client.post("/clients", json={}).status_code == 400
    assert add_ravi(client, program="ZZ").status_code == 400
    assert add_ravi(client, age="abc").status_code == 400


def test_duplicate_client(client):
    add_ravi(client)
    assert add_ravi(client).status_code == 409


def test_client_not_found(client):
    assert client.get("/clients/Nobody").status_code == 404


def test_delete_client(client):
    add_ravi(client)
    assert client.delete("/clients/Ravi").status_code == 200
    assert client.get("/clients/Ravi").status_code == 404
    assert client.delete("/clients/Ravi").status_code == 404


# ---------- progress / summary / bmi ----------
def test_progress_and_summary(client):
    add_ravi(client)
    client.post("/clients/Ravi/progress", json={"week": "W1", "adherence": 80})
    client.post("/clients/Ravi/progress", json={"week": "W2", "adherence": 60})
    res = client.get("/clients/Ravi/summary")
    assert res.json["weeks_logged"] == 2
    assert res.json["average_adherence"] == 70.0


def test_progress_validation(client):
    add_ravi(client)
    assert client.post("/clients/Ravi/progress",
                       json={"week": "W1", "adherence": 150}).status_code == 400
    assert client.post("/clients/Ravi/progress",
                       json={"week": "W1", "adherence": "x"}).status_code == 400
    assert client.post("/clients/Nobody/progress",
                       json={"week": "W1", "adherence": 50}).status_code == 404


def test_bmi_endpoint(client):
    add_ravi(client)
    res = client.get("/clients/Ravi/bmi")
    assert res.status_code == 200
    assert res.json["category"] == "Normal"


def test_bmi_missing_data(client):
    client.post("/clients", json={"name": "NoData"})
    assert client.get("/clients/NoData/bmi").status_code == 400


# ---------- workouts / membership / csv ----------
def test_workouts(client):
    add_ravi(client)
    res = client.post("/clients/Ravi/workouts",
                      json={"workout_type": "Strength", "duration_min": 45})
    assert res.status_code == 201
    assert client.get("/clients/Ravi/workouts").json[0]["workout_type"] == "Strength"
    assert client.post("/clients/Ravi/workouts", json={}).status_code == 400


def test_membership_endpoint(client):
    add_ravi(client, membership_end="2000-01-01")
    assert client.get("/clients/Ravi/membership").json["membership"] == "Expired"


def test_export_csv(client):
    add_ravi(client)
    res = client.get("/export/clients.csv")
    assert res.status_code == 200
    assert res.mimetype == "text/csv"
    assert "Ravi" in res.data.decode()
