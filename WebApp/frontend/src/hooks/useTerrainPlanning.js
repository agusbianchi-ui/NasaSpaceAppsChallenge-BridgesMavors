import { useEffect, useMemo, useRef, useState } from "react";
import {
  useMissionSession,
  updateMissionSession,
} from "../services/missionSession.js";
import {
  buildVisualRoute,
  importPreliminaryRoute,
} from "../terrain/visualRoute.js";

// Planning state is independent of the renderer and never changes scientific data.
export function useTerrainPlanning(grid, baseUrl) {
  const [mode, setMode] = useState("navigation");
  const [kind, setKind] = useState("Start");
  const session = useMissionSession();
  const points = session.points,
    history = session.history;
  const setPoints = (next) => updateMissionSession({ points: next }, true);
  const setHistory = (next) =>
    updateMissionSession({
      history: typeof next === "function" ? next(history) : next,
    });
  const inspection = session.inspection;
  const setInspection = (point) => updateMissionSession({ inspection: point });
  const [selectedId, setSelectedId] = useState(null);
  const [moving, setMoving] = useState(false);
  const [message, setMessage] = useState("");
  const [importing, setImporting] = useState(false);
  const importController = useRef(null);
  useEffect(() => () => importController.current?.abort(), []);
  const activePath = (!session.stale ? session.results : null)?.routes?.find(
    (route) => route.success && route.strategy === session.activeStrategy,
  )?.path_local;
  const route = useMemo(
    () =>
      grid
        ? buildVisualRoute(
            grid,
            session.results && !session.stale ? activePath || [] : points,
          )
        : { vertices: [], error: null },
    [grid, points, activePath, session.results, session.stale],
  );
  const selected =
    points.find((point) => point.id === selectedId) ||
    (inspection?.id === selectedId ? inspection : null);
  function commit(next) {
    importController.current?.abort();
    setHistory((previous) => [...previous.slice(-49), points]);
    setPoints(next);
    setMoving(false);
  }
  function select(id) {
    setSelectedId(id);
    setMoving(false);
  }
  function inspect(hit) {
    if (!hit) {
      setMessage("No valid terrain at this position.");
      return;
    }
    if (hit.markerId) {
      select(hit.markerId);
      return;
    }
    const point = {
      ...hit,
      id: "inspection",
      type: "Inspection point",
      label: "Inspection",
    };
    setInspection(point);
    select(point.id);
    setMessage(
      "Visual marker height uses exaggerated geometry. Scientific elevation is reported separately in the inspection panel.",
    );
  }
  function place(hit) {
    if (hit?.markerId) {
      select(hit.markerId);
      return;
    }
    if (mode === "inspect") {
      inspect(hit);
      return;
    }
    if (mode !== "planning") return;
    if (!hit) {
      setMessage("Choose a valid terrain cell.");
      return;
    }
    if (moving && selected) {
      edit(selected.id, { x: hit.x, z: hit.z });
      return;
    }
    const point = { ...hit, id: crypto.randomUUID(), type: kind, label: kind };
    const next =
      kind === "Waypoint" ? [...points] : points.filter((p) => p.type !== kind);
    const destination = next.findIndex((p) => p.type === "Destination");
    if (kind === "Start") next.unshift(point);
    else if (kind === "Waypoint" && destination >= 0)
      next.splice(destination, 0, point);
    else next.push(point);
    commit(next);
    select(point.id);
    setMessage("Preliminary visual route. Traversability is not assessed.");
    if (kind === "Start") setKind("Destination");
    else if (kind === "Destination") setKind("Waypoint");
  }
  function edit(id, changes) {
    const point =
      points.find((p) => p.id === id) ||
      (inspection?.id === id ? inspection : null);
    if (!point || !grid) return;
    const next = { ...point, ...changes },
      y = grid.getVisualElevation(next.x, next.z);
    if (y === null) {
      setMessage("Edit rejected: this position has no valid visual elevation.");
      return;
    }
    next.y = y;
    next.label = next.label.trim().slice(0, 60) || next.type;
    if (id === "inspection") setInspection(next);
    else commit(points.map((p) => (p.id === id ? next : p)));
    setMoving(false);
    setMessage("Marker updated and anchored to the visual surface.");
  }
  function remove(id) {
    if (id === "inspection") setInspection(null);
    else commit(points.filter((p) => p.id !== id));
    setSelectedId(null);
    setMoving(false);
  }
  function undo() {
    if (!history.length) return;
    importController.current?.abort();
    setPoints(history.at(-1));
    setHistory(history.slice(0, -1));
    setMoving(false);
    setSelectedId(null);
    setMessage("Last route modification undone.");
  }
  async function importReference() {
    if (!grid || importing) return;
    const controller = new AbortController();
    importController.current = controller;
    setImporting(true);
    try {
      const response = await fetch(`${baseUrl}/preliminary-route.json`, {
        signal: controller.signal,
      });
      if (!response.ok)
        throw new Error(`Reference download failed (${response.status}).`);
      const next = importPreliminaryRoute(await response.json(), grid);
      controller.signal.throwIfAborted();
      commit(next);
      setSelectedId(next[0].id);
      setMessage(
        `Imported ${next.length} geometrically matched reference points. The reference circle and point indicate the start region and destination only. Not a validated expedition route.`,
      );
    } catch (error) {
      if (error.name !== "AbortError") setMessage(error.message);
    } finally {
      if (importController.current === controller) {
        importController.current = null;
        setImporting(false);
      }
    }
  }
  function useInspected(type) {
    if (!inspection || !grid) return;
    const point = { ...inspection, id: crypto.randomUUID(), type, label: type };
    const next =
      type === "Waypoint" ? [...points] : points.filter((p) => p.type !== type);
    if (type === "Start") next.unshift(point);
    else if (type === "Waypoint" && next.some((p) => p.type === "Destination"))
      next.splice(
        next.findIndex((p) => p.type === "Destination"),
        0,
        point,
      );
    else next.push(point);
    commit(next);
    select(point.id);
    setMode("planning");
    setMessage(`Inspection point added as ${type}.`);
  }
  return {
    useInspected,
    mode,
    setMode: (value) => {
      setMode(value);
      setMoving(false);
    },
    kind,
    setKind,
    points,
    inspection,
    selected,
    selectedId,
    select,
    route,
    message,
    moving,
    importing,
    place,
    inspect,
    edit,
    remove,
    undo,
    canUndo: history.length > 0,
    importReference,
    moveSelected: () => {
      setMode("planning");
      setMoving(true);
      setMessage(
        "Click or tap a valid surface position to move the selected marker.",
      );
    },
    clear: () => {
      commit([]);
      updateMissionSession({ results: null, stale: false });
      setSelectedId(null);
      setMessage("Route cleared. Undo restores it.");
    },
  };
}
