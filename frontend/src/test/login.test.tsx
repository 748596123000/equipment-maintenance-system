import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import LoginPage from '../pages/login'

// Mock the API
vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

// Mock auth store
vi.mock('../stores/auth-store', () => ({
  useAuthStore: vi.fn(() => ({
    login: vi.fn(),
    user: null,
    logout: vi.fn(),
  })),
}))

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders login form', async () => {
    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    )
    
    expect(screen.getByText('设备检修知识系统')).toBeTruthy()
  })

  it('has username and password inputs', async () => {
    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    )
    
    expect(screen.getByPlaceholderText(/用户名/)).toBeTruthy()
    expect(screen.getByPlaceholderText(/密码/)).toBeTruthy()
  })
})