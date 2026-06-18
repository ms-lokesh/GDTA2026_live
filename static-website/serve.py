import http.server
import os
import sys

class ExtensionlessHTMLHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Translate standard path
        translated = super().translate_path(path)
        
        # If the file doesn't exist and has no extension, check if file.html exists
        if not os.path.exists(translated):
            base, ext = os.path.splitext(translated)
            if not ext:
                html_path = translated + '.html'
                if os.path.exists(html_path):
                    return html_path
        return translated

if __name__ == '__main__':
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
            
    print(f"Starting server on port {port} with extensionless HTML routing support...")
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, ExtensionlessHTMLHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        sys.exit(0)
