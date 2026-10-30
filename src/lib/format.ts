const pctFmt = new Intl.NumberFormat('pt-BR', {
  style: 'percent',
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

/** Probabilidade (0–1) em texto, sem arredondar extremos para 0% ou 100%. */
export function pct(v: number): string {
  if (!Number.isFinite(v)) return '—';
  if (v <= 0) return '0%';
  if (v < 0.001) return '<0,1%';
  if (v >= 1) return '100%';
  if (v > 0.999) return '>99,9%';
  return pctFmt.format(v);
}

export const signed = (n: number): string => (n > 0 ? `+${n}` : String(n));

const dateTimeFmt = new Intl.DateTimeFormat('pt-BR', {
  timeZone: 'America/Sao_Paulo',
  day: '2-digit',
  month: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
});

const longFmt = new Intl.DateTimeFormat('pt-BR', {
  timeZone: 'America/Sao_Paulo',
  dateStyle: 'long',
  timeStyle: 'short',
});

export const shortDateTime = (iso: string): string => dateTimeFmt.format(new Date(iso));
export const longDateTime = (iso: string): string => longFmt.format(new Date(iso));

/** Posição da zona na tabela, para estilo. */
export function zone(pos: number, libDirect: number, relegated: number, teams: number): 'lib' | 'rel' | null {
  if (pos <= libDirect) return 'lib';
  if (pos > teams - relegated) return 'rel';
  return null;
}
