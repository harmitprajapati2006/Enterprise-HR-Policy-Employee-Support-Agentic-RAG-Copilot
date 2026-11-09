@echo off
cd /d "%~dp0"
echo ========================================================
echo Pushing Enterprise HR Agentic RAG to GitHub
echo Repository: harmitprajapati2006/Enterprise-HR-Policy-Employee-Support-Agentic-RAG-Copilot
echo ========================================================
echo.
git status
echo.
git add .
git commit -m "feat: complete enterprise HR agentic RAG copilot with FastAPI, UI, and policy KB"
git push -u origin main
echo.
pause
