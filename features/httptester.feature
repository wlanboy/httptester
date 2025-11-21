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
    When ich eine POST Anfrage auf "/resolve" mit hostname "unbekannt.local"
    Then erhalte ich den Statuscode 200
    And die Antwort enthält "Fehler"
