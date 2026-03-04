param(
    [string]$CommitMessage = "Initial commit to GitHub"
)

Write-Host "Ensuring Git remote 'origin' points to GitHub repo..."

# Check if 'origin' remote exists
$remoteExists = git remote | Where-Object { $_ -eq "origin" }

if ($remoteExists) {
    git remote set-url origin https://github.com/SingleColumn/privateclub_zkp.git
} else {
    git remote add origin https://github.com/SingleColumn/privateclub_zkp.git
}

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to configure git remote 'origin'. Aborting."
    exit 1
}

Write-Host "Staging allowed files (as controlled by .gitignore)..."
git add .

if ($LASTEXITCODE -ne 0) {
    Write-Error "git add failed. Aborting."
    exit 1
}

Write-Host "Creating commit..."
git commit -m $CommitMessage

if ($LASTEXITCODE -ne 0) {
    Write-Error "git commit failed (possibly nothing to commit). Aborting."
    exit 1
}

Write-Host "Pushing to 'origin' on 'main' (or 'master' if main fails)..."
git push -u origin main

if ($LASTEXITCODE -ne 0) {
    Write-Warning "Push to 'main' failed. Trying 'master'..."
    git push -u origin master
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Push failed to both 'main' and 'master'. Please check your branch name and authentication."
        exit 1
    }
}

Write-Host "Done. Project committed and pushed to GitHub."
