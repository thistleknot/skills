---
name: headless-browser-verification
description: >
  Visual verification protocol using headless browsers to capture screenshots (PNG)
  before handing off updated web pages to users. Use when code changes affect rendered
  output, CSS/layout, interactive elements, or responsive design, and you need proof
  that the visual result matches intent before delivery.
status: active
last_validated: 2026-05-03
---

# Headless Browser Verification

## When to Use

Use this pattern when:

- You modify HTML/CSS and need to verify layout changes before shipping
- Testing responsive design across breakpoints (mobile, tablet, desktop)
- Ensuring interactive elements (buttons, forms, modals) render correctly
- Documenting visual regressions or improvements as PNG artifacts
- Handing off code changes to a user/designer with visual proof
- Building a visual regression test suite (screenshot comparisons)

**Not** for:
- Unit testing logic (use traditional unit tests instead)
- JavaScript functionality testing (use automation frameworks like Playwright/Puppeteer with assertions)
- Performance profiling (use DevTools profiler)
- Accessibility audit (use axe-core or similar WCAG validators)

---

## Architecture

```
┌────────────────────────────────┐
│ Code changes (HTML/CSS/JS)     │
└────────────────┬───────────────┘
                 │
                 ▼
    ┌────────────────────────────┐
    │ Spin up headless browser   │
    │ (Puppeteer/Selenium)       │
    └────────────┬───────────────┘
                 │
                 ▼
    ┌────────────────────────────┐
    │ Navigate to endpoint       │
    │ (http://localhost:3000)    │
    └────────────┬───────────────┘
                 │
                 ▼
    ┌────────────────────────────┐
    │ Wait for render (DOM ready)│
    │ (waitForNavigation, etc)   │
    └────────────┬───────────────┘
                 │
                 ▼
    ┌────────────────────────────┐
    │ Optional: interactions     │
    │ (click, scroll, hover)     │
    └────────────┬───────────────┘
                 │
                 ▼
    ┌────────────────────────────┐
    │ Capture screenshot (PNG)   │
    │ Full page or viewport      │
    └────────────┬───────────────┘
                 │
                 ▼
    ┌────────────────────────────┐
    │ Save to artifacts dir      │
    │ /artifacts/screenshots/    │
    └────────────┬───────────────┘
                 │
                 ▼
    ┌────────────────────────────┐
    │ Hand off to user with URL  │
    │ "See /artifacts/screenshot │
    │  _homepage_desktop.png"    │
    └────────────────────────────┘
```

---

## Implementation Pattern

### Step 1: Basic Headless Browser Setup

**Using Puppeteer (Node.js):**

```javascript
const puppeteer = require('puppeteer');

async function captureScreenshot(url, options = {}) {
  const {
    fullPage = true,
    viewport = { width: 1280, height: 720 },
    waitFor = 'networkidle2', // 'networkidle0', 'networkidle2', 'domcontentloaded'
    outputPath = './screenshots'
  } = options;

  let browser;
  try {
    browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    await page.setViewport(viewport);
    
    // Navigate and wait for render
    await page.goto(url, { waitUntil: waitFor });
    
    // Optional: wait additional time for animations
    await page.waitForTimeout(1000);
    
    // Take screenshot
    const screenshotPath = `${outputPath}/screenshot_${Date.now()}.png`;
    await page.screenshot({
      path: screenshotPath,
      fullPage: fullPage
    });
    
    console.log(`✓ Screenshot saved: ${screenshotPath}`);
    return screenshotPath;
    
  } finally {
    if (browser) await browser.close();
  }
}

// Usage
captureScreenshot('http://localhost:3000/homepage');
```

**Using Selenium (Python):**

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os

def capture_screenshot(url, output_path='./screenshots', viewport_size=(1280, 720)):
    """
    Require: url is a valid HTTP endpoint; output_path exists or will be created
    Guarantee: returns path to saved PNG screenshot
    """
    os.makedirs(output_path, exist_ok=True)
    
    # Configure headless Chrome
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument(f'--window-size={viewport_size[0]},{viewport_size[1]}')
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(('tag_name', 'body'))
        )
        
        # Wait additional time for dynamic content
        driver.execute_script("window.scrollTo(0, 0);")  # Scroll to top
        driver.implicitly_wait(2)
        
        # Save screenshot
        timestamp = int(time.time() * 1000)
        screenshot_path = os.path.join(output_path, f'screenshot_{timestamp}.png')
        driver.save_screenshot(screenshot_path)
        
        print(f'✓ Screenshot saved: {screenshot_path}')
        return screenshot_path
        
    finally:
        if driver:
            driver.quit()

# Usage
capture_screenshot('http://localhost:3000')
```

### Step 2: Multi-Viewport Testing

Test across multiple device sizes (responsive design verification).

```javascript
async function captureMultiViewport(url, outputDir = './screenshots') {
  const viewports = {
    mobile: { width: 375, height: 667 },      // iPhone 8
    tablet: { width: 768, height: 1024 },     // iPad
    desktop: { width: 1280, height: 720 }     // Desktop
  };
  
  let browser;
  try {
    browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();
    
    const results = {};
    for (const [deviceType, viewport] of Object.entries(viewports)) {
      await page.setViewport(viewport);
      await page.goto(url, { waitUntil: 'networkidle2' });
      
      const fileName = `${outputDir}/screenshot_${deviceType}.png`;
      await page.screenshot({ path: fileName, fullPage: true });
      results[deviceType] = fileName;
      
      console.log(`✓ ${deviceType}: ${fileName}`);
    }
    
    return results;
    
  } finally {
    if (browser) await browser.close();
  }
}

// Usage
captureMultiViewport('http://localhost:3000');
```

### Step 3: Interaction & Dynamic Content

Capture screenshots after user interactions (clicks, scrolls, form fills).

```javascript
async function captureAfterInteraction(url, interactions = [], outputPath = './screenshots') {
  """
  Require: interactions is a list of functions that take (page) and return Promise
  Guarantee: saves screenshot after each interaction
  """
  let browser;
  try {
    browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();
    
    await page.goto(url, { waitUntil: 'networkidle2' });
    
    // Initial screenshot
    let step = 0;
    let fileName = `${outputPath}/screenshot_step_${step}.png`;
    await page.screenshot({ path: fileName });
    console.log(`✓ Initial state: ${fileName}`);
    
    // Execute interactions and capture
    for (const interaction of interactions) {
      await interaction(page);
      await page.waitForTimeout(500);  // Wait for animations
      
      step++;
      fileName = `${outputPath}/screenshot_step_${step}.png`;
      await page.screenshot({ path: fileName });
      console.log(`✓ After interaction ${step}: ${fileName}`);
    }
    
  } finally {
    if (browser) await browser.close();
  }
}

// Usage
const interactions = [
  async (page) => {
    await page.click('button[data-action="menu"]');
  },
  async (page) => {
    await page.type('input[name="search"]', 'test query');
  },
  async (page) => {
    await page.click('button[type="submit"]');
  }
];

captureAfterInteraction('http://localhost:3000', interactions);
```

### Step 4: Visual Regression Detection

Compare screenshots to detect unexpected changes.

```python
from PIL import Image
import imagehash
import os

def visual_regression_check(baseline_dir, current_dir, threshold=5):
    """
    Require: baseline_dir and current_dir contain PNG screenshots with matching names
    Guarantee: returns list of files with visual changes above threshold
    Maintain: threshold=5 (1-10 scale; 0=identical, 10+=significant)
    """
    differences = []
    
    for filename in os.listdir(baseline_dir):
        if not filename.endswith('.png'):
            continue
        
        baseline_path = os.path.join(baseline_dir, filename)
        current_path = os.path.join(current_dir, filename)
        
        if not os.path.exists(current_path):
            differences.append({
                'file': filename,
                'status': 'missing',
                'message': 'Screenshot not found in current'
            })
            continue
        
        # Compare using perceptual hash
        baseline_img = Image.open(baseline_path)
        current_img = Image.open(current_path)
        
        baseline_hash = imagehash.phash(baseline_img)
        current_hash = imagehash.phash(current_img)
        
        distance = baseline_hash - current_hash
        
        if distance > threshold:
            differences.append({
                'file': filename,
                'status': 'changed',
                'distance': distance,
                'message': f'Visual change detected (distance={distance})'
            })
        else:
            print(f'✓ {filename}: unchanged (distance={distance})')
    
    return differences

# Usage
diffs = visual_regression_check('./screenshots/baseline', './screenshots/current')
if diffs:
    print(f'\n⚠ {len(diffs)} differences found:')
    for diff in diffs:
        print(f'  - {diff["file"]}: {diff["message"]}')
```

### Step 5: Integration with CI/CD

Automated screenshot verification in your build pipeline.

**GitHub Actions example:**
```yaml
name: Visual Regression

on: [push, pull_request]

jobs:
  screenshot-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Start dev server
        run: npm run dev &
        
      - name: Wait for server
        run: sleep 5
        
      - name: Capture screenshots
        run: npm run test:screenshots
        
      - name: Compare with baseline
        run: npm run test:visual-regression
        
      - name: Upload artifacts
        if: always()
        uses: actions/upload-artifact@v2
        with:
          name: screenshots
          path: ./screenshots
```

---

## Configuration & Options

### Puppeteer Options

| Option | Default | Purpose |
|---|---|---|
| `headless` | `true` | Run without UI |
| `viewport.width` | 1280 | Viewport width (px) |
| `viewport.height` | 720 | Viewport height (px) |
| `waitUntil` | 'networkidle2' | When to consider nav complete |
| `fullPage` | `true` | Capture full scrollable page or viewport only |
| `timeout` | 30000 | Navigation timeout (ms) |

### Wait Conditions

- **`domcontentloaded`**: Fire when DOM is loaded (fast, may miss async content)
- **`load`**: Wait for page load event (standard)
- **`networkidle0`**: Wait until no network requests (slow, safest)
- **`networkidle2`**: Wait until ≤2 network requests (balanced)

### Viewport Presets

```python
VIEWPORTS = {
    'iphone_8': (375, 667),
    'iphone_12': (390, 844),
    'pixel_5': (393, 851),
    'ipad': (768, 1024),
    'ipad_pro': (1024, 1366),
    'desktop_small': (1280, 720),
    'desktop_large': (1920, 1080),
    'desktop_4k': (3840, 2160),
}
```

---

## Edge Cases & Mitigations

| Problem | Cause | Mitigation |
|---|---|---|
| Screenshot captures incomplete content | Dynamic content loading after render | Increase `waitFor` timeout or add explicit `waitForSelector` |
| Flaky tests (different screenshots each run) | Animations, timers, or randomized content | Disable animations; use `waitForTimeout` or static test data |
| Server not responding | Port/service not running | Add health-check before capture; retry logic |
| Chrome crash on Linux | Missing libraries | Use `--no-sandbox` flag; install `libx11-dev` etc. |
| Out-of-memory on large pages | Full-page capture too large | Use viewport-only mode; chunk large pages |
| SSL/cert errors | Self-signed certificate | Pass `--ignore-certificate-errors` flag |

---

## Worked Example: Verifying Homepage Redesign

**Goal**: Ensure new homepage layout renders correctly across devices before handoff.

**Step 1: Capture baseline (before changes)**
```bash
npm run screenshot -- http://localhost:3000 --viewports mobile,tablet,desktop --output ./screenshots/baseline
```

**Step 2: Make CSS/layout changes**
(Edit homepage.css, test locally)

**Step 3: Capture current state**
```bash
npm run screenshot -- http://localhost:3000 --viewports mobile,tablet,desktop --output ./screenshots/current
```

**Step 4: Visual regression check**
```bash
npm run test:visual-regression -- ./screenshots/baseline ./screenshots/current
```

**Output:**
```
✓ screenshot_desktop.png: unchanged
⚠ screenshot_mobile.png: changed (distance=8)
✓ screenshot_tablet.png: unchanged

Result: Homepage layout looks good on mobile (expected change), unchanged on tablet/desktop.
Ready to hand off.
```

---

## Integration with Existing Skills

- **`validation`**: Add visual screenshot verification to the test suite
- **`code`**: Document CSS/HTML changes with before/after screenshots
- **`documentation`**: Include rendered screenshots in README/changelog
- **`security-review`**: Verify security-sensitive UI (auth forms) render correctly

---

## Performance Notes

- **Startup**: ~2–5 seconds (browser launch)
- **Per screenshot**: ~1–3 seconds (navigation + render)
- **Batch (5 viewports)**: ~20–30 seconds total
- **Full-page capture**: ~2–5 seconds (larger files, 1–5MB PNG)

**Optimization**: Reuse browser instance for multiple screenshots; cache browser startup.

---

## Evidence

- Puppeteer: widely used for headless automation (Google-maintained)
- Selenium: industry-standard browser automation
- Visual regression: standard practice in design QA (see Percy, Chromatic)
- Screenshot-based verification: common in acceptance testing (Gherkin/BDD)
<!-- consolidation:see-also:start -->
## See Also
[[validation-artifacts]]  [[cua-desktop-agent]]  [[git-workflow]]  [[openspec-workflow]]  [[react-fastapi-sqlite]]
<!-- consolidation:see-also:end -->
