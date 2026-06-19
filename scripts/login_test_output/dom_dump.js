const fs = require('fs');
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const report = { startedAt: new Date().toISOString(), url: 'https://xeroxytb.com/login', observations: [] };
  const puppeteer = await import('puppeteer-core');
  const browser = await puppeteer.launch({
    executablePath: process.env.EDGE_PATH,
    headless: 'new',
    args: ['--no-sandbox','--disable-setuid-sandbox']
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 900 });
  await page.goto(report.url, { waitUntil: 'networkidle2', timeout: 60000 });
  const snap = async (label) => {
    const bootDots = await page.$('.login-boot-dots');
    const googleBtn = await page.$('[data-testid="google-login-btn"]');
    const loginCard = await page.$('[data-testid="login-card"]');
    const retryBtn = await page.evaluate(() => [...document.querySelectorAll('button')].some(b => b.textContent.includes('Réessayer')));
    const msg = await page.evaluate(() => {
      const p = document.querySelector('.login-page p.text-secondary-em');
      return p ? p.textContent.trim() : '';
    });
    const toasts = await page.evaluate(() => [...document.querySelectorAll('[data-sonner-toast]')].map(el => el.textContent.trim()).filter(Boolean));
    await page.screenshot({ path: `${process.env.OUT_DIR}/${label}.png`, fullPage: true });
    return { label, at: new Date().toISOString(), bootDots: !!bootDots, googleBtn: !!googleBtn, loginCard: !!loginCard, retryBtn, msg, toasts, url: page.url(), title: await page.title() };
  };
  report.snapshots = [];
  report.snapshots.push(await snap('t0_immediate'));
  await sleep(5000);
  report.snapshots.push(await snap('t5s'));
  const deadline = Date.now() + 90000;
  while (Date.now() < deadline) {
    const ready = await page.$('[data-testid="google-login-btn"], [data-testid="login-card"], button');
    const state = await page.evaluate(() => {
      if (document.querySelector('[data-testid="google-login-btn"]')) return 'google';
      if (document.querySelector('[data-testid="login-card"]')) return 'login';
      if ([...document.querySelectorAll('button')].some(b => b.textContent.includes('Réessayer'))) return 'offline';
      return 'boot';
    });
    if (state !== 'boot') { report.finalState = state; break; }
    await sleep(1000);
  }
  if (!report.finalState) report.finalState = 'timeout';
  report.snapshots.push(await snap('t_final'));
  const google = await page.$('[data-testid="google-login-btn"]');
  if (google) {
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 30000 }).catch(() => null),
      google.click()
    ]);
    report.snapshots.push(await snap('t_after_google_click'));
  }
  report.finishedAt = new Date().toISOString();
  fs.writeFileSync(`${process.env.OUT_DIR}/report.json`, JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  await browser.close();
})();
