import { expect, test } from '@playwright/test'

// Phase 2 smoke: the first-run key screen renders in a real browser. The full
// slice E2E (mocked backend, clarification loop, error paths) lands in Phase 3.
test('first-run key screen loads in the browser', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Do the Math' })).toBeVisible()
  await expect(page.getByLabel(/anthropic api key/i)).toBeVisible()
  await expect(page.getByText(/more ai providers are coming/i)).toBeVisible()
})
