"""Contratos da API: autenticação, filtros, escopo por papel e exportação."""

from __future__ import annotations

from datetime import date, timedelta

KPI_KEYS = {
    "scheduled",
    "completed",
    "attendance_rate",
    "no_show_rate",
    "cancellation_rate",
    "occupancy",
    "revenue",
    "revenue_received",
    "ticket",
    "wait_time",
    "reschedule_rate",
}


def test_login_invalido(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "gestor@clinicavida.example", "password": "senha-errada"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_endpoint_exige_token(client):
    response = client.get("/api/v1/kpis/overview")
    assert response.status_code == 401


def test_token_invalido(client):
    response = client.get(
        "/api/v1/kpis/overview", headers={"Authorization": "Bearer abc.def.ghi"}
    )
    assert response.status_code == 401


def test_meta_options(client, gestor_headers):
    response = client.get("/api/v1/meta/options", headers=gestor_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["units"]) == 3
    assert len(body["specialties"]) == 8
    assert len(body["professionals"]) == 12
    assert body["demo_today"] == "2026-10-19"
    assert "AGENDADA" in body["statuses"]
    assert body["clinic"]["name"] == "Clínica Vida Integrada"


def test_overview_kpis(client, gestor_headers):
    response = client.get("/api/v1/kpis/overview", headers=gestor_headers)
    assert response.status_code == 200
    body = response.json()
    assert {kpi["key"] for kpi in body["kpis"]} == KPI_KEYS
    assert body["period"]["end"] == "2026-10-19"
    scheduled = next(kpi for kpi in body["kpis"] if kpi["key"] == "scheduled")
    assert scheduled["value"] > 0
    assert scheduled["formula"]


def test_overview_com_filtros(client, gestor_headers):
    full = client.get("/api/v1/kpis/overview", headers=gestor_headers).json()
    filtered = client.get(
        "/api/v1/kpis/overview?unit_id=1&specialty_id=1", headers=gestor_headers
    ).json()
    full_scheduled = next(k for k in full["kpis"] if k["key"] == "scheduled")["value"]
    filtered_scheduled = next(
        k for k in filtered["kpis"] if k["key"] == "scheduled"
    )["value"]
    assert 0 < filtered_scheduled < full_scheduled


def test_periodo_invalido(client, gestor_headers):
    response = client.get(
        "/api/v1/kpis/overview?start=2026-10-19&end=2026-10-01", headers=gestor_headers
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_period"


def test_operacional(client, gestor_headers):
    response = client.get("/api/v1/kpis/operational", headers=gestor_headers)
    assert response.status_code == 200
    body = response.json()
    assert "today_scheduled" in body["counts"]
    assert len(body["next_days"]) == 7
    for task in body["tasks"]:
        assert task["rule"]
        assert task["severity"] in {"critical", "warning", "info"}


def test_timeseries(client, gestor_headers):
    response = client.get(
        "/api/v1/kpis/timeseries?granularity=week", headers=gestor_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["granularity"] == "week"
    assert body["points"]
    point = body["points"][0]
    assert {"scheduled", "completed", "no_show", "occupancy_pct"} <= set(point)


def test_breakdown_dimensoes(client, gestor_headers):
    for dimension, expected in (
        ("specialty", 8),
        ("professional", 12),
        ("unit", 3),
        ("weekday", 7),
    ):
        response = client.get(
            f"/api/v1/analytics/breakdown?dimension={dimension}", headers=gestor_headers
        )
        assert response.status_code == 200, dimension
        assert len(response.json()["items"]) == expected

    hour = client.get(
        "/api/v1/analytics/breakdown?dimension=hour", headers=gestor_headers
    )
    assert hour.status_code == 200
    assert hour.json()["items"]


def test_agenda_e_detalhe(client, gestor_headers):
    today = date.fromisoformat("2026-10-19")
    end = today + timedelta(days=6)
    response = client.get(
        f"/api/v1/appointments/agenda?start={today}&end={end}", headers=gestor_headers
    )
    assert response.status_code == 200
    agenda = response.json()
    assert agenda
    appointment_id = agenda[0]["id"]
    detail = client.get(
        f"/api/v1/appointments/{appointment_id}", headers=gestor_headers
    )
    assert detail.status_code == 200
    assert detail.json()["timeline"]


def test_lista_paginada(client, gestor_headers):
    response = client.get(
        "/api/v1/appointments?page=1&page_size=5&sort=scheduled_start&direction=asc",
        headers=gestor_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) <= 5
    assert body["total"] > 5
    assert body["pages"] > 1


def test_atendimentos(client, gestor_headers):
    response = client.get(
        "/api/v1/attendances?page_size=3", headers=gestor_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["items"]
    attendance_id = body["items"][0]["id"]
    detail = client.get(f"/api/v1/attendances/{attendance_id}", headers=gestor_headers)
    assert detail.status_code == 200
    assert detail.json()["appointment"]["patient_ref"].startswith("PAC-")


def test_escopo_do_profissional(client, gestor_headers, profissional_headers):
    options = client.get("/api/v1/meta/options", headers=gestor_headers).json()
    own = next(p for p in options["professionals"] if p["code"] == "PRO-001")
    other = next(p for p in options["professionals"] if p["code"] == "PRO-002")

    indicators = client.get(
        "/api/v1/kpis/professionals", headers=profissional_headers
    ).json()
    assert [item["professional"]["id"] for item in indicators] == [own["id"]]

    appointments = client.get(
        "/api/v1/appointments?page_size=50", headers=profissional_headers
    ).json()
    assert appointments["items"]
    assert all(
        item["professional"]["id"] == own["id"] for item in appointments["items"]
    )

    forbidden = client.get(
        f"/api/v1/professionals/{other['id']}", headers=profissional_headers
    )
    assert forbidden.status_code == 403

    own_detail = client.get(
        f"/api/v1/professionals/{own['id']}", headers=profissional_headers
    )
    assert own_detail.status_code == 200


def test_permissoes_de_exportacao_e_admin(
    client, profissional_headers, gestor_headers, admin_headers
):
    export_forbidden = client.get(
        "/api/v1/analytics/export.csv", headers=profissional_headers
    )
    assert export_forbidden.status_code == 403

    users_forbidden = client.get("/api/v1/admin/users", headers=gestor_headers)
    assert users_forbidden.status_code == 403

    users = client.get("/api/v1/admin/users", headers=admin_headers)
    assert users.status_code == 200
    assert len(users.json()) == 3

    status = client.get("/api/v1/admin/status", headers=gestor_headers)
    assert status.status_code == 200
    assert status.json()["database"] == "ok"


def test_exportacao_csv(client, gestor_headers):
    response = client.get(
        "/api/v1/analytics/export.csv?start=2026-10-01&end=2026-10-19",
        headers=gestor_headers,
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    text = response.content.decode("utf-8-sig")
    assert text.splitlines()[0].startswith("agendamento_id;data_hora_local")


def test_qualidade(client, gestor_headers):
    response = client.get("/api/v1/quality/summary", headers=gestor_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["last_run"]["rows_rejected"] == 7
    assert body["issues_by_severity"]["ERROR"] == 7
    assert body["rejected_pct"] > 0
    assert body["recent_runs"]

    issues = client.get(
        "/api/v1/quality/issues?severity=ERROR&page_size=10", headers=gestor_headers
    )
    assert issues.status_code == 200
    assert issues.json()["total"] == 7


def test_erros_padronizados(client, gestor_headers):
    not_found = client.get(
        "/api/v1/appointments/999999", headers=gestor_headers
    )
    assert not_found.status_code == 404
    assert not_found.json()["error"]["code"] == "not_found"

    bad_dimension = client.get(
        "/api/v1/analytics/breakdown?dimension=invalida", headers=gestor_headers
    )
    assert bad_dimension.status_code == 422
