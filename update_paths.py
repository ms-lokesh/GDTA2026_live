import os
import re

def update_html_paths(directory):
    """
    Updates paths in HTML files to reflect the new project structure.
    """
    html_files = [f for f in os.listdir(directory) if f.endswith('.html')]

    for filename in html_files:
        filepath = os.path.join(directory, filename)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Rule 1-6: Update asset paths
        content = re.sub(r'href="css/', 'href="/static/css/', content)
        content = re.sub(r'href="lib/', 'href="/static/lib/', content)
        content = re.sub(r'src="js/', 'src="/static/js/', content)
        content = re.sub(r'src="lib/', 'src="/static/lib/', content)
        content = re.sub(r'src="img/', 'src="/static/img/', content)
        content = re.sub(r"url\('img/", "url('/static/img/", content)

        # Rule 7: Update navigation links to be absolute
        content = re.sub(r'href="([a-zA-Z0-9_-]+\.html)"', r'href="/\1"', content)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"Updated paths in: {filename}")

if __name__ == "__main__":
    templates_dir = os.path.join('admin_system', 'templates')
    if os.path.isdir(templates_dir):
        update_html_paths(templates_dir)
        print("\nAll HTML files have been updated successfully!")
    else:
        print(f"Error: The directory '{templates_dir}' does not exist.")

