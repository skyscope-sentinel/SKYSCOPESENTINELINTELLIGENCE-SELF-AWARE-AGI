#Requires -RunAsAdministrator

# Comprehensive PowerShell script to integrate Ollama into Windows with elevated permissions,
# filesystem access, internet access, OS management, and advanced AI capabilities.

# Check for administrative privileges
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "This script requires administrative privileges. Relaunching as administrator..."
    Start-Process powershell -Verb RunAs -ArgumentList "-File `"$PSCommandPath`""
    exit
}

# Define base directory for Skyscope Sentinel
$baseDir = "C:\SkyscopeSentinel"
if (-not (Test-Path $baseDir)) {
    New-Item -Path $baseDir -ItemType Directory -Force
}

# Check if Ollama is installed
try {
    $ollamaVersion = ollama --version
    Write-Host "Ollama is installed: $ollamaVersion"
} catch {
    Write-Host "Ollama is not installed. Please install it from https://ollama.com/download/windows."
    exit
}

# Install required PowerShell modules
$requiredModules = @("Selenium", "PSWindowsUpdate")
foreach ($module in $requiredModules) {
    if (-not (Get-Module -ListAvailable -Name $module)) {
        Install-Module -Name $module -Scope CurrentUser -Force -AllowClobber
    }
}

# Download and integrate GitHub repositories
$repos = @{
    "PowerShell" = "https://github.com/skyscope-sentinel/PowerShell/archive/refs/heads/main.zip"
    "KnowledgeStack" = "https://github.com/skyscope-sentinel/SKYSCOPESENTINELINTELLIGENCE-SELF-AWARE-AGI/archive/refs/heads/main.zip"
}
foreach ($repo in $repos.GetEnumerator()) {
    $repoDir = "$baseDir\$($repo.Key)"
    if (-not (Test-Path $repoDir)) {
        $zipPath = "$baseDir\$($repo.Key).zip"
        Invoke-WebRequest -Uri $repo.Value -OutFile $zipPath
        Expand-Archive -Path $zipPath -DestinationPath $baseDir -Force
        Remove-Item $zipPath
        # Rename extracted folder to match key
        $extractedFolder = Get-ChildItem -Path $baseDir -Directory | Where-Object { $_.Name -like "$($repo.Key)-main" }
        if ($extractedFolder) {
            Move-Item -Path $extractedFolder.FullName -Destination $repoDir -Force
        }
    }
}

# Include PowerShell scripts from repository
$psScriptsDir = "$baseDir\PowerShell"
Get-ChildItem -Path $psScriptsDir -Filter "*.ps1" -Recurse | ForEach-Object {
    . $_.FullName
}

# Define tools for Ollama models
$tools = @(
    @{
        type = "function"
        function = @{
            name = "web_search"
            description = "Search the web using DuckDuckGo"
            parameters = @{ type = "object"; properties = @{ query = @{ type = "string" } }; required = @("query") }
        }
    },
    @{
        type = "function"
        function = @{
            name = "execute_command"
            description = "Execute a PowerShell command"
            parameters = @{ type = "object"; properties = @{ command = @{ type = "string" } }; required = @("command") }
        }
    },
    @{
        type = "function"
        function = @{
            name = "read_file"
            description = "Read a file's content"
            parameters = @{ type = "object"; properties = @{ path = @{ type = "string" } }; required = @("path") }
        }
    },
    @{
        type = "function"
        function = @{
            name = "write_file"
            description = "Write content to a file"
            parameters = @{ type = "object"; properties = @{ path = @{ type = "string" }; content = @{ type = "string" } }; required = @("path", "content") }
        }
    },
    @{
        type = "function"
        function = @{
            name = "open_url"
            description = "Open a URL in Chrome"
            parameters = @{ type = "object"; properties = @{ url = @{ type = "string" } }; required = @("url") }
        }
    },
    @{
        type = "function"
        function = @{
            name = "get_page_content"
            description = "Get current browser page HTML"
            parameters = @{}
        }
    },
    @{
        type = "function"
        function = @{
            name = "edit_document"
            description = "Edit text in a document or image (e.g., replace 'resume' with 'CV')"
            parameters = @{ type = "object"; properties = @{ path = @{ type = "string" }; oldText = @{ type = "string" }; newText = @{ type = "string" } }; required = @("path", "oldText", "newText") }
        }
    }
)

# Comprehensive system prompt
$systemPrompt = @"
You are Skyscope Sentinel Intelligence, an advanced AI assistant integrated into Windows. You have:
- **Filesystem Access**: Read/write files using read_file and write_file.
- **Internet Access**: Search via DuckDuckGo with web_search.
- **OS Management**: Execute PowerShell commands with execute_command, including scripts from $psScriptsDir for managing apps, volume, registry, group policies, firewall, and processes.
- **Browser Automation**: Open URLs (open_url) and retrieve content (get_page_content) using Chrome.
- **Knowledge Stack**: Access PDFs and text files from $baseDir\KnowledgeStack.
- **Advanced Capabilities**: Edit documents/images with edit_document, and leverage vision models for social media, video generation, and more.

Use these tools to manage the OS, install apps/extensions, modify policies, and perform autonomous tasks. Call functions as needed and provide detailed responses.
"@

# Start Selenium Chrome driver
$driver = Start-SeChrome

# Tool implementation functions
function Invoke-WebSearch { param ($query) $driver.Navigate().GoToUrl("https://duckduckgo.com/?q=$query"); Start-Sleep -Seconds 2; ($driver.FindElementsByClassName("result__body") | ForEach-Object { $_.Text }) -join "`n" }
function Invoke-ExecuteCommand { param ($command) try { Invoke-Expression $command } catch { $_.Exception.Message } }
function Invoke-ReadFile { param ($path) try { Get-Content -Path $path -Raw } catch { $_.Exception.Message } }
function Invoke-WriteFile { param ($path, $content) try { Set-Content -Path $path -Value $content; "Success" } catch { $_.Exception.Message } }
function Invoke-OpenUrl { param ($url) $driver.Navigate().GoToUrl($url); "URL opened" }
function Invoke-GetPageContent { $driver.PageSource }
function Invoke-EditDocument { param ($path, $oldText, $newText) try { $content = Get-Content -Path $path -Raw; $content -replace $oldText, $newText | Set-Content -Path $path; "Edited" } catch { $_.Exception.Message } }

# Clone and modify Open-WebUI
$openWebUiDir = "$baseDir\OpenWebUI"
if (-not (Test-Path $openWebUiDir)) {
    git clone https://github.com/open-webui/open-webui.git $openWebUiDir
}

# Install development tools if missing
$devTools = @("choco install git", "choco install nodejs", "choco install python", "choco install visualstudio2022buildtools")
foreach ($tool in $devTools) {
    if (-not (Get-Command ($tool.Split(" ")[2]) -ErrorAction SilentlyContinue)) {
        Invoke-ExecuteCommand -command $tool
    }
}

# Rename Open-WebUI to Skyscope Sentinel Intelligence - Local AI Workspace
$uiDir = "$openWebUiDir\frontend"
Get-ChildItem -Path $openWebUiDir -Recurse -File | ForEach-Object {
    (Get-Content $_.FullName -Raw) -replace "Open WebUI", "Skyscope Sentinel Intelligence - Local AI Workspace" | Set-Content $_.FullName
}

# Add themes and advanced options
$indexHtml = "$uiDir\index.html"
if (Test-Path $indexHtml) {
    $themeScript = @"
    <script>
        const themes = [
            { name: 'Light', css: 'body { background: #fff; color: #000; }' },
            { name: 'Dark', css: 'body { background: #333; color: #fff; }' },
            { name: 'Blue', css: 'body { background: #e6f0ff; color: #003087; }' },
            { name: 'Green', css: 'body { background: #e6ffe6; color: #006600; }' }
        ];
        function applyTheme(themeIndex) {
            document.head.insertAdjacentHTML('beforeend', `<style>${themes[themeIndex].css}</style>`);
        }
        document.addEventListener('DOMContentLoaded', () => {
            const themeSelect = document.createElement('select');
            themes.forEach((t, i) => {
                const opt = document.createElement('option');
                opt.value = i; opt.text = t.name;
                themeSelect.appendChild(opt);
            });
            themeSelect.onchange = (e) => applyTheme(e.target.value);
            document.body.appendChild(themeSelect);
        });
    </script>
"@
    (Get-Content $indexHtml -Raw) + $themeScript | Set-Content $indexHtml
}

# Build MSI/EXE installer
$buildDir = "$openWebUiDir\build"
if (-not (Test-Path $buildDir)) {
    Set-Location $openWebUiDir
    npm install
    npm run build
    python -m PyInstaller --onefile --name "SkyscopeSentinelIntelligence" main.py
    Move-Item "$openWebUiDir\dist\SkyscopeSentinelIntelligence.exe" "$baseDir\SkyscopeSentinelIntelligence.exe"
}

# Interactive loop with vision and advanced features
$messages = @(@{ role = "system"; content = $systemPrompt })
while ($true) {
    $userInput = Read-Host "You"
    if ($userInput -eq "exit") { break }
    $messages += @{ role = "user"; content = $userInput }

    $response = Invoke-RestMethod -Method Post -Uri "http://localhost:11434/api/chat" -Body (@{
        model = "llama3.2" # Replace with vision-capable model if available
        messages = $messages
        tools = $tools
    } | ConvertTo-Json -Depth 10)

    if ($response.tool_calls) {
        foreach ($toolCall in $response.tool_calls) {
            $args = $toolCall.function.arguments | ConvertFrom-Json
            $result = switch ($toolCall.function.name) {
                "web_search" { Invoke-WebSearch -query $args.query }
                "execute_command" { Invoke-ExecuteCommand -command $args.command }
                "read_file" { Invoke-ReadFile -path $args.path }
                "write_file" { Invoke-WriteFile -path $args.path -content $args.content }
                "open_url" { Invoke-OpenUrl -url $args.url }
                "get_page_content" { Invoke-GetPageContent }
                "edit_document" { Invoke-EditDocument -path $args.path -oldText $args.oldText -newText $args.newText }
            }
            $messages += @{ role = "tool"; content = $result; tool_call_id = $toolCall.id }
        }
        $finalResponse = Invoke-RestMethod -Method Post -Uri "http://localhost:11434/api/chat" -Body (@{
            model = "llama3.2"
            messages = $messages
        } | ConvertTo-Json -Depth 10)
        Write-Host "Assistant: $($finalResponse.content)"
        $messages += @{ role = "assistant"; content = $finalResponse.content }
    } else {
        Write-Host "Assistant: $($response.content)"
        $messages += @{ role = "assistant"; content = $response.content }
    }
}

# Cleanup
$driver.Quit()
