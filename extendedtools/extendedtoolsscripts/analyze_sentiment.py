def analyze_sentiment(text):
    # A very basic sentiment analysis function (for demonstration purposes)
    positive_words = ['good', 'great', 'happy']
    negative_words = ['bad', 'terrible', 'sad']
    
    words = text.split()
    positive_count = sum(1 for word in words if word in positive_words)
    negative_count = sum(1 for word in words if word in negative_words)
    
    if positive_count > negative_count:
        return 'Positive'
    elif negative_count > positive_count:
        return 'Negative'
    else:
        return 'Neutral'