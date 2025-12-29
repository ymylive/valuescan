# Chrome MCP Test for Black Screen Issue

## Prerequisites

1. **Start the API server**:
   ```bash
   python -m api.server
   ```
   The API server should be running on http://localhost:5000

2. **Start the web development server**:
   ```bash
   cd web
   npm run dev
   ```
   The web server should be running on http://localhost:3000

3. **Install Playwright** (if not already installed):
   ```bash
   pip install playwright
   playwright install chromium
   ```

## Running the Test

Once both servers are running, execute the test script:

```bash
python scripts/test_config_page_chrome.py
```

## What the Test Does

1. ✅ Launches Chrome browser (visible, not headless)
2. ✅ Navigates to http://localhost:3000
3. ✅ Takes screenshot of dashboard
4. ✅ Clicks on "系统配置" (System Configuration) tab
5. ✅ Takes screenshot after clicking
6. ✅ Waits for loading to complete
7. ✅ Checks if config sections are visible
8. ✅ Inspects DOM structure
9. ✅ Checks computed styles for visibility issues
10. ✅ Monitors console messages and errors
11. ✅ Checks network requests to /api/config
12. ✅ Keeps browser open for 30 seconds for manual inspection

## Expected Output

The script will:
- Print detailed logs to console
- Save screenshots to `output/screenshots/`
- Report any errors or visibility issues
- Keep the browser open for manual inspection

## Troubleshooting

If the test fails:

1. **Check if servers are running**:
   ```bash
   # Check API server
   curl http://localhost:5000/api/config

   # Check web server
   curl http://localhost:3000
   ```

2. **Check browser console** (the test keeps browser open for 30 seconds)

3. **Review screenshots** in `output/screenshots/`

4. **Check the test output** for DOM structure and style information

## Alternative: Manual Testing

If the automated test doesn't work, you can manually test:

1. Open Chrome DevTools (F12)
2. Navigate to http://localhost:3000
3. Click on "系统配置" tab
4. Check Console tab for errors
5. Check Elements tab to inspect DOM
6. Check Network tab for failed requests
7. Take screenshots of the issue
