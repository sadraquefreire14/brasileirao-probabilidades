import type { APIRoute } from 'astro';
import { snapshot } from '../lib/data';

/** Usado pela página para detectar um build mais novo e oferecer recarregar. */
export const GET: APIRoute = () =>
  new Response(JSON.stringify({ generated_at: snapshot.generated_at, rodada: snapshot.rodada }), {
    headers: { 'Content-Type': 'application/json' },
  });
