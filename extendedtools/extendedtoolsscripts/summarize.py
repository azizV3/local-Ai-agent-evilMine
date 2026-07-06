def summarize(text):
    # A very basic summarization function (for demonstration purposes)
    words = text.split()
    summary = ' '.join(words[:5]) + '...'  # Summarize by taking the first 5 words
    return summary