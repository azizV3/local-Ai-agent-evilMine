import requests
from bs4 import BeautifulSoup

def scrape_website(url):
    try:
        # Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the HTML content of the page with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Example: Extract all paragraph tags
        paragraphs = soup.find_all('p')
        for i, p in enumerate(paragraphs):
            print(f"Paragraph {i+1}: {p.get_text()}")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the website: {e}")

if __name__ == "__main__":
    url = input("Enter the URL of the website you want to scrape: ")
    scrape_website(url)