'use client';

// "New match": title and format only (sprint-00 §3.1 ST-010). Validated in the browser
// because the Sprint 0 API returns no per-field errors (api-sprint-00 §3).
import { useRouter } from 'next/navigation';
import { useRef, useState, type FormEvent } from 'react';
import { ErrorSummary, useErrorTitle, type FieldError } from '@/components/ErrorSummary';
import { ApiError, type ApiClient } from '@/lib/api/client';
import { browserApi } from '@/lib/api/browser';
import {
  FORMAT_LABELS,
  MATCH_FORMATS,
  TITLE_MAX_LENGTH,
  type MatchFormat,
} from '@/lib/api/types';

type Api = Pick<ApiClient, 'createMatch'>;

function validate(title: string, format: string): FieldError[] {
  const errors: FieldError[] = [];
  const trimmed = title.trim();
  if (trimmed.length === 0) {
    errors.push({ field: 'title', message: 'Enter a title for the match' });
  } else if (trimmed.length > TITLE_MAX_LENGTH) {
    errors.push({ field: 'title', message: `Title must be ${TITLE_MAX_LENGTH} characters or fewer` });
  }
  if (!(MATCH_FORMATS as readonly string[]).includes(format)) {
    errors.push({ field: 'format', message: 'Select the match format' });
  }
  return errors;
}

export function NewMatchForm({ api = browserApi }: { api?: Api }) {
  const router = useRouter();
  const [title, setTitle] = useState('');
  const [format, setFormat] = useState('');
  const [errors, setErrors] = useState<FieldError[]>([]);
  const [general, setGeneral] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);

  useErrorTitle(errors.length > 0 || general !== undefined);

  const errorFor = (field: string) => errors.find((e) => e.field === field);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busyRef.current) return;
    const found = validate(title, format);
    setErrors(found);
    setGeneral(undefined);
    if (found.length > 0) return;

    busyRef.current = true;
    setBusy(true);
    try {
      const match = await api.createMatch({ title: title.trim(), format: format as MatchFormat });
      router.push(`/matches/${match.id}`);
    } catch (e) {
      busyRef.current = false;
      setBusy(false);
      if (e instanceof ApiError && e.status === 401) {
        router.push('/');
        return;
      }
      setGeneral('We could not create the match. Check the details and try again.');
    }
  }

  const titleError = errorFor('title');
  const formatError = errorFor('format');

  return (
    <>
      <ErrorSummary errors={errors} general={general} />
      <form noValidate onSubmit={onSubmit} className="stack">
        <div className={`field${titleError ? ' field--error' : ''}`}>
          <label htmlFor="title" className="field__label">
            Title
          </label>
          <p id="title-hint" className="field__hint">
            For example, &ldquo;Sunday doubles at the park&rdquo;. Do not enter contact details.
          </p>
          {titleError ? (
            <p id="title-error" className="field__error">
              <span className="visually-hidden">Error: </span>
              {titleError.message}
            </p>
          ) : null}
          <input
            id="title"
            name="title"
            type="text"
            className="input"
            autoComplete="off"
            maxLength={TITLE_MAX_LENGTH * 2}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            aria-describedby={titleError ? 'title-hint title-error' : 'title-hint'}
            aria-invalid={titleError ? true : undefined}
          />
        </div>

        <div className={`field${formatError ? ' field--error' : ''}`}>
          <label htmlFor="format" className="field__label">
            Format
          </label>
          {formatError ? (
            <p id="format-error" className="field__error">
              <span className="visually-hidden">Error: </span>
              {formatError.message}
            </p>
          ) : null}
          <select
            id="format"
            name="format"
            className="input select"
            value={format}
            onChange={(e) => setFormat(e.target.value)}
            aria-describedby={formatError ? 'format-error' : undefined}
            aria-invalid={formatError ? true : undefined}
          >
            <option value="">Choose a format</option>
            {MATCH_FORMATS.map((f) => (
              <option key={f} value={f}>
                {FORMAT_LABELS[f]}
              </option>
            ))}
          </select>
        </div>

        <button type="submit" className="button" aria-busy={busy}>
          {busy ? 'Creating match…' : 'Create match'}
        </button>
      </form>
    </>
  );
}
