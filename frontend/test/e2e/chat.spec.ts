import { expect, test } from '@playwright/test';
import ADVICE from '../../lib/advice.json';

/**
 * The chat panel as someone meets it (chat.md 9). The e2e server runs with no OpenRouter
 * key, so every answer here comes from the free layers and nothing leaves the box.
 */

const EQUAL_CHANCE = 'equally likely to win';

function assertNoAdvice(text: string) {
  for (const phrase of ADVICE) {
    expect(text, `banned phrase: ${phrase}`).not.toContain(phrase);
  }
}

test('opens, answers a suggested question, and nothing leaves the box', async ({ page, baseURL }) => {
  const outside: string[] = [];
  page.on('request', (r) => {
    if (!r.url().startsWith(baseURL!)) outside.push(r.url());
  });
  await page.goto('/numbers');
  await page.getByRole('button', { name: 'Ask about this page' }).click();

  const panel = page.getByRole('dialog', { name: 'Ask about this page' });
  await expect(panel).toBeVisible();
  await panel.getByRole('button', { name: 'What is volatility?' }).click();
  await expect(panel.getByText(/how uneven a number's gaps/)).toBeVisible();
  await expect(panel.getByText('Prepared answer')).toBeVisible();
  expect(outside).toEqual([]);
});

test('answers a typed question from the data, about the page s own number', async ({ page }) => {
  await page.goto('/numbers/12');
  await page.getByRole('button', { name: 'Ask about this page' }).click();
  const panel = page.getByRole('dialog');
  await panel.getByLabel('Your question').fill('How many times has it come up?');
  await panel.getByRole('button', { name: 'Ask', exact: true }).click();
  await expect(panel.getByText(/^12 has been drawn \d+ times/)).toBeVisible();
  await expect(panel.getByText('From the data')).toBeVisible();
});

test('says plainly when a question needs the model and there is none', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Ask about this page' }).click();
  const panel = page.getByRole('dialog');
  await panel.getByLabel('Your question').fill('What stands out on this page?');
  await panel.getByLabel('Your question').press('Enter');
  await expect(panel.getByText(/free-form answers are not switched on/)).toBeVisible();
});

test('offers the questions for the way of picking on screen', async ({ page }) => {
  await page.goto('/pick');
  await page.getByRole('button', { name: 'Shake the bag' }).click();
  await page.getByRole('button', { name: 'Ask about this page' }).click();
  const panel = page.getByRole('dialog');
  await expect(panel.getByRole('button', { name: 'What does shaking the bag do?' })).toBeVisible();
  await expect(panel.getByRole('button', { name: 'How do the wheels work?' })).toHaveCount(0);

  await panel.getByRole('button', { name: 'Why take out numbers that were a bonus ball?' }).click();
  await expect(panel.getByText(/a fair draw gives \d+\.\d%/)).toBeVisible();
  await expect(panel.getByText('From the data')).toBeVisible();

  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Spin the wheels' }).click();
  await page.getByRole('button', { name: 'Ask about this page' }).click();
  await expect(panel.getByRole('button', { name: 'How do the wheels work?' })).toBeVisible();
});

test('fits the screen, and closes with Escape', async ({ page }) => {
  await page.goto('/pick');
  await page.getByRole('button', { name: 'Ask about this page' }).click();
  const panel = page.getByRole('dialog');
  await expect(panel).toBeVisible();
  // Measure where it comes to rest, not a frame of the slide-in.
  await panel.evaluate((el) => Promise.all(el.getAnimations().map((a) => a.finished)));
  const box = (await panel.boundingBox())!;
  const width = page.viewportSize()!.width;
  expect(box.x).toBeGreaterThanOrEqual(0);
  expect(box.x + box.width).toBeLessThanOrEqual(width + 1);
  await expect(panel.getByLabel('Your question')).toBeInViewport();

  await page.keyboard.press('Escape');
  await expect(panel).toBeHidden();
});

test('its opening state passes the wording guard on every destination', async ({ page }) => {
  for (const path of ['/', '/pick', '/explore', '/numbers', '/review']) {
    await page.goto(path);
    await page.getByRole('button', { name: 'Ask about this page' }).click();
    const panel = page.getByRole('dialog');
    await expect(panel.getByRole('listitem').first()).toBeVisible();
    const text = (await panel.innerText()).toLowerCase();
    expect(text).toContain(EQUAL_CHANCE);
    assertNoAdvice(text);
  }
});
