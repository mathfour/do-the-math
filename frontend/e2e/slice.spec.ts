import { expect, test, type Page } from '@playwright/test'

// E2E for the full slice against a MOCKED backend — no live model billing.
// We intercept POST /chat and return canned envelopes (and answer the CORS
// preflight, since the app calls a different origin in dev).

type Envelope = {
  type: string
  explanation: string
  payload: Record<string, unknown>
}

const CORS = {
  'access-control-allow-origin': '*',
  'access-control-allow-headers': '*',
  'access-control-allow-methods': '*',
}

/** Make POST /chat return `responses` in order (last one repeats). */
async function mockChat(page: Page, responses: Envelope[]) {
  let call = 0
  await page.route('**/chat', async (route) => {
    if (route.request().method() === 'OPTIONS') {
      return route.fulfill({ status: 204, headers: CORS })
    }
    const body = responses[Math.min(call, responses.length - 1)]
    call += 1
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      headers: CORS,
      body: JSON.stringify(body),
    })
  })
}

const GRAPH: Envelope = {
  type: 'graph',
  explanation: 'Nice — one parabola, coming right up: y = (x − 1)² + 2.',
  payload: {
    figure: {
      data: [{ type: 'scatter', mode: 'lines', x: [-2, 0, 2, 4], y: [11, 3, 3, 11] }],
      layout: { title: { text: 'y = (x − 1)² + 2' } },
    },
    equation: 'y = (x - 1)**2 + 2',
    ir: { kind: 'parabola_vertex_direction', vertex: [1, 2], direction: 'up' },
  },
}

async function enterKeyAndOpenChat(page: Page) {
  await page.goto('/')
  await page.getByLabel(/anthropic api key/i).fill('sk-ant-e2e')
  await page.getByRole('button', { name: /start graphing/i }).click()
  await expect(page.getByLabel(/describe a graph/i)).toBeVisible()
}

async function send(page: Page, text: string) {
  await page.getByLabel(/describe a graph/i).fill(text)
  await page.getByRole('button', { name: /send/i }).click()
}

test('happy path: key screen -> request -> graph + reasoning panel', async ({ page }) => {
  await mockChat(page, [GRAPH])
  await enterKeyAndOpenChat(page)

  await send(page, 'a parabola with vertex (1, 2) opening upward')

  // The conversational line and the interactive graph both render.
  await expect(page.getByText(/coming right up/i)).toBeVisible()
  await expect(page.getByRole('img', { name: /graph/i })).toBeVisible()

  // The reasoning panel is collapsed by default; expanding reveals IR + equation.
  await page.getByText(/how this was derived/i).click()
  await expect(page.getByText(/parabola_vertex_direction/)).toBeVisible()
  await expect(page.getByText('y = (x - 1)**2 + 2')).toBeVisible()
})

test('clarification loop: question -> answer -> graph', async ({ page }) => {
  await mockChat(page, [
    {
      type: 'clarification',
      explanation: 'Where is the vertex of the parabola?',
      payload: { question: 'Where is the vertex of the parabola?', field: 'vertex' },
    },
    GRAPH,
  ])
  await enterKeyAndOpenChat(page)

  await send(page, 'graph a parabola')
  await expect(page.getByText(/where is the vertex of the parabola/i)).toBeVisible()

  await send(page, 'the vertex is (1, 2)')
  await expect(page.getByRole('img', { name: /graph/i })).toBeVisible()
})

test('out-of-scope request shows a gentle note + what it can graph', async ({ page }) => {
  await mockChat(page, [
    {
      type: 'error',
      explanation: 'not supported',
      payload: {
        message: "Implicit equations (like x**2 + y**2 = 25) aren't supported in v1.",
        reason: 'implicit',
      },
    },
  ])
  await enterKeyAndOpenChat(page)

  await send(page, 'graph x^2 + y^2 = 25')
  await expect(page.getByText(/i can only graph functions/i)).toBeVisible()
  await expect(page.getByText(/aren't supported in v1/i)).toBeVisible()
  await expect(page.getByText(/single-variable function/i)).toBeVisible()
})
