from behave import given, when, then
from fastapi.testclient import TestClient
from server import app
import json

client = TestClient(app)

@given("die FastAPI App läuft")
def step_app_running(context):
    context.client = client

@when('ich eine GET Anfrage auf "/"')
def step_get_root(context):
    context.response = context.client.get("/")

@when('ich eine POST Anfrage auf "/" mit url "{url}"')
def step_post_root(context, url):
    context.response = context.client.post("/", data={"url": url})

@when('ich eine POST Anfrage auf "/resolve" mit hostname "{hostname}"')
def step_post_resolve(context, hostname):
    context.response = context.client.post("/resolve", data={"hostname": hostname})

@then("erhalte ich den Statuscode 200")
def step_status_200(context):
    assert context.response.status_code == 200

@then('die Antwort enthält "{text}"')
def step_response_contains(context, text):
    assert text in context.response.text

@when('ich eine POST Anfrage auf "/postbody" mit body:')
def step_post_body(context):
    body = json.loads(context.text)
    context.response = context.client.post("/postbody", json=body)
