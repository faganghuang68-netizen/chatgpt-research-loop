param(
  [Parameter(Mandatory=$true)][string]$ReceiptJsonPath,
  [switch]$DryRun,
  [switch]$AllowUniqueConversationFallback
)

$ErrorActionPreference = "Stop"

function Finish-Safely([string]$status, [string]$reason) {
  Write-Host "CHATGPT_RESEARCH_LOOP_WAKE=$status"
  if (-not [string]::IsNullOrWhiteSpace($reason)) {
    Write-Host "REASON=$reason"
  }
  exit 0
}

function Invoke-BrowserControlQuiet([string[]]$Arguments) {
  $previousPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = "Continue"
    # Browser Control may include the adopted target URL in stdout/stderr.
    # Never mirror native output into public Actions logs because the exact
    # ChatGPT conversation URL is treated as sensitive configuration.
    $null = & browser-control @Arguments 2>&1
    return $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $previousPreference
  }
}

if (-not (Test-Path $ReceiptJsonPath)) {
  Finish-Safely "SKIP" "RECEIPT_JSON_MISSING"
}

try {
  $receipt = Get-Content $ReceiptJsonPath -Raw | ConvertFrom-Json
} catch {
  Finish-Safely "SKIP" "RECEIPT_JSON_INVALID"
}

if (-not $receipt.eligible) {
  Finish-Safely "SKIP" "RECEIPT_NOT_ELIGIBLE"
}

$chatUrl = [Environment]::GetEnvironmentVariable("CHATGPT_RESEARCH_BRAIN_URL")
if ([string]::IsNullOrWhiteSpace($chatUrl)) {
  Finish-Safely "SKIP" "CHATGPT_RESEARCH_BRAIN_URL_NOT_SET"
}

try {
  $uri = [System.Uri]$chatUrl
} catch {
  Finish-Safely "SKIP" "INVALID_CHATGPT_RESEARCH_BRAIN_URL"
}

if ($uri.Scheme -ne "https" -or $uri.Host -ne "chatgpt.com" -or -not $uri.AbsolutePath.StartsWith("/c/")) {
  Finish-Safely "SKIP" "CHATGPT_RESEARCH_BRAIN_URL_MUST_BE_HTTPS_CONVERSATION"
}

$sourceCommentId = [string]$receipt.source_comment_id
$fingerprint = [string]$receipt.semantic_fingerprint
$decision = [string]$receipt.decision
$repository = [string]$receipt.repository
$sourceResource = [string]$receipt.source_resource
$sourceUrl = [string]$receipt.source_url
$nextAction = if ($receipt.next_action) { [string]$receipt.next_action } else { "UNSPECIFIED" }

if ([string]::IsNullOrWhiteSpace($sourceCommentId) -or
    [string]::IsNullOrWhiteSpace($fingerprint) -or
    [string]::IsNullOrWhiteSpace($decision) -or
    [string]::IsNullOrWhiteSpace($repository)) {
  Finish-Safely "SKIP" "RECEIPT_REQUIRED_FIELDS_MISSING"
}

$wakeKey = "$sourceCommentId|$fingerprint"
$wakePayloadLines = @(
  "CHATGPT_RESEARCH_LOOP_WAKE",
  "SOURCE_REPOSITORY=$repository",
  "SOURCE_RESOURCE=$sourceResource",
  "SOURCE_COMMENT_ID=$sourceCommentId",
  "SOURCE_URL=$sourceUrl",
  "SEMANTIC_FINGERPRINT=$fingerprint",
  "COMPLETION_CLASS=$([string]$receipt.completion_class)",
  "COMPLETION_DECISION=$decision",
  "NEXT_ACTION=$nextAction",
  "",
  "Read the authoritative GitHub source receipt and current repository/controller state before taking further action.",
  "Do not infer scientific or engineering validity from CI status alone.",
  "Respect repository safety gates, authorization boundaries, and human-only decisions.",
  "Treat this message as a wake-up pointer, not as the authoritative evidence itself."
)
$wakeMessage = [string]::Join([Environment]::NewLine, $wakePayloadLines)

if ($DryRun) {
  Write-Host "CHATGPT_RESEARCH_LOOP_WAKE=DRY_RUN_PASS"
  Write-Host "WAKE_KEY=$wakeKey"
  Write-Host "TARGET_HOST=$($uri.Host)"
  Write-Host "TARGET_PATH_PREFIX=/c/"
  Write-Host "PROMPT_CHARS=$($wakeMessage.Length)"
  exit 0
}

if (-not (Get-Command browser-control -ErrorAction SilentlyContinue)) {
  Finish-Safely "SKIP" "BROWSER_CONTROL_NOT_INSTALLED"
}

$stateDir = Join-Path $env:USERPROFILE ".chatgpt-research-loop"
New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
$statePath = Join-Path $stateDir "wake_state.json"
$recentKeys = @()

if (Test-Path $statePath) {
  try {
    $state = Get-Content $statePath -Raw | ConvertFrom-Json
    if ($state.recent_wake_keys) {
      $recentKeys = @($state.recent_wake_keys | ForEach-Object { [string]$_ })
    }
    if ($recentKeys -contains $wakeKey) {
      Write-Host "CHATGPT_RESEARCH_LOOP_WAKE=NO_OP"
      Write-Host "WAKE_KEY=$wakeKey"
      exit 0
    }
  } catch {
    Finish-Safely "SKIP" "WAKE_STATE_UNREADABLE"
  }
}

$session = "chatgpt-research-loop"
$newExit = Invoke-BrowserControlQuiet @("session", "new", $session)
if ($newExit -ne 0) {
  Write-Host "BROWSER_CONTROL_SESSION_NEW=NONZERO_CONTINUE"
}

$adoptMode = "EXACT"
$selectedTarget = $uri.AbsoluteUri
$adoptExit = Invoke-BrowserControlQuiet @("session", "adopt", "--session", $session, "--target-url", $selectedTarget)

if ($adoptExit -ne 0 -and $AllowUniqueConversationFallback) {
  Write-Host "BROWSER_CONTROL_EXACT_ADOPT=NONZERO_TRY_UNIQUE_CHATGPT_CONVERSATION"
  $adoptMode = "UNIQUE_CHATGPT_CONVERSATION"
  $selectedTarget = "https://chatgpt.com/c/"
  $adoptExit = Invoke-BrowserControlQuiet @("session", "adopt", "--session", $session, "--target-url", $selectedTarget)
}

if ($adoptExit -ne 0) {
  Finish-Safely "SKIP" "CHATGPT_TAB_NOT_ATTACHED_OR_ADOPT_FAILED"
}

$targetJson = $selectedTarget | ConvertTo-Json -Compress
$messageJson = $wakeMessage | ConvertTo-Json -Compress
$modeJson = $adoptMode | ConvertTo-Json -Compress
$tempRoot = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { [System.IO.Path]::GetTempPath() }
$tempScript = Join-Path $tempRoot ("chatgpt-research-loop-browser-control-" + [Guid]::NewGuid().ToString("N") + ".js")

$script = @"
const targetUrl = $targetJson;
const wakeMessage = $messageJson;
const adoptMode = $modeJson;
const currentUrl = page.url();
if (adoptMode === 'EXACT') {
  if (currentUrl !== targetUrl) {
    throw new Error('adopted ChatGPT tab does not exactly match configured conversation');
  }
} else {
  if (!currentUrl.startsWith('https://chatgpt.com/c/')) {
    throw new Error('fallback adopted page is not a ChatGPT conversation');
  }
}
const composer = page.locator('#prompt-textarea[contenteditable="true"]').first();
await composer.waitFor({ state: 'visible', timeout: 15000 });
await composer.fill(wakeMessage);
const send = page.locator('button[data-testid="send-button"], button[aria-label="Send prompt"]').first();
await send.waitFor({ state: 'visible', timeout: 10000 });
if (await send.isDisabled()) throw new Error('send button disabled');
await send.click();
await page.waitForFunction(() => {
  const el = document.querySelector('#prompt-textarea[contenteditable="true"]');
  return !el || !(el.innerText || '').trim();
}, null, { timeout: 10000 });
return { submitted: true, adoptMode };
"@

try {
  Set-Content -Path $tempScript -Value $script -Encoding UTF8
  $executeExit = Invoke-BrowserControlQuiet @("execute", "--session", $session, "--file", $tempScript, "--json")
} finally {
  Remove-Item $tempScript -Force -ErrorAction SilentlyContinue
}

if ($executeExit -ne 0) {
  Finish-Safely "SKIP" "BROWSER_CONTROL_SUBMIT_FAILED"
}

# Keep a bounded history rather than only the immediately previous key. This
# prevents A -> B -> A event ordering from re-delivering A.
$newKeys = @($wakeKey) + @($recentKeys | Where-Object { $_ -ne $wakeKey })
if ($newKeys.Count -gt 256) {
  $newKeys = @($newKeys[0..255])
}

$newState = @{
  schema = 1
  recent_wake_keys = $newKeys
  last_source_comment_id = $sourceCommentId
  last_semantic_fingerprint = $fingerprint
  last_adopt_mode = $adoptMode
  completed_at_utc = [DateTime]::UtcNow.ToString("o")
}
$stateTemp = Join-Path $stateDir ("wake_state-" + [Guid]::NewGuid().ToString("N") + ".json")
try {
  $newState | ConvertTo-Json -Depth 4 | Set-Content -Path $stateTemp -Encoding UTF8
  Move-Item -Path $stateTemp -Destination $statePath -Force
} finally {
  Remove-Item $stateTemp -Force -ErrorAction SilentlyContinue
}

Write-Host "CHATGPT_RESEARCH_LOOP_WAKE=PASS"
Write-Host "WAKE_KEY=$wakeKey"
Write-Host "ADOPT_MODE=$adoptMode"
