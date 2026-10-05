'use client';

// A line ending in a date in the viewer's time zone (C-21, PD-R2R-06). The server does not know
// the viewer's zone, so it renders UTC and the browser re-formats after hydration; `timeZone`
// fixes the zone for tests. The line is one text node, so it reads (and matches) as one sentence.
import { useEffect, useState } from 'react';

export function formatLocalDate(iso: string, timeZone?: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone }).format(d);
}

export function LocalDateLine({
  prefix,
  iso,
  timeZone,
  className,
}: {
  prefix: string;
  iso: string;
  timeZone?: string;
  className?: string;
}) {
  const [date, setDate] = useState(() => formatLocalDate(iso, timeZone ?? 'UTC'));
  useEffect(() => {
    setDate(formatLocalDate(iso, timeZone));
  }, [iso, timeZone]);
  return (
    <p className={className} suppressHydrationWarning>
      {`${prefix}${date}`}
    </p>
  );
}
