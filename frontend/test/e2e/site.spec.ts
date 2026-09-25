import { expect, test } from '@playwright/test';
import ADVICE from '../../lib/advice.json';

/**
 * The site as someone actually meets it (web.md 7.3, 7.4).
 *
 * The wording assertions are the rendered half of the guard that replaces
 * tests/test_site_wording.py: the ADVICE list, verbatim, against the full visible text of
 * each page with a typical line and an unusual one. The list is lib/advice.json, shared with
 * the source scan and the chat panel's guard.
 */

const EQUAL_CHANCE = 'equally likely to win';

const TYPICAL = '5, 12, 23, 31, 38, 44';
const UNUSUAL = '1, 2, 3, 4, 5, 6';

async function visibleText(page: import('@playwright/test').Page): Promise<string> {
  return (await page.locator('body').innerText()).toLowerCase();
}

/** The numbers currently in the line tray, read off their labels. */
async function trayNumbers(page: import('@playwright/test').Page): Promise<number[]> {
  return page
    .locator('.fixed [aria-label]')
    .evaluateAll((nodes) =>
      nodes
        .map((n) => n.getAttribute('aria-label') ?? '')
        .filter((label) => /^\d+(,|$)/.test(label))
        .map((label) => Number(label.split(',')[0])),
    );
}

/** web.md 7.3: every method must produce six distinct numbers in 1-47. */
async function assertAPlayableLine(page: import('@playwright/test').Page) {
  const numbers = await trayNumbers(page);
  expect(numbers).toHaveLength(6);
  expect(new Set(numbers).size).toBe(6);
  for (const n of numbers) {
    expect(n).toBeGreaterThanOrEqual(1);
    expect(n).toBeLessThanOrEqual(47);
  }
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

  for (const [label, width, height] of [
    ['phone', 390, 844],
    ['tablet', 820, 1180],
    ['desktop', 1440, 900],
  ] as const) {
    test(`home sits on its picture at ${label} width`, async ({ page }) => {
      await page.setViewportSize({ width, height });
      const picture = page.waitForResponse(
        (r) => r.url().includes('/home/background-') && r.ok(),
      );
      await page.goto('/');
      await picture;

      const scroll = await page.evaluate(() => [
        document.documentElement.scrollWidth,
        document.documentElement.clientWidth,
      ]);
      expect(scroll[0], 'no sideways scroll').toBeLessThanOrEqual(scroll[1]);

      const cta = page.getByRole('link', { name: 'Build my line' });
      await expect(cta).toBeVisible();
      await expect(cta).toHaveCSS('background-color', 'rgb(233, 196, 106)');
      const box = await cta.boundingBox();
      expect(box!.x + box!.width).toBeLessThanOrEqual(width);

      const banner = page.getByRole('main').getByRole('status');
      if (await banner.count()) {
        await expect(banner).toHaveCSS('background-image', /linear-gradient/);
      }
    });
  }

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
    await assertAPlayableLine(page);

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

    // One per band, all different: a wheel never hands back a number already in the line.
    const numbers = await trayNumbers(page);
    expect(numbers).toHaveLength(count);
    expect(new Set(numbers).size).toBe(count);
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
    await page.getByRole('button', { name: '32 to 47' }).click();
    await expect(remaining).not.toContainText('47');
  });

  test('an emptied band says so rather than spinning nothing', async ({ page }) => {
    await page.goto('/pick');
    // Keeping only numbers at 32 and above empties at least one band in any real data set,
    // or leaves them all populated - either way no wheel may claim to spin an empty band.
    await page.getByRole('button', { name: '32 to 47' }).click();
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
    await page.getByText('View full breakdown').first().click();
    await page.getByText('Show the numbers').first().click();
    await expect(page.locator('table').first()).toBeVisible();
  });

  test('statistics starts as a list of collapsed cards that open on demand', async ({ page }) => {
    await page.goto('/explore?tab=statistics');
    const cards = page.locator('details.stat-card');
    await expect(cards).toHaveCount(11);
    await expect(page.locator('details.stat-card[open]')).toHaveCount(0);
    await expect(page.getByText('How to read it', { exact: true }).first()).toBeHidden();

    const sums = page.locator('details#sums');
    const toggle = sums.locator('> summary');
    await toggle.click();
    await expect(sums).toHaveAttribute('open', '');
    await expect(sums.getByText('How to read it', { exact: true })).toBeVisible();
    await expect(sums.getByText('The sum of the six main numbers.')).toBeVisible();

    await toggle.click();
    await expect(sums).not.toHaveAttribute('open', '');
  });

  test('every statistics card, opened, says nothing that advises', async ({ page }) => {
    await page.goto('/explore?tab=statistics');
    for (const summary of await page.locator('details.stat-card > summary').all()) {
      await summary.click();
    }
    await expect(page.locator('details.stat-card[open]')).toHaveCount(11);
    const text = await visibleText(page);
    expect(text).toContain(EQUAL_CHANCE);
    assertNoAdvice(text);
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

  test('opens from a freshness bin', async ({ page }) => {
    await page.goto('/explore?tab=freshness');
    const first = page.locator('a[href^="/numbers/"]').first();
    const href = await first.getAttribute('href');
    await first.click();
    await expect(page).toHaveURL(new RegExp(`${href}$`));
    await expect(page.getByText(/last drawn/i)).toBeVisible();
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

test.describe('the pieces added after the first pass', () => {
  test('a dossier hands its number to the picker', async ({ page }) => {
    await page.goto('/numbers/23');
    await page.getByRole('link', { name: /add 23 to a line/i }).click();
    await expect(page).toHaveURL(/\/pick\?numbers=23/);
    await expect(page.getByText(/1 of 6 chosen/)).toBeVisible();
  });

  test('a freshness bin is sent to the picker as a filter', async ({ page }) => {
    await page.goto('/explore?tab=freshness');
    await page.getByRole('link', { name: 'Send these to the picker' }).first().click();
    await expect(page).toHaveURL(/\/pick\?bin=/);
    await expect(page.getByText(/freshness C/)).toBeVisible();
  });

  test('a band can be given another wheel, or none at all', async ({ page }) => {
    await page.goto('/pick');
    const before = await page.getByRole('button', { name: 'Spin', exact: true }).count();
    await page.getByRole('button', { name: 'One more hot wheel' }).click();
    await expect(page.getByRole('button', { name: 'Spin', exact: true })).toHaveCount(
      before + 1,
    );

    for (let i = 0; i < 2; i += 1) {
      await page.getByRole('button', { name: 'One fewer hot wheel' }).click();
    }
    await expect(page.getByText(/No hot wheel/)).toBeVisible();
  });

  test('a shape can be built from a sum band', async ({ page }) => {
    await page.goto('/pick');
    await page.getByRole('button', { name: 'Follow a shape' }).click();
    await page.getByRole('button', { name: /^140-154/ }).click();
    await page.getByRole('button', { name: 'Fill a line with this shape' }).click();
    await expect(page.getByText(/6 of 6 chosen/)).toBeVisible();
    await expect(page.getByText(/140-154/).first()).toBeVisible();
    await assertAPlayableLine(page);
  });

  test('a finished line can be saved as a PNG', async ({ page }) => {
    await page.goto('/pick');
    await page.getByRole('button', { name: 'Surprise me', exact: true }).first().click();
    await page.getByRole('button', { name: 'Surprise me', exact: true }).last().click();
    await expect(page.getByText(/6 of 6 chosen/)).toBeVisible();

    const download = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Save PNG' }).click();
    const file = await download;
    expect(file.suggestedFilename()).toMatch(/^lotto-line-[\d-]+\.png$/);
  });

  test('the counted charts follow a date range', async ({ page }) => {
    await page.goto('/explore?tab=statistics');
    const all = await page.getByText(/Over all \d+ draws/).first().innerText();

    await page.goto('/explore?tab=statistics&from=2026-01-01');
    const ranged = await page.getByText(/Over \d+ draws, /).first().innerText();
    expect(ranged).not.toBe(all);
    // The charts the engine wrote say plainly that a range does not apply to them.
    await expect(page.getByText(/a date range does not apply/).first()).toBeVisible();
  });
});

test.describe('the methods and the ways out', () => {
  test('shake the bag fills the tray with six', async ({ page }) => {
    await page.goto('/pick');
    await page.getByRole('button', { name: 'Shake the bag' }).click();
    await page.getByRole('button', { name: /^Shak/ }).last().click();

    // The numbers land one at a time, so the count settles rather than jumping.
    await expect(page.getByText(/6 of 6 chosen/)).toBeVisible();
    await expect(page.getByText(/next to \d+ past draws/i)).toBeVisible();

    await assertAPlayableLine(page);
  });

  test('the bag shows what is in it, and a card takes numbers out', async ({ page }) => {
    await page.goto('/pick');
    await page.getByRole('button', { name: 'Shake the bag' }).click();
    const bag = page.getByRole('list', { name: 'Numbers in the bag' });
    await expect(bag.getByRole('listitem')).toHaveCount(47);
    await expect(page.getByText('47 balls in the bag')).toBeVisible();

    // The cards are slides of a carousel; the one on screen is the one that can be used.
    await page.getByRole('button', { name: /^Show card \d: High or low/ }).click();
    await page.getByRole('button', { name: '32 to 47' }).click();
    await expect(bag.getByRole('listitem')).toHaveCount(16);
    await expect(page.getByText('16 balls in the bag')).toBeVisible();
    await expect(page.getByText('takes out 31')).toBeVisible();

    await page.getByRole('button', { name: /^Shak/ }).last().click();
    await expect(page.getByText(/6 of 6 chosen/)).toBeVisible();
    await expect(bag.getByRole('listitem', { name: /in your line/ })).toHaveCount(6);
  });

  test('the filter cards are a carousel that wraps, and moves by key', async ({ page }) => {
    await page.goto('/pick');
    const carousel = page.getByRole('region', { name: 'Filters' });
    // The indicator marks the card on screen at once; the card itself cross-fades in.
    const shows = async (title: string) => {
      await expect(carousel.locator('button[aria-current="true"]')).toHaveAccessibleName(
        new RegExp(title),
      );
      await expect(carousel.getByRole('heading', { name: title })).toBeVisible();
    };
    await shows('Busy lately');

    // Previous from the first card wraps to the last, next from the last wraps back.
    await carousel.getByRole('button', { name: 'Previous card' }).click();
    await shows('High or low');
    await carousel.getByRole('button', { name: 'Next card' }).click();
    await shows('Busy lately');

    await carousel.focus();
    await page.keyboard.press('ArrowRight');
    await shows('Quiet lately');
    await page.keyboard.press('ArrowLeft');
    await shows('Busy lately');

    await carousel.getByRole('button', { name: /^Show card \d: Freshness/ }).click();
    await shows('Freshness');
  });

  test('the filter carousel moves on its own until someone is using it', async ({ page }) => {
    // A fake clock, so five seconds are five seconds however busy the machine is.
    await page.clock.install();
    await page.goto('/pick');
    await page.waitForLoadState('networkidle');
    const carousel = page.getByRole('region', { name: 'Filters' });
    const current = carousel.locator('button[aria-current="true"]');
    await expect(current).toHaveAccessibleName(/Busy lately/);

    await page.clock.runFor(5100);
    await expect(current).toHaveAccessibleName(/Quiet lately/);

    // Hovering holds the card in place; leaving lets it move on.
    await carousel.getByRole('heading', { name: 'Quiet lately' }).hover();
    await page.clock.runFor(12000);
    await expect(current).toHaveAccessibleName(/Quiet lately/);
    await page.mouse.move(0, 0);
    await page.clock.runFor(5100);
    await expect(current).toHaveAccessibleName(/Freshness/);

    // Using a control on a card stops the carousel for good.
    await carousel
      .getByRole('group', { name: /Freshness$/ })
      .getByRole('button', { name: 'More info' })
      .click();
    await page.mouse.move(0, 0);
    await page.evaluate(() => (document.activeElement as HTMLElement).blur());
    await page.clock.runFor(12000);
    await expect(current).toHaveAccessibleName(/Freshness/);
  });

  test('a filter card explains itself and points at Explore by a relative link', async ({
    page,
  }) => {
    await page.goto('/pick');
    const carousel = page.getByRole('region', { name: 'Filters' });
    const more = carousel.getByRole('button', { name: 'More info' });
    await more.click();
    await expect(more).toHaveAttribute('aria-expanded', 'true');
    await expect(carousel.getByText(/every ball the same chance/)).toBeVisible();

    const explore = carousel.getByRole('link', { name: /on Explore/ });
    await expect(explore).toHaveAttribute('href', /^\/explore\?tab=/);
    await explore.click();
    await expect(page).toHaveURL(/\/explore\?tab=statistics/);
  });

  test('a freshness bin sent from Explore opens the carousel on its card', async ({ page }) => {
    await page.goto('/pick?bin=2');
    const carousel = page.getByRole('region', { name: 'Filters' });
    await expect(carousel.getByRole('heading', { level: 3 })).toHaveText('Freshness');
  });

  test('follow a shape explains the idea and links to Explore', async ({ page }) => {
    await page.goto('/pick');
    await page.getByRole('button', { name: 'Follow a shape' }).click();
    await expect(page.getByRole('heading', { name: 'Follow a shape' })).toBeVisible();
    await expect(page.getByText(/every line of six has the same chance/)).toBeVisible();
    await expect(page.getByText(/Your shape: nothing chosen yet/)).toBeVisible();

    await page.getByRole('button', { name: /^140-154/ }).click();
    await expect(page.getByText(/Your shape: sum 140-154/)).toBeVisible();

    const link = page.getByRole('link', { name: 'Odd/even, sums and spreads on Explore' });
    await expect(link).toHaveAttribute('href', '/explore?tab=statistics');
    await link.click();
    await expect(page).toHaveURL(/\/explore\?tab=statistics/);
  });

  test('a wheel can be used without spinning it', async ({ page }) => {
    // The plain way in: the same pool as a list, for anyone who would rather read it.
    await page.goto('/pick');
    const choose = page.getByLabel(/Choose a hot number/i).first();
    const value = await choose.locator('option').nth(1).getAttribute('value');
    await choose.selectOption(value!);
    await expect(page.getByText(/1 of 6 chosen/)).toBeVisible();
  });

  test('the line sheet opens when the line is complete and can be put away', async ({ page }) => {
    await page.goto('/pick');
    await page.getByRole('button', { name: 'Surprise me', exact: true }).first().click();
    await page.getByRole('button', { name: 'Surprise me', exact: true }).last().click();

    const handle = page.getByRole('button', { name: /the line details/i });
    await expect(handle).toHaveAttribute('aria-expanded', 'true');
    await expect(page.getByText(/next to \d+ past draws/i)).toBeVisible();

    await handle.click();
    await expect(handle).toHaveAttribute('aria-expanded', 'false');
    await expect(page.getByText(/next to \d+ past draws/i)).toBeHidden();
  });

  test('logging out ends the session', async ({ page, request }) => {
    await page.goto('/login');
    await page.getByLabel('Username').fill('e2e');
    await page.getByLabel('Password').fill('e2e-password');
    await page.getByRole('button', { name: 'Sign in' }).click();
    await expect(page.getByRole('link', { name: /download the data bundle/i })).toBeVisible();

    const before = (await page.context().cookies()).find((c) => c.name === 'lotto_admin');
    expect(before?.value).toBeTruthy();

    const loggedOut = await page.request.post('/api/logout');
    expect(loggedOut.ok()).toBeTruthy();

    const after = (await page.context().cookies()).find((c) => c.name === 'lotto_admin');
    expect(after?.value ?? '').toBe('');

    // And the session it cleared no longer opens the download.
    const refused = await request.get('/api/download/data', {
      headers: { Cookie: `lotto_admin=${after?.value ?? ''}` },
    });
    expect(refused.status()).toBe(401);
  });
});
