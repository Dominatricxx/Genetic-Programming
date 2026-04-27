import re

def remove_docstrings(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex to remove """ """ and ''' ''' docstrings
    content = re.sub(r'\"\"\"[\s\S]*?\"\"\"', '', content)
    content = re.sub(r"\'\'\'[\s\S]*?\'\'\'", '', content)

    # Clean up excessive empty lines
    content = re.sub(r'\n\s*\n', '\n\n', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

remove_docstrings("main.py")
remove_docstrings("Práctica GP.py")
print("Removed docstrings from Python files!")
