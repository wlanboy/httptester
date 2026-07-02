Feature: Testen der FastAPI App

  Scenario: GET Anfrage auf Home
    Given die FastAPI App läuft
    When ich eine GET Anfrage auf "/"
    Then erhalte ich den Statuscode 200

  Scenario: POST Anfrage mit gültiger URL
    Given die FastAPI App läuft
    When ich eine POST Anfrage auf "/" mit url "https://google.de"
    Then erhalte ich den Statuscode 200
    And die Antwort enthält "google"

  Scenario: POST Anfrage mit ungültiger URL
    Given die FastAPI App läuft
    When ich eine POST Anfrage auf "/" mit url "http://nicht-existierend.local"
    Then erhalte ich den Statuscode 200
    And die Antwort enthält "Fehler"

  Scenario: Hostname erfolgreich auflösen
    Given die FastAPI App läuft
    When ich eine POST Anfrage auf "/resolve" mit hostname "localhost"
    Then erhalte ich den Statuscode 200
    And die Antwort enthält "127.0.0.1"

  Scenario: Hostname nicht auflösbar
    Given die FastAPI App läuft
    When ich eine POST Anfrage auf "/resolve" mit hostname "nonexistent.invalid"
    Then erhalte ich den Statuscode 200
    And die Antwort enthält "Fehler"

  Scenario: POST Anfrage mit JSON Body
    Given die FastAPI App läuft
    When ich eine POST Anfrage auf "/postbody" mit body:
      """
      {"message": "Hallo Welt", "value": 42}
      """
    Then erhalte ich den Statuscode 200
    And die Antwort enthält "Hallo Welt"
    And die Antwort enthält "42"

  Scenario: GET-Methode gegen /healthz einer anderen Instanz klappt
    Given die FastAPI App läuft
    When ich eine erweiterte POST Anfrage auf "/" mit url "http://127.0.0.1:5091/healthz", method "GET", timeout "3" und header "X-Test: abc"
    Then erhalte ich den Statuscode 200
    And die Antwort enthält "ok"

  Scenario: Nicht erlaubte Methode gegen /healthz liefert 405 in der Antwort
    Given die FastAPI App läuft
    When ich eine erweiterte POST Anfrage auf "/" mit url "http://127.0.0.1:5091/healthz", method "PUT", timeout "3" und header "X-Test: abc"
    Then erhalte ich den Statuscode 200
    And die Antwort enthält "Method Not Allowed"

  Scenario: Chain über zwei weitere Instanzen läuft komplett durch
    Given die FastAPI App läuft
    When ich eine POST Anfrage auf "/chain" mit chain ["http://127.0.0.1:5091", "http://127.0.0.1:5092"]
    Then erhalte ich den Statuscode 200
    And der final_status ist 200
    And der path enthält 2 hops

  Scenario: Chain bricht bei nicht erreichbarem Hop sauber ab
    Given die FastAPI App läuft
    When ich eine POST Anfrage auf "/chain" mit chain ["http://127.0.0.1:5999"]
    Then erhalte ich den Statuscode 200
    And der final_status ist 502
    And der path enthält 1 hops
