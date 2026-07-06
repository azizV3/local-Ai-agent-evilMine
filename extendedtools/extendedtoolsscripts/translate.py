def translate(text, target_language):
    # A very basic translation function (for demonstration purposes)
    translations = {
        'en': {'hello': 'world'},
        'fr': {'hello': 'bonjour'}
    }
    words = text.split()
    translated_words = [translations[target_language].get(word, word) for word in words]
    return ' '.join(translated_words)