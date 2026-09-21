import { expect, test } from '@playwright/test';

/**
 * The site as someone actually meets it (web.md 7.3, 7.4).
 *
 * The wording assertions are the rendered half of the guard that replaces
 * tests/test_site_wording.py: the ADVICE list, verbatim, against the full visible text of
 * each page with a typical line and an unusual one.
 */
const ADVICE = [
  'play with confidence',
  'recommended',
  'regenerate',
  'risk',
  'improvement',
  'statistically sound',
  'excellent',
  'poor',
  'strong',
  'weak',
  'realistic',
  'confidence',
  'consider',
  'success rate',
  'astronomically',
  'diversif',
];

const EQUAL_CHANCE = 'equally likely to win';

const TYPICAL = '5, 12, 23, 31, 38, 44';
const UNUSUAL = '1, 2, 3, 4, 5, 6';

async function visibleText(page: import('@playwright/test').Page): Promise<string> {
  return (await page.locator('body').innerText()).toLowerCase();
}

function assertNoAdvice(text: string) {
  for (const phrase of ADVICE) {
    expect(text, `banned phrase: ${phrase}`).not.toContain(phrase);
  }
}

test.describe('the pages a player meets', () => {
  test('home shows the latest draw and the equal-chance sentence', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: /latest draw/i })).toBeVisible();
    // Six main numbers and a bonus.
    await expect(page.locator('[aria-label*="bonus ball"]')).toHaveCount(1);
    const text = await visibleText(page);
    expect(text).toContain(EQUAL_CHANCE);
    assertNoAdvice(text);
  });

  test('every destination is reachable from the navigation', async ({ page }) => {
    await page.goto('/');
    for (const name of ['Pick', 'Explore', 'Numbers', 'Review']) {
      await page.getByRole('navigation').getByRole('link', { name, exact: true }).click();
      await expect(page).toHaveURL(new RegExp(name.toLowerCase()));
      const text = await visibleText(page);
      expect(text).toContain(EQUAL_CHANCE);
      assertNoAdvice(text);
    }
  });
});

test.describe('picking a line', () => {
  test('surprise me gives six distinct numbers in 1-47 and scores them', async ({ page }) => {
    await page.goto('/pick');
    await page.getByRole('button', { name: 'Surprise me', exact: true }).first().click();
    await page.getByRole('button', { name: 'Surprise me', exact: true }).last().click();

    await expect(page.getByText(/6 of 6 chosen/)).toBeVisible();
    await expect(page.getByText(/next to \d+ past draws/i)).toBeVisible();

    const text = await visibleText(page);
    expect(text).toMatch(/this line looks (typical|uncommon|unusual) /);
    expect(text).toContain(EQUAL_CHANCE);
    assertNoAdvice(text);
  });

  test('the wheels add one number per band', async ({ page }) => {
    await page.goto('/pick');
    // Exact: the method chip is called "Spin the wheels", which also contains "Spin".
    const spins = page.getByRole('button', { name: 'Spin', exact: true });
    const count = await spins.count();
    for (let i = 0; i < count; i += 1) await spins.nth(i).click();
    await expect(page.getByText(new RegExp(`${count} of 6 chosen`))).toBeVisible();
  });

  test('picking by hand toggles a number in and out', async ({ page }) => {
    await page.goto('/pick');
    await page.getByRole('button', { name: 'Pick by hand' }).click();
    // The tray shows a button for a chosen number too, so scope to the grid.
    const seven = page.locator('ul').getByRole('button', { name: /^7, / });
    await seven.click();
    await expect(page.getByText(/1 of 6 chosen/)).toBeVisible();
    await seven.click();
    await expect(page.getByText(/0 of 6 chosen/)).toBeVisible();
  });

  test('a filter shrinks the pool and says so', async ({ page }) => {
    await page.goto('/pick');
    const remaining = page.getByText(/numbers left in the wheels/);
    await expect(remaining).toContainText('47');
    await page.getByLabel(/^Half$/).selectOption('high');
    await expect(remaining).not.toContainText('47');
  });

  test('an emptied band says so rather than spinning nothing', async ({ page }) => {
    await page.goto('/pick');
    // Keeping only numbers at 32 and above empties at least one band in any real data set,
    // or leaves them all populated - either way no wheel may claim to spin an empty band.
    await page.getByLabel(/^Half$/).selectOption('high');
    const empty = page.getByRole('button', { name: 'Empty' });
    for (let i = 0; i < (await empty.count()); i += 1) {
      await expect(empty.nth(i)).toBeDisabled();
    }
  });
});

test.describe('explore', () => {
  test('the draw list pages', async ({ page }) => {
    await page.goto('/explore?tab=draws');
    const newest = page.locator('li a[href*="draw="]').first();
    const first = await newest.innerText();
    await page.getByRole('link', { name: 'Older' }).click();
    await expect(newest).not.toHaveText(first);
  });

  test('a draw opens as a card with its pre-draw bonus window', async ({ page }) => {
    await page.goto('/explore?tab=draws');
    await page.locator('li a[href*="draw="]').first().click();
    await expect(page.getByText(/bonus balls before this draw/i)).toBeVisible();
  });

  test('statistics shows the numbers behind a chart', async ({ page }) => {
    await page.goto('/explore?tab=statistics');
    await page.getByText('Show the numbers').first().click();
    await expect(page.locator('table').first()).toBeVisible();
    assertNoAdvice(await visibleText(page));
  });

  test('freshness highlights a bin', async ({ page }) => {
    await page.goto('/explore?tab=freshness');
    await page.getByRole('link', { name: 'Highlight this bin' }).first().click();
    await expect(page.getByRole('link', { name: 'Clear highlight' })).toBeVisible();
  });

  test('patterns finds an exact match for a past draw (F-25)', async ({ page }) => {
    // The newest draw, read off the home page, must find itself.
    await page.goto('/');
    const balls = page.locator('main [aria-label]');
    const labels = await balls.evaluateAll((nodes) =>
      nodes
        .map((n) => n.getAttribute('aria-label') ?? '')
        .filter((l) => !l.includes('bonus'))
        .map((l) => l.split(',')[0]),
    );
    const line = labels.slice(0, 6).join(', ');

    await page.goto(`/explore?tab=patterns&line=${encodeURIComponent(line)}`);
    await expect(page.getByText(/an exact match/)).toBeVisible();
    assertNoAdvice(await visibleText(page));
  });

  test('a line of the wrong length is refused, not scored as zero', async ({ page }) => {
    await page.goto('/explore?tab=patterns&line=1,2,3');
    await expect(page.locator('main').getByRole('alert')).toContainText('exactly 6 numbers');
  });
});

test.describe('a number dossier', () => {
  test('opens from the numbers page and reads as a fact sheet', async ({ page }) => {
    await page.goto('/numbers');
    await page.locator('a[href^="/numbers/"]').first().click();
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await expect(page.getByText(/last drawn/i)).toBeVisible();
    assertNoAdvice(await visibleText(page));
  });

  test('opens from the pick page peek card', async ({ page }) => {
    await page.goto('/pick');
    await page.getByRole('button', { name: 'Pick by hand' }).click();
    await page.locator('ul').getByRole('button', { name: /^7, / }).click();
    await page.getByRole('link', { name: 'Full dossier' }).click();
    await expect(page).toHaveURL(/\/numbers\/7$/);
  });

  test('a number outside 1-47 is not a page', async ({ page }) => {
    const response = await page.goto('/numbers/48');
    expect(response?.status()).toBe(404);
  });
});

test.describe('the admin half', () => {
  test('the download is refused when logged out', async ({ request }) => {
    const response = await request.get('/api/download/data');
    expect(response.status()).toBe(401);
  });

  test('logging in gives a zip holding the artifacts', async ({ page, request }) => {
    await page.goto('/login');
    await page.getByLabel('Username').fill('e2e');
    await page.getByLabel('Password').fill('e2e-password');
    await page.getByRole('button', { name: 'Sign in' }).click();
    await expect(page.getByRole('link', { name: /download the data bundle/i })).toBeVisible();

    const cookies = await page.context().cookies();
    const session = cookies.find((c) => c.name === 'lotto_admin');
    expect(session?.httpOnly).toBe(true);

    const download = await request.get('/api/download/data', {
      headers: { Cookie: `lotto_admin=${session!.value}` },
    });
    expect(download.status()).toBe(200);
    expect(download.headers()['content-type']).toBe('application/zip');
    expect(Number(download.headers()['content-length'] ?? '1')).toBeGreaterThan(0);
  });

  test('a wrong password is refused', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('Username').fill('e2e');
    await page.getByLabel('Password').fill('not-the-password');
    await page.getByRole('button', { name: 'Sign in' }).click();
    await expect(page.locator('main').getByRole('alert')).toContainText('Invalid credentials');
  });

  test('review hides the generated lines from the public', async ({ page }) => {
    await page.goto('/review');
    await expect(page.getByText(/generated lines \(admin\)/i)).toHaveCount(0);
    assertNoAdvice(await visibleText(page));
  });
});

test.describe('the wording guard, on real lines', () => {
  for (const [name, line] of [
    ['typical', TYPICAL],
    ['unusual', UNUSUAL],
  ] as const) {
    test(`a ${name} line is described, never advised`, async ({ page }) => {
      await page.goto(`/explore?tab=patterns&line=${encodeURIComponent(line)}`);
      const text = await visibleText(page);
      expect(text).toMatch(/this line looks (typical|uncommon|unusual) /);
      expect(text).toContain(EQUAL_CHANCE);
      assertNoAdvice(text);
    });
  }
});
