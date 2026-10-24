/* Agent Zero snapshot adapter. No network calls, mutations, or fabricated results. */
(function (global) {
  "use strict";

  const OUTCOMES = {
    confirmed_violation: ["Violación confirmada", "danger"],
    prevented: ["Bloqueado", "success"],
    not_achieved: ["No logrado", "neutral"],
    contained_honeypot: ["Contenido en señuelo", "success"],
    inconclusive: ["Inconcluso", "warning"],
    apparent_success: ["Éxito aparente", "warning"],
  };
  const ACTION_LABELS = {
    baseline_attack: "Ataque base",
    protected_replay: "Reproducción",
    legitimate_before: "Control legítimo · antes",
    legitimate_after: "Control legítimo · después",
    followup_same_session: "Continuación de sesión",
    legitimate_memory: "Control de memoria",
  };
  const USAGE_FIELDS = ["input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens"];
  const COST_FIELDS = ["input_usd", "output_usd", "cache_read_usd", "cache_write_usd"];
  const list = (value) => Array.isArray(value) ? value : [];
  const key = (value) => typeof value === "string" ? value.toLowerCase() : "";
  const number = (value) => typeof value === "number" && Number.isFinite(value) && value >= 0;
  const unique = (values) => [...new Set(values.filter((value) => value != null && value !== ""))];

  function timeMs(value) {
    if (typeof value !== "string" || !value.trim()) return null;
    let iso = value.trim().replace(/^(\d{4}-\d{2}-\d{2}) /, "$1T");
    // SQLite stores UTC without an offset; never interpret it in the browser's local zone.
    if (iso.includes("T") && !/(?:z|[+-]\d{2}:?\d{2})$/i.test(iso)) iso += "Z";
    const result = Date.parse(iso);
    return Number.isFinite(result) ? result : null;
  }

  function shortId(value) {
    if (value == null || value === "") return "—";
    const id = String(value);
    return id.length > 17 ? id.slice(0, 8) + "…" + id.slice(-6) : id;
  }

  function formatTime(value) {
    const ms = timeMs(value);
    if (ms == null) return "—";
    return new Intl.DateTimeFormat("es-VE", {
      timeZone: "UTC", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
    }).format(ms) + " UTC";
  }

  function duration(value) {
    if (!number(value)) return "—";
    if (value < 1000) return (value < 10 ? value.toFixed(1) : Math.round(value)) + " ms";
    if (value < 60000) return (value / 1000).toFixed(value < 10000 ? 2 : 1) + " s";
    const seconds = Math.floor(value / 1000);
    if (seconds < 3600) return Math.floor(seconds / 60) + "m " + (seconds % 60) + "s";
    return Math.floor(seconds / 3600) + "h " + Math.floor((seconds % 3600) / 60) + "m";
  }

  function outcomeLabel(value) {
    return OUTCOMES[key(value)]?.[0] || (value ? String(value) : "Pendiente");
  }

  function outcomeTone(value) {
    return OUTCOMES[key(value)]?.[1] || "neutral";
  }

  function totalFrom(record, fields, totalField) {
    if (record == null || typeof record !== "object") return null;
    if (number(record[totalField])) return record[totalField];
    const present = fields.filter((field) => number(record[field]));
    return present.length ? present.reduce((sum, field) => sum + record[field], 0) : null;
  }

  function knownSum(values) {
    const known = values.filter(number);
    return known.length ? known.reduce((sum, value) => sum + value, 0) : null;
  }

  function dedupeEvents(events) {
    const seen = new Set();
    return events.filter((event) => {
      if (!event || typeof event !== "object") return false;
      const identity = event.id != null
        ? "id:" + event.id
        : JSON.stringify([event.type, event.timestamp, event.attempt_id, event.session_id, event.data]);
      if (seen.has(identity)) return false;
      seen.add(identity);
      return true;
    }).sort((a, b) => {
      const at = timeMs(a.timestamp), bt = timeMs(b.timestamp);
      if (at != null && bt != null && at !== bt) return at - bt;
      return (Number(a.id) || 0) - (Number(b.id) || 0);
    });
  }

  function toolOperations(events) {
    const operations = new Set();
    let uncorrelatedTerminals = 0;
    for (const event of events) {
      const type = key(event.type);
      if (!type.startsWith("tool_")) continue;
      const operation = event.data?.operation_id;
      if (operation) operations.add(operation);
      // A proposal without an operation ID is not another call. With no correlation,
      // terminal events are the only countable evidence; dedupeEvents removed repeats.
      else if (type === "tool_completed" || type === "tool_denied") uncorrelatedTerminals += 1;
    }
    return operations.size + uncorrelatedTerminals;
  }

  function firstTime(events, type) {
    for (const event of events) {
      if (key(event.type) !== type) continue;
      const at = timeMs(event.timestamp);
      if (at != null) return at;
    }
    return null;
  }

  function delta(start, end) {
    return start != null && end != null && end >= start ? end - start : null;
  }

  function normalize(snapshot) {
    const raw = snapshot && typeof snapshot === "object" ? snapshot : {};
    const events = dedupeEvents(list(raw.events));
    const rawSessions = list(raw.sessions);
    const sessionById = new Map(rawSessions.map((session) => [session.id, session]));
    const actions = new Map(list(raw.actions).map((action) => [action.attempt_id, action]));
    const campaignByAttempt = new Map();
    for (const campaign of list(raw.campaigns)) {
      for (const attemptId of list(campaign.attempt_ids)) campaignByAttempt.set(attemptId, campaign.id);
    }

    const calls = list(raw.calls).map((call) => {
      const tokens = totalFrom(call.usage, USAGE_FIELDS, "total_tokens");
      const costUsd = totalFrom(call.cost, COST_FIELDS, "total_usd");
      return {
        ...call, raw: call, scope: { ...(call.scope || {}) },
        usageKnown: tokens != null, costKnown: costUsd != null, tokens, costUsd,
      };
    });

    const attempts = list(raw.attempts).map((attempt) => {
      const sessionId = attempt.session_id ?? attempt.sessionId ?? null;
      const session = sessionById.get(sessionId);
      const action = actions.get(attempt.id);
      const attemptEvents = dedupeEvents([
        ...list(attempt.events), ...events.filter((event) => event.attempt_id === attempt.id),
      ]);
      const attemptCalls = calls.filter((call) => call.scope.attempt_id === attempt.id);
      const queuedAt = firstTime(attemptEvents, "attempt_queued");
      const startedAt = firstTime(attemptEvents, "attempt_started");
      const completedAt = firstTime(attemptEvents, "attempt_completed");
      const evaluatedAt = firstTime(attemptEvents, "attempt_evaluated");
      const verdicts = list(attempt.assessment?.verdicts);
      const campaignId = attempt.campaign_id || campaignByAttempt.get(attempt.id) || null;
      const origin = key(attempt.origin);
      const sourceLabel = ACTION_LABELS[action?.label]
        || (campaignId ? "Prober · " + shortId(campaignId)
          : origin === "audience" ? "Audiencia"
          : origin === "autonomous" ? "Autónomo"
          : origin || "Origen desconocido");
      return {
        ...attempt,
        raw: attempt,
        id: attempt.id ?? null,
        sessionId,
        alias: session?.alias || shortId(sessionId),
        customer: session?.customer_name || attempt.customer_id || session?.customer_id || null,
        customerId: attempt.customer_id || session?.customer_id || null,
        objectiveIds: unique(verdicts.map((verdict) => verdict.objective_id)),
        violatedObjectiveIds: unique(verdicts.filter((verdict) => verdict.violated === true).map((verdict) => verdict.objective_id)),
        declaredObjectiveId: attempt.objective_id ?? null,
        policyVersion: attempt.policy_version ?? attempt.policyVersion ?? null,
        route: key(attempt.route) || null,
        status: key(attempt.status) || null,
        outcome: key(attempt.outcome) || null,
        messages: list(attempt.messages).slice(),
        reply: typeof attempt.reply === "string" ? attempt.reply : "",
        createdAt: attempt.created_at ?? attempt.createdAt ?? null,
        events: attemptEvents,
        calls: attemptCalls,
        toolCount: toolOperations(attemptEvents),
        queueMs: delta(queuedAt, startedAt),
        executionMs: delta(startedAt, completedAt),
        totalMs: delta(queuedAt ?? timeMs(attempt.created_at), evaluatedAt ?? completedAt),
        usageKnown: attemptCalls.some((call) => call.usageKnown),
        tokens: knownSum(attemptCalls.map((call) => call.tokens)),
        costUsd: knownSum(attemptCalls.map((call) => call.costUsd)),
        campaignId,
        sourceLabel,
        label: action?.label ?? null,
        legitimate: typeof action?.legitimate === "boolean" ? action.legitimate : null,
      };
    });

    const sessionIds = unique([...rawSessions.map((session) => session.id), ...attempts.map((attempt) => attempt.sessionId)]);
    const sessions = sessionIds.map((id) => {
      const session = sessionById.get(id);
      const sessionAttempts = attempts.filter((attempt) => attempt.sessionId === id);
      const routeEvents = events.filter((event) => event.session_id === id && key(event.type) === "route_changed");
      const lastRoute = routeEvents.length ? routeEvents[routeEvents.length - 1].data?.route : null;
      return {
        ...(session || {}), raw: session || null, id,
        alias: session?.alias || shortId(id),
        customer: session?.customer_name || session?.customer_id || sessionAttempts[0]?.customer || null,
        customerId: session?.customer_id || sessionAttempts[0]?.customerId || null,
        createdAt: session?.created_at ?? null,
        route: key(session?.route) || key(lastRoute) || sessionAttempts[sessionAttempts.length - 1]?.route || null,
        orderIds: Array.isArray(session?.order_ids) ? session.order_ids.slice() : null,
        order_ids: Array.isArray(session?.order_ids) ? session.order_ids.slice() : null,
        attempts: sessionAttempts,
        events: events.filter((event) => event.session_id === id),
        routeEvents,
        memory: null,
        memoryCount: null,
        inferred: !session,
      };
    });

    const findings = list(raw.findings).map((finding) => ({ ...finding, raw: finding }));
    const policies = list(raw.policies).map((policy) => ({ ...policy, raw: policy }));
    const byOutcome = Object.fromEntries(Object.keys(OUTCOMES).map((outcome) => [outcome, 0]));
    for (const attempt of attempts) {
      if (attempt.outcome) byOutcome[attempt.outcome] = (byOutcome[attempt.outcome] || 0) + 1;
    }
    const fromAction = (label) => attempts.find((attempt) => attempt.label === label) || null;
    const hasComparisonAction = attempts.some((attempt) => ["baseline_attack", "protected_replay", "legitimate_before", "legitimate_after"].includes(attempt.label));
    const stats = {
      totalAttempts: attempts.length,
      byOutcome,
      outcomes: byOutcome,
      queued: attempts.filter((attempt) => attempt.status === "queued").length,
      running: attempts.filter((attempt) => attempt.status === "running").length,
      toolOperations: attempts.reduce((sum, attempt) => sum + attempt.toolCount, 0),
      calls: calls.length,
      measuredUsageCalls: calls.filter((call) => key(call.origin) === "live" && call.usageKnown).length,
      usageKnownCalls: calls.filter((call) => call.usageKnown).length,
      unknownUsageCalls: calls.filter((call) => !call.usageKnown).length,
      costKnownCalls: calls.filter((call) => call.costKnown).length,
      tokens: knownSum(calls.map((call) => call.tokens)),
      costUsd: knownSum(calls.map((call) => call.costUsd)),
      openFindings: findings.filter((finding) => ["open", "reopened"].includes(key(finding.status))).length,
      sessionCount: sessions.length,
    };
    return {
      raw,
      id: raw.run_id ?? raw.id ?? null,
      capturedAt: raw.captured_at ?? raw.capturedAt ?? null,
      provider: raw.provider ?? null,
      model: raw.model ?? null,
      arena: { ...(raw.arena || {}) },
      attempts, sessions, findings, policies, events, calls,
      usage: list(raw.usage).map((usage) => ({ ...usage })),
      stats,
      comparison: hasComparisonAction ? {
        before: fromAction("baseline_attack"),
        after: fromAction("protected_replay"),
        legitBefore: fromAction("legitimate_before"),
        legitAfter: fromAction("legitimate_after"),
      } : null,
    };
  }

  global.ZeroData = Object.freeze({ normalize, shortId, formatTime, duration, outcomeLabel, outcomeTone });
})(typeof window !== "undefined" ? window : globalThis);
