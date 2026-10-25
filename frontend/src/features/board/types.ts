// Contrato de GET /api/operator/live v2. Espejo de backend/src/agent_zero/live/models.py.
// Lo mantiene el líder: las tareas lo importan y no lo editan.

export type SessionKind = "audience" | "swarm" | "prober";
export type KpiScope = "all" | "swarm_prober";
export type RouteName = "protected" | "honeypot";
export type AttemptStatus = "queued" | "running" | "evaluated" | "inconclusive";
export type AttemptOutcome =
  | "confirmed_violation"
  | "prevented"
  | "not_achieved"
  | "contained_honeypot"
  | "inconclusive";

/** Llamada a herramienta negada por el gateway (evento `tool_denied`). */
export interface LiveDenial {
  tool: string;
  /** Valor de `GatewayReason`, p. ej. "business_rule_denied" o "rate_limited". */
  reason: string;
  /** Validador que negó, p. ej. "order_belongs_to_session_customer" o "flow:…"; null si no hubo. */
  validator: string | null;
}

/** Técnica del ataque. Solo se conoce para el Prober (`case_json` de su caso de campaña); el
 * enjambre llega por la API pública y el servidor no sabe su plantilla, así que va null. */
export interface LiveTechnique {
  /** Valor de `AttackFamily`: direct_injection, indirect_injection, goal_hijacking, tool_misuse,
   * tool_poisoning o memory_poisoning. */
  family: string;
  /** Mutador aplicado; null = plantilla base. */
  mutator: string | null;
}

/** Parche activado que cubre la violación de este intento. */
export interface LivePatch {
  version: number;
  /** Segundos entre el cierre del intento (updated_at) y la activación de la política (>= 0).
   * Ojo: la mediana de `patches` se mide desde la creación del hallazgo, no desde el intento. */
  seconds_after: number;
}

export interface LiveAttempt {
  id: string;
  /** Posición 1..N del intento dentro de la sesión del tablero (cuenta todos, no solo los enviados). */
  number: number;
  status: AttemptStatus;
  /** null mientras no termina o si la sesión está enmascarada (`concealed`). */
  outcome: AttemptOutcome | null;
  /** null si la sesión está enmascarada. */
  route: RouteName | null;
  policy_version: number;
  messages: string[];
  /** "" si la sesión está enmascarada: el texto no viaja. */
  reply: string;
  /** [] si la sesión está enmascarada. */
  denials: LiveDenial[];
  /** [] si la sesión está enmascarada o no hubo violación. */
  violated_objectives: string[];
  /** null si no hay parche activado que cubra este intento o si está enmascarada. */
  patched_by: LivePatch | null;
  /** null fuera del Prober o si está enmascarada: la vista no inventa una técnica. */
  technique: LiveTechnique | null;
  created_at: string;
  updated_at: string;
}

export interface LiveSession {
  /** `sess-…` para público y enjambre; para el Prober es el `campaign_id` (una sesión por campaña). */
  session_id: string;
  /** Para el Prober: "Prober · " + últimos 4 caracteres del campaign_id. */
  alias: string;
  kind: SessionKind;
  /** true = Público antes de revelar: sin ruta, desenlace, respuesta ni negaciones. */
  concealed: boolean;
  route: RouteName | null;
  customer_id: string;
  last_activity: string;
  /** Todos los intentos de la sesión (los `attempts` enviados son como máximo los últimos 30). */
  attempt_total: number;
  /** Contadores sobre todos los intentos terminados de la sesión; null si `concealed`. */
  contained_n: number | null;
  prevented_n: number | null;
  leaked_n: number | null;
  attempts: LiveAttempt[];
}

export interface TokenPart {
  measured: boolean;
  tokens: number | null;
  calls: number;
}

export interface LiveKpis {
  attacks: {
    /** Intentos terminados (evaluated o inconclusive) de toda la ronda, sin repeticiones. */
    n: number;
    audience: number;
    swarm: number;
    prober: number;
    /** Intentos en cola o en curso (no cuentan en n). */
    in_flight: number;
    source: string;
  };
  safe_space: {
    /** Denominador: sesiones del tablero con alcance (sin Público hasta revelar). */
    n: number;
    /** Sesiones con alcance en ruta señuelo con al menos un intento contenido. */
    safe_sessions: number;
    /** Sesiones con alcance en ruta señuelo. */
    diverted_sessions: number;
    /** Intentos terminados con alcance con desenlace contained_honeypot. */
    contained_attempts: number;
    scope: KpiScope;
    label: string;
    source: string;
  };
  leaked: {
    /** Intentos terminados con alcance (sin Público hasta revelar). */
    n: number;
    /** Intentos con alcance con confirmed_violation. */
    leaked: number;
    /** Siempre trae OBJ-ORDER, OBJ-MEMORY y OBJ-REFUND (0 si no hay). */
    by_objective: Record<string, number>;
    /** Suma de by_objective; puede superar `leaked` porque un intento viola varios objetivos. */
    objective_sum: number;
    scope: KpiScope;
    label: string;
    source: string;
  };
  attacker_tokens: {
    measured: boolean;
    label: string;
    attacker: TokenPart;
    decoy: TokenPart;
    n: number;
    source: string;
  };
  patches: {
    n: number;
    activated: number;
    current_version: number;
    median_seconds_to_patch: number | null;
    findings_covered: number;
    /** Hallazgos con al menos un intento con alcance (cubiertos o no); covered <= total. */
    findings_total: number;
    source: string;
  };
}

export interface LiveBoard {
  revealed: boolean;
  /** false = entradas pausadas («Acceso cerrado»). */
  accepting: boolean;
  llm_mode: string;
  policy_version: number;
  /** Sesiones del tablero con al menos un intento (Prober agrupado por campaña). */
  sessions_total: number;
  sessions: LiveSession[];
  kpis: LiveKpis;
  generated_at: string;
}

// ---- Tipos compartidos de la vista (no vienen del servidor) ----

/** Tono del estado de un chat. Clase CSS: `st-${tone}`. */
export type ChatTone = "neutral" | "safe" | "leak" | "blocked";

export interface ChatStatus {
  tone: ChatTone;
  /** "Atacando" | "En espacio seguro" | "Se filtró" | "Bloqueado" | "Acceso cerrado" */
  label: string;
  detail: string;
}

/** Lo que el carrusel necesita de cada chat para su indicador en la barra. */
export interface CarouselItem {
  id: string;
  label: string;
  short: string;
  tone: ChatTone;
  title: string;
  /** Cuando cambia, el indicador muestra el anillo de evento durante 4 s. */
  pulseKey: string;
}
