import os
from dotenv import load_dotenv
from flask import Flask, render_template, request
from google.oauth2 import service_account
import google.generativeai as genai

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv("/home/nlrose32/.env")

# Path to the service account key file
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Authenticate using the JSON key file
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)

# Configure the Gemini API client using the credentials
genai.configure(api_key=credentials.token)  # Ensure this works for the generative API

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get the user-provided ingredients
        ingredients = request.form['ingredients']

        # Use the GEMINI API to generate a recipe
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"Give a recipie using the following ingredients{ingredients}. Use newline characters to format the response.")
        recipe = response.text

        return render_template('index.html', recipe=recipe)

    return render_template('index.html')

# @app.route('/static/style.css')
# def serve_static(filename):
#     return send_from_directory(os.path.join(app.root_path, 'static'), filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
