/**
 * Example Component Test
 * Demonstrates basic component testing pattern
 * This test doesn't require any actual components to exist yet
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

// Simple test component for demonstration
function TestButton({ label }: { label: string }) {
  return <button>{label}</button>;
}

describe('Example Component Test', () => {
  it('should render a button with text', () => {
    render(<TestButton label="Click Me" />);
    expect(screen.getByText('Click Me')).toBeInTheDocument();
  });

  it('should render a button with different text', () => {
    render(<TestButton label="Submit" />);
    expect(screen.getByRole('button', { name: 'Submit' })).toBeInTheDocument();
  });
});
