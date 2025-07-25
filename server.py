from flask import Flask, request, g, render_template_string
import requests
import socket
import html
import logging

app = Flask(__name__)

# access logs
access_logger = logging.getLogger('http_access')
access_logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(remote_addr)s - %(method)s %(path)s - %(status)s - %(response_length)s bytes - %(user_agent)s')
# Configure StreamHandler to print logs to console (stdout)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
access_logger.addHandler(console_handler)

@app.before_request
def log_request_info():
    g.start_time = request.date
    g.remote_addr = request.remote_addr
    g.method = request.method
    g.path = request.path
    g.user_agent = request.headers.get('User-Agent', 'N/A')

@app.after_request
def log_response_info(response):
    response_length = len(response.data) if response.data else 0
    status_code = response.status_code

    # Log the access
    access_logger.info(
        '',
        extra={
            'remote_addr': g.remote_addr,
            'method': g.method,
            'path': g.path,
            'status': status_code,
            'response_length': response_length,
            'user_agent': g.user_agent
        }
    )
    return response

# HTML-Seite
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>GET Request Tester</title>
</head>
<body>
    <h1>GET Request Tester</h1>
    <p>Send GET Request from pod</p>
    <form method="post" action="/">
        <label for="url">URL:</label>
        <input type="text" id="url" name="url" required>
        <button type="submit">Senden</button>
    </form>
    <br/>
    <p>or lookup a hostname from pod</p>
    <br/>
    <form method="post" action="/resolve">
        <label for="hostname">hostname:</label>
        <input type="text" id="hostname" name="hostname" required>
        <button type="submit">Senden</button>
    </form>
    {% if response %}
        <h2>Response</h2>
        <textarea rows="10" cols="80">{{ response }}</textarea>
        {% if headers %}
            <h2>headers</h2>
            <textarea rows="10" cols="80">{{ headers }}</textarea>
            <table border="1">
                <tr>
                    <th>Key</th>
                    <th>Value</th>
                </tr>
                {% for key, value in headers.items() %}
                <tr>
                    <td>{{ key }}</td>
                    <td>{{ value }}</td>
                </tr>
                {% endfor %}
            </table>
        {% endif %}
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    response_text = ""
    response_headers = {}
    if request.method == "POST":
        url = request.form.get("url")
        try:
            res = requests.get(url, timeout=5)
            response_text = res.text
            response_headers = res.headers
        except requests.exceptions.Timeout:
            response_text = f"Timeout: {e}"
            response_headers = ""
        except Exception as e:
            response_text = f"Fehler: {e}"
            response_headers = ""

    return render_template_string(HTML, response=response_text, headers=response_headers)

@app.route('/resolve', methods=['GET', 'POST'])
def resolve():
    hostname = None
    ip_address = None
    error = None
    response_headers = {}

    if request.method == 'POST':
        hostname = request.form.get('hostname')
        if hostname:
            try:
                ip_address = socket.gethostbyname(hostname)
                response_text = f"Hostname: {html.escape(hostname)} IP-Adresse: {html.escape(ip_address)}"
            except socket.gaierror as e:
                error = f"Fehler beim Auflösen des Hostnamens '{hostname}': {e}"
                response_text = f"Fehler beim Auflösen des Hostnamens '{hostname}': {e}"
            except Exception as e:
                error = f"Ein unerwarteter Fehler ist aufgetreten: {e}"
                response_text = f"Ein unerwarteter Fehler ist aufgetreten: {e}"
        else:
            error = "Bitte geben Sie einen Hostnamen ein."

    return render_template_string(HTML, response=response_text, headers=response_headers)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
