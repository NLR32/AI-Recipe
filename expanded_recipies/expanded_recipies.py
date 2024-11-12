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

# def validate_image_url(url):
#     """Validate if the image URL is accessible"""
#     try:
#         response = requests.head(url, timeout=5)
#         content_type = response.headers.get('content-type', '')
#         return response.status_code == 200 and 'image' in content_type.lower()
#     except:
#         return False

# def get_google_image(query):
#     """Fetch an image URL from Google Custom Search API with improved error handling"""
#     fallback_image = f'https://via.placeholder.com/300x200.png?text={urllib.parse.quote(query)}'
    
#     if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
#         print("Missing Google API credentials")
#         return fallback_image
        
#     try:
#         # Add "food" to the query to get more relevant results
#         search_query = f"{query} food recipe"
#         url = "https://www.googleapis.com/customsearch/v1"
#         params = {
#             'key': GOOGLE_API_KEY,
#             'cx': GOOGLE_CSE_ID,
#             'q': search_query,
#             'searchType': 'image',
#             'num': 5,  # Request more images in case some fail validation
#             'imgSize': 'MEDIUM',
#             'safe': 'active'
#         }
        
#         response = requests.get(url, params=params, timeout=10)
#         response.raise_for_status()  # Raise exception for bad status codes
        
#         data = response.json()
#         if 'items' in data:
#             # Try each image URL until we find a valid one
#             for item in data['items']:
#                 image_url = item.get('link')
#                 if image_url and validate_image_url(image_url):
#                     return image_url
        
#         print(f"No valid images found for query: {query}")
#         return fallback_image
        
#     except requests.exceptions.RequestException as e:
#         print(f"Request error fetching image: {str(e)}")
#         return fallback_image
#     except Exception as e:
#         print(f"Unexpected error fetching image: {str(e)}")
#         return fallback_image

def get_related_recipes(recipe_title):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    related_recipes = []
    search_query = urllib.parse.quote(f"{recipe_title} recipe")
    
    sites = [
        ('https://www.allrecipes.com/search?q=', '.card__title-text', 'a.card__titleLink'),
        ('https://www.food.com/search/', '.title a', 'a.title'),
        ('https://www.simplyrecipes.com/search?q=', '.card__title', 'a.card__titleLink')
    ]
    
    for base_url, title_selector, link_selector in sites:
        try:
            response = requests.get(f"{base_url}{search_query}", headers=headers, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find recipe cards/links
                recipe_elements = soup.select(title_selector)[:2]
                
                for element in recipe_elements:
                    title = element.get_text().strip()
                    
                    # Find the link to the recipe
                    link = ''
                    if link_selector:
                        link_element = element.find_parent(link_selector) or element.find(link_selector)
                        if link_element and link_element.get('href'):
                            link = link_element['href']
                            if not link.startswith('http'):
                                link = urllib.parse.urljoin(base_url, link)
                    
                    # Only add if we found a valid title
                    if title and len(title) > 3:
                        # Get image from Google
                        img_url = get_google_image(title)
                        
                        related_recipes.append({
                            'title': title,
                            'image_url': img_url,
                            'source': base_url.split('.')[1].capitalize(),
                            'link': link
                        })
            
            time.sleep(random.uniform(0.5, 1.5))
            
        except Exception as e:
            print(f"Error fetching from {base_url}: {str(e)}")
            continue
    
    # If we couldn't find any recipes, add some generic ones
    if not related_recipes:
        fallback_image = f'https://via.placeholder.com/300x200.png?text=Similar+Recipe'
        related_recipes = [
            {
                'title': f"Similar {recipe_title}",
                'image_url': fallback_image,
                'source': 'Suggested Recipe',
                'link': '#'
            }
        ]
    
    return related_recipes[:5]


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