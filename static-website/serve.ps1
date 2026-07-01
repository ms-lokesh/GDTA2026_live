# Helper to get canonical full path
function Get-FullPath($path) {
    return [System.IO.Path]::GetFullPath($path)
}

# Change working directory to the script's directory so it serves static-website files correctly
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($scriptDir) { Set-Location $scriptDir }

$port = 8000
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://localhost:$port/")

try {
    $listener.Start()
    Write-Host "Server running at http://localhost:$port/"
    Write-Host "Press Ctrl+C to stop the server."
    
    while ($listener.IsListening) {
        $context = $listener.GetContext()
        $request = $context.Request
        $response = $context.Response
        
        $url = $request.Url.LocalPath
        if ($url -eq "/" -or $url -eq "\") {
            $url = "/index.html"
        }
        
        # Decode URL-encoded characters (like spaces)
        $url = [System.Uri]::UnescapeDataString($url)
        
        # Clean up path separators
        $cleanUrl = $url.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
        if ($cleanUrl.StartsWith([System.IO.Path]::DirectorySeparatorChar)) {
            $cleanUrl = $cleanUrl.Substring(1)
        }
        
        $filePath = Get-FullPath (Join-Path (Get-Location) $cleanUrl)
        
        # Prevent directory traversal
        $currentDir = (Get-Location).Path
        if (-not $filePath.StartsWith($currentDir)) {
            $response.StatusCode = 403
            $errBytes = [System.Text.Encoding]::UTF8.GetBytes("403 Forbidden")
            $response.OutputStream.Write($errBytes, 0, $errBytes.Length)
            $response.Close()
            continue
        }
        
        # Handle extensionless HTML routing
        if (-not (Test-Path $filePath -PathType Leaf)) {
            $htmlPath = $filePath + ".html"
            if (Test-Path $htmlPath -PathType Leaf) {
                $filePath = $htmlPath
            }
        }
        
        if (Test-Path $filePath -PathType Leaf) {
            $bytes = [System.IO.File]::ReadAllBytes($filePath)
            
            # Content type matching
            $ext = [System.IO.Path]::GetExtension($filePath).ToLower()
            $contentType = switch ($ext) {
                ".html" { "text/html; charset=utf-8" }
                ".css"  { "text/css; charset=utf-8" }
                ".js"   { "application/javascript; charset=utf-8" }
                ".png"  { "image/png" }
                ".jpg"  { "image/jpeg" }
                ".jpeg" { "image/jpeg" }
                ".gif"  { "image/gif" }
                ".svg"  { "image/svg+xml" }
                ".ico"  { "image/x-icon" }
                default { "application/octet-stream" }
            }
            
            $response.ContentType = $contentType
            $response.ContentLength64 = $bytes.Length
            $response.OutputStream.Write($bytes, 0, $bytes.Length)
        } else {
            $response.StatusCode = 404
            $errBytes = [System.Text.Encoding]::UTF8.GetBytes("404 Not Found")
            $response.OutputStream.Write($errBytes, 0, $errBytes.Length)
        }
        $response.Close()
    }
} catch {
    Write-Error $_
} finally {
    if ($listener) {
        $listener.Stop()
        $listener.Close()
    }
}
