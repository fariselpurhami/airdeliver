// apps/web/__tests__/HomePage.test.tsx

import { render, screen } from '@testing-library/react'
import HomePage from '../app/(main)/page'

describe('HomePage', () => {
  it('renders the main headline', () => {
    render(<HomePage />)

    const headline = screen.getByRole('heading', {
      name: /The Future of Delivery is Here./i,
    })

    expect(headline).toBeInTheDocument()
  })
})
