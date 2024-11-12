
# import os
# from dotenv import load_dotenv
# from flask import Flask, render_template, request
# from markupsafe import Markup
# from google.oauth2 import service_account
# import google.generativeai as genai
# import re

# app = Flask(__name__)

# # Load environment variables from .env file
# load_dotenv("/home/nlrose32/.env")

# # Path to the service account key file
# SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# # Authenticate using the JSON key file
# credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)

# # Configure the Gemini API client using the credentials
# genai.configure(api_key=credentials.token)

# def format_recipe(text):
#     # First, handle the title (## pattern)
#     title_pattern = r'##(.*?)##'
#     formatted_text = re.sub(title_pattern, r'<h1>\1</h1>\n', text)
    
#     # Handle double asterisks (bold text)
#     bold_pattern = r'\*\*(.*?)\*\*'
#     formatted_text = re.sub(bold_pattern, r'\n<strong>\1</strong>\n', formatted_text)
    
#     # Handle single ~ (new line after)
#     single_pattern = r'\~(.*?)\~'
#     formatted_text = re.sub(single_pattern, r'\1<br>', formatted_text)
    
#     return formatted_text

# @app.route('/', methods=['GET', 'POST'])
# def index():
#     if request.method == 'POST':
#         # Get the user-provided ingredients
#         ingredients = request.form['ingredients']

#         # Use the GEMINI API to generate a recipe
#         model = genai.GenerativeModel("gemini-1.5-flash")
#         prompt = f"""Generate a recipe using these ingredients: {ingredients}. 
#         Format the recipe with:
#         - Title preceded and followed by ##
#         - Ingredients section marked with **Ingredients:**
#         - Each ingredient being numbered
#         - Each ingredient preceded and followed by a single ~
#         - Instructions section marked with **Instructions:**, 
#         - Each instuction being numbered
#         - Each instruction preceded and followed by a single ~
#         - Tips section marked with **Tips:**"""
        
#         response = model.generate_content(prompt)
#         raw_recipe = response.text
        
#         # Format the recipe using our regex function
#         formatted_recipe = format_recipe(raw_recipe)
        
#         # Mark the formatted recipe as safe HTML
#         formatted_recipe = Markup(formatted_recipe)
        
#         return render_template('index.html', recipe=formatted_recipe)

#     return render_template('index.html')

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=8080, debug=True)

import os
from dotenv import load_dotenv
from flask import Flask, render_template, request
from markupsafe import Markup
from google.oauth2 import service_account
import google.generativeai as genai
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv("/home/nlrose32/.env")

# Path to the service account key file
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Authenticate using the JSON key file
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)

# Configure the Gemini API client using the credentials
genai.configure(api_key=credentials.token)

def get_related_recipes(recipe_title):
    """Search for related recipes and return their titles, URLs, and images"""
    try:
        clean_title = re.sub(r'<[^>]+>', '', recipe_title)
        search_query = quote_plus(f"{clean_title} recipe")
        
        # Search AllRecipes.com
        url = f"https://www.allrecipes.com/search?q={search_query}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        recipe_links = []
        # Find recipe cards - adjust selectors based on the website's structure
        recipe_cards = soup.find_all('div', class_='card__recipe', limit=10)  # Adjust class name as needed
        
        for card in recipe_cards:
            try:
                link = card.find('a', class_='card__titleLink')
                img = card.find('img', class_='card__image')  # Adjust class name as needed
                
                if link and img:
                    recipe_links.append({
                        'title': link.get_text().strip(),
                        'url': link['href'],
                        'image_url': img.get('data-src', img.get('src', '/static/default-recipe.jpg'))
                    })
            except Exception as e:
                print(f"Error processing recipe card: {e}")
                continue
                
        return recipe_links

    except Exception as e:
        print(f"Error fetching related recipes: {e}")
        return []

def fetch_recipe_image(url):
    """Try to fetch a recipe image from a recipe page"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for recipe image - adjust selectors based on the website's structure
        img = soup.find('img', class_='recipe-image')  # Adjust class name as needed
        if img:
            image_url = img.get('data-src', img.get('src'))
            if image_url:
                return urljoin(url, image_url)
    except Exception as e:
        print(f"Error fetching recipe image: {e}")
    return None

def format_recipe(text):
    # Extract title for related recipes search
    title_match = re.search(r'##\s*(.*?)(?=\*|$)', text)
    recipe_title = title_match.group(1) if title_match else ""
    
    # Format title
    title_pattern = r'##\s*(.*?)(?=\*|$)'
    formatted_text = re.sub(title_pattern, r'<h1>\1</h1>\n', text)
    
    # Handle double asterisks (bold text)
    bold_pattern = r'\*\*(.*?)\*\*'
    formatted_text = re.sub(bold_pattern, r'\n<strong>\1</strong>\n', formatted_text)
    
    # Handle single asterisks (new line after)
    single_pattern = r'\*(.*?)\*'
    formatted_text = re.sub(single_pattern, r'\1<br>', formatted_text)
    
    return formatted_text, recipe_title

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        ingredients = request.form['ingredients']

        # Use the GEMINI API to generate a recipe
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""Generate a recipe using these ingredients: {ingredients}. 
        Format the recipe with:
        - Title preceded by ##
        - Ingredients section marked with **Ingredients:**
        - Each ingredient preceded by a single *
        - Instructions section marked with **Instructions:**
        - Tips section marked with **Tips:**"""
        
        response = model.generate_content(prompt)
        raw_recipe = response.text
        
        # Format the recipe and get the title
        formatted_recipe, recipe_title = format_recipe(raw_recipe)
        
        # Get related recipes with images
        related_recipes = get_related_recipes(recipe_title)
        
        # Mark the formatted recipe as safe HTML
        formatted_recipe = Markup(formatted_recipe)
        
        return render_template('index.html', recipe=formatted_recipe, related_recipes=related_recipes)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)