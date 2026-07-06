def search_web(query):
    import requests
    url = f'https://www.google.com/search?q={query}'
    response = requests.get(url)
    return response.status_code == 200