import { afterEach, describe, expect, it } from 'vitest'
import { clearApiKey, getApiKey, setApiKey } from './storage'

afterEach(() => localStorage.removeItem('do-the-math:anthropic-key'))

describe('storage', () => {
  it('round-trips the key through localStorage', () => {
    expect(getApiKey()).toBeNull()
    setApiKey('sk-ant-abc')
    expect(getApiKey()).toBe('sk-ant-abc')
  })

  it('clears the key', () => {
    setApiKey('sk-ant-abc')
    clearApiKey()
    expect(getApiKey()).toBeNull()
  })
})
