from flask import Flask, request, render_template_string
import requests
import html

app = Flask(__name__)

# HTML-Seite
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>GET Request Tester</title>
</head>
<body>
    <h1>GET Request Tester</h1>
    <form method="post">
        <label for="url">URL:</label>
        <input type="text" id="url" name="url" required>
        <button type="submit">Senden</button>
    </form>
    {% if response %}
        <h2>Response</h2>
        <textarea rows="10" cols="80">{{ response }}</textarea>
        <h2>Headers</h2>
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
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    response_text = ""
    response_headers = ""
    if request.method == "POST":
        url = request.form.get("url")
        try:
            res = requests.get(url)
            response_text = res.text
            response_headers = res.headers
        except Exception as e:
            response_text = f"Fehler: {e}"
            response_headers = ""

    return render_template_string(HTML, response=response_text, headers=response_headers)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
