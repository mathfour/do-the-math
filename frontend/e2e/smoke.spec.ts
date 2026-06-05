import { expect, test } from '@playwright/test'

// Phase 0 smoke test — proves the Playwright harness drives a real browser
// against the dev server. Replaced by real slice E2E in Phase 3.
test('app loads in the browser', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: /get started/i })).toBeVisible()
})
