import os
from dotenv import load_dotenv
from flask import Flask, render_template, request
from markupsafe import Markup
from google.oauth2 import service_account
import google.generativeai as genai
import re
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv("/home/nlrose32/.env")

# Path to the service account key file
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Authenticate using the JSON key file
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)

# Configure the Gemini API client using the credentials
genai.configure(api_key=credentials.token)

def format_recipe(text):
    # First, handle the title (## pattern)
    title_pattern = r'##(.*?)##'
    formatted_text = re.sub(title_pattern, r'<h1>\1</h1>\n', text)
    
    # Handle double asterisks (bold text)
    bold_pattern = r'\*\*(.*?)\*\*'
    formatted_text = re.sub(bold_pattern, r'\n<strong>\1</strong>\n', formatted_text)
    
    # Handle single ~ (new line after)
    single_pattern = r'\~(.*?)\~'
    formatted_text = re.sub(single_pattern, r'\1<br>', formatted_text)
    
    return formatted_text

def get_related_recipes(main_ingredients):
    # Use Gemini to generate related recipe titles
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"Generate 5 different recipe names that use similar ingredients to: {main_ingredients}. Format as a simple comma-separated list."
    
    response = model.generate_content(prompt)
    recipe_titles = [title.strip() for title in response.text.split(',')]
    
    related_recipes = []
    for title in recipe_titles:
        related_recipes.append({
            'title': title,
            'image_url': f'/api/placeholder/300/200',  # Using placeholder images
            'description': f'A delicious recipe featuring similar ingredients to your search.'
        })
    
    return related_recipes

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get the user-provided ingredients
        ingredients = request.form['ingredients']

        # Use the GEMINI API to generate a recipe
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""Generate a recipe using these ingredients: {ingredients}. 
        Format the recipe with:
        - Title preceded and followed by ##
        - Ingredients section marked with **Ingredients:**
        - Each ingredient being numbered
        - Each ingredient preceded and followed by a single ~
        - Instructions section marked with **Instructions:**, 
        - Each instuction being numbered
        - Each instruction preceded and followed by a single ~
        - Tips section marked with **Tips:**"""
        
        response = model.generate_content(prompt)
        raw_recipe = response.text
        
        # Format the recipe using our regex function
        formatted_recipe = format_recipe(raw_recipe)
        
        # Get related recipes
        related_recipes = get_related_recipes(ingredients)
        
        # Mark the formatted recipe as safe HTML
        formatted_recipe = Markup(formatted_recipe)
        
        return render_template('index.html', recipe=formatted_recipe, related_recipes=related_recipes)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)