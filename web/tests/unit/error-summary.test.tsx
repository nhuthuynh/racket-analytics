// Error summary [DPA/DESIGN-13] (PD-R2-01): focus moves to the summary when its messages change,
// never on an unrelated re-render, so a player can type to correct the field (SC 3.2.2, NFR-034).
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ErrorSummary } from '@/components/ErrorSummary';

function Page({ message, tick }: { message: string; tick: number }) {
  return (
    <>
      <ErrorSummary errors={[{ field: 'email', message }]} />
      <input id="email" aria-label="Email address" data-tick={tick} />
    </>
  );
}

describe('ErrorSummary focus', () => {
  it('keeps focus in the field when a re-render passes an equal, new errors array', () => {
    const { rerender } = render(<Page message="Enter an email address" tick={0} />);
    expect(screen.getByRole('alert')).toHaveFocus();
    screen.getByLabelText('Email address').focus();
    rerender(<Page message="Enter an email address" tick={1} />);
    expect(screen.getByLabelText('Email address')).toHaveFocus();
  });

  it('moves focus to the summary again when the messages change', () => {
    const { rerender } = render(<Page message="Enter an email address" tick={0} />);
    screen.getByLabelText('Email address').focus();
    rerender(<Page message="Enter an email address in the correct format" tick={1} />);
    expect(screen.getByRole('alert')).toHaveFocus();
  });

  it('renders a link with an href as a plain link to another page', () => {
    render(<ErrorSummary errors={[{ field: 'x', message: 'Go to Your matches', href: '/matches' }]} />);
    expect(screen.getByRole('link', { name: 'Go to Your matches' })).toHaveAttribute('href', '/matches');
  });
});
