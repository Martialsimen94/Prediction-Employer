import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RiskBadge } from './RiskBadge'

describe('RiskBadge', () => {
  it.each(['low', 'medium', 'high', 'critical'] as const)('renders the %s level', (level) => {
    render(<RiskBadge level={level} />)
    expect(screen.getByText(level)).toBeInTheDocument()
  })
})
