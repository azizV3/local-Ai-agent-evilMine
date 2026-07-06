def write_text_file(file_name, content):
    with open(file_name, 'w') as file:
        file.write(content)
    return "success"