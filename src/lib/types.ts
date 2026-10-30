export type Result = 'V' | 'E' | 'D';

export interface TeamRow {
  pos: number;
  id: number;
  name: string;
  short: string;
  crest: string | null;
  j: number; v: number; e: number; d: number;
  gp: number; gc: number; sg: number; pts: number;
  form: Result[];
  p_title: number;
  p_lib: number;
  p_rel: number;
  exp_pts: number;
  pos_probs: number[];
  attack: number;
  defense: number;
}

export interface NextMatch {
  utc_date: string;
  matchday: number | null;
  status: string;
  home: string;
  away: string;
  home_crest: string | null;
  away_crest: string | null;
  p_home: number;
  p_draw: number;
  p_away: number;
}

export interface Snapshot {
  generated_at: string;
  season: number;
  sample: boolean;
  rodada: number;
  played: number;
  remaining: number;
  n_sims: number;
  rules: { teams: number; libertadores_direct: number; relegated: number };
  model: { mu_home: number; mu_away: number; half_life_matchdays: number };
  teams: TeamRow[];
  next_matches: NextMatch[];
}

export interface HistoryEntry {
  rodada: number;
  at: string;
  sample?: boolean;
  title: Record<string, number>;
  rel: Record<string, number>;
}
