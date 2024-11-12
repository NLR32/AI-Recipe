# app.py
import os
from dotenv import load_dotenv
from flask import Flask, render_template, request
from markupsafe import Markup
from google.oauth2 import service_account
import google.generativeai as genai
import re
import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
import random

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
    # Extract title from the text (between ## markers)
    title_pattern = r'##(.*?)##'
    title_match = re.search(title_pattern, text)
    title = title_match.group(1).strip() if title_match else "Recipe"
    
    # Format the rest of the text
    formatted_text = re.sub(title_pattern, r'<h1>\1</h1>\n', text)
    bold_pattern = r'\*\*(.*?)\*\*'
    formatted_text = re.sub(bold_pattern, r'\n<strong>\1</strong>\n', formatted_text)
    single_pattern = r'\~(.*?)\~'
    formatted_text = re.sub(single_pattern, r'\1<br>', formatted_text)
    
    return formatted_text, title

def get_related_recipes(recipe_title):
    # Headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Search for similar recipes on food websites
    related_recipes = []
    search_query = urllib.parse.quote(f"{recipe_title} recipe")
    
    # Try different recipe websites
    sites = [
        ('https://www.allrecipes.com/search?q=', '.card__title-text', '.card__image img'),
        ('https://www.food.com/search/', '.title a', '.recipe-image img'),
        ('https://www.simplyrecipes.com/search?q=', '.card__title', '.card__image img')
    ]
    
    for base_url, title_selector, img_selector in sites:
        try:
            response = requests.get(f"{base_url}{search_query}", headers=headers, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find recipe cards/links
                recipe_elements = soup.select(title_selector)[:2]  # Get first 2 recipes from each site
                
                for element in recipe_elements:
                    title = element.get_text().strip()
                    
                    # Try to find an image for the recipe
                    img_url = '/api/placeholder/300/200'  # Default placeholder
                    if img_selector:
                        img_element = soup.select_one(img_selector)
                        if img_element and img_element.get('src'):
                            img_url = img_element['src']
                    
                    # Only add if we found a valid title
                    if title and len(title) > 3:
                        related_recipes.append({
                            'title': title,
                            'image_url': img_url,
                            'source': base_url.split('.')[1].capitalize()
                        })
            
            # Add a small delay between requests to be polite
            time.sleep(random.uniform(0.5, 1.5))
            
        except Exception as e:
            print(f"Error fetching from {base_url}: {str(e)}")
            continue
    
    # If we couldn't find any recipes, add some generic ones
    if not related_recipes:
        related_recipes = [
            {
                'title': f"Similar {recipe_title}",
                'image_url': '/api/placeholder/300/200',
                'source': 'Suggested Recipe'
            }
        ]
    
    return related_recipes[:5]  # Return up to 5 related recipes

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
        - Each instruction being numbered
        - Each instruction preceded and followed by a single ~
        - Tips section marked with **Tips:**"""
        
        response = model.generate_content(prompt)
        raw_recipe = response.text
        
        # Format the recipe and get the title
        formatted_recipe, recipe_title = format_recipe(raw_recipe)
        
        # Get related recipes based on the generated title
        related_recipes = get_related_recipes(recipe_title)
        
        # Mark the formatted recipe as safe HTML
        formatted_recipe = Markup(formatted_recipe)
        
        return render_template('index.html', 
                             recipe=formatted_recipe, 
                             related_recipes=related_recipes,
                             generated_title=recipe_title)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)