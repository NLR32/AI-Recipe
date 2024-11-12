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
import json

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv("/home/nlrose32/.env")

# Path to the service account key file
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")  # Custom Search Engine ID
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # API Key for Custom Search API

# Authenticate using the JSON key file
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)

# Configure the Gemini API client using the credentials
genai.configure(api_key=credentials.token)

# def get_google_image(query):
#     """Fetch an image URL from Google Custom Search API"""
#     try:
#         # Add "food" to the query to get more relevant results
#         search_query = f"{query} food recipe"
#         url = f"https://www.googleapis.com/customsearch/v1"
#         params = {
#             'key': GOOGLE_API_KEY,
#             'cx': GOOGLE_CSE_ID,
#             'q': search_query,
#             'searchType': 'image',
#             'num': 1,
#             'imgSize': 'MEDIUM',
#             'safe': 'active'
#         }
        
#         response = requests.get(url, params=params)
#         if response.status_code == 200:
#             data = response.json()
#             if 'items' in data and len(data['items']) > 0:
#                 return data['items'][0]['link']
#     except Exception as e:
#         print(f"Error fetching image: {str(e)}")
    
#     return '/api/placeholder/300/200'

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
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    related_recipes = []
    search_query = urllib.parse.quote(f"{recipe_title} recipe")
    
    # sites = [
    #     ('https://www.allrecipes.com/search?q=', '.card__title-text', 'a.card__titleLink'),
    #     ('https://www.food.com/search/', '.title a', 'a.title'),
    #     ('https://www.simplyrecipes.com/search?q=', '.card__title', 'a.card__titleLink')
    # ]
    base_url = "https://www.simplyrecipes.com/search?q="
    # for base_url, title_selector, link_selector in sites:
    try:

        response = requests.get(f"{base_url}{search_query}", headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find recipe cards/links
            titles = soup.find_all("span", {"class": "card__underline"})
            links  = soup.find_all("a", {"class": "comp card"})
            images = soup.find_all("img", {"class": "card__image"})

            # get rid of None's found
            sources = []
            for i in images:
                src = i.get("src")
                if i is not None:
                    sources.append(i)
            
            
            for i in range(0,min(len(links), len(titles), len(sources))):
                related_recipes.append({
                    'title': titles[i],
                    'image_url': sources[i],
                    'link': links[i]
                })
            print(related_recipes)
        
        time.sleep(random.uniform(0.5, 1.5))
        
    except Exception as e:
        print(f"Error fetching from {base_url}: {str(e)}")

    
    # If we couldn't find any recipes, add some generic ones
    if not related_recipes:
        related_recipes = [
            {
                'title': f"Similar {recipe_title}",
                'image_url': '/api/placeholder/300/200',
                'source': 'Suggested Recipe',
                'link': '#'
            }
        ]
    
    return related_recipes

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        ingredients = request.form['ingredients']

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
        
        formatted_recipe, recipe_title = format_recipe(raw_recipe)
        related_recipes = get_related_recipes(recipe_title)
        
        formatted_recipe = Markup(formatted_recipe)
        
        return render_template('index.html', 
                             recipe=formatted_recipe, 
                             related_recipes=related_recipes,
                             generated_title=recipe_title)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)