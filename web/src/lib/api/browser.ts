// The browser's API client: same origin, through the `/api` rewrite (api-sprint-00 §1, §8).
import { createApiClient } from './client';

export const browserApi = createApiClient({ baseUrl: '/api' });
