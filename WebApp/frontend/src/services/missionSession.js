// Single mission session shared across map pages; no renderer or scientific calculations here.
import { useSyncExternalStore } from "react";
export const MODEL_SHA =
  "8786642ea6461b4c62ee5b0f9a3b190a962e84ef1e3844dd293a73494068ab48";
export const DEFAULT_MISSION = {
  displacement: "foot",
  velocity: 1,
  max_slope: 25,
  max_descent_slope: 25,
  thermal_min: -40,
  thermal_max: 30,
  high_dust: 0.3,
  high_wind: 15,
  roughness_scale: 50,
  unknown_policy: "topography_only",
  dust_scenario: "none",
  mars_year: 36,
  sol: 1,
  climate_scenario: "unavailable",
  ls: null,
  local_time: null,
  slope_weight: 2,
  roughness_weight: 1,
  environment_weight: 2,
  unknown_weight: 1,
};
const empty = {
  points: [],
  history: [],
  inspection: null,
  mission: DEFAULT_MISSION,
  strategy: "balanced",
  results: null,
  activeStrategy: "balanced",
  stale: false,
  excluded: [],
  hazards: null,
  science: null,
};
let saved;
try {
  saved = JSON.parse(localStorage.getItem("bridges-mission-v1") || "null");
} catch {
  saved = null;
}
let state =
  saved?.source === MODEL_SHA
    ? {
        ...empty,
        ...saved.state,
        mission: { ...DEFAULT_MISSION, ...saved.state?.mission },
        history: [],
        hazards: null,
        science: null,
      }
    : empty;
const listeners = new Set();
export function getMissionSession() {
  return state;
}
export function updateMissionSession(changes, invalidate = false) {
  const missionChanged = changes.mission && Object.keys(DEFAULT_MISSION).some(
    (key) => changes.mission[key] !== state.mission[key],
  );
  state = {
    ...state,
    ...changes,
    ...(missionChanged ? { hazards: null, science: null } : {}),
    ...(invalidate ? { stale: Boolean(state.results) } : {}),
  };
  try {
    localStorage.setItem(
      "bridges-mission-v1",
      JSON.stringify({
        source: MODEL_SHA,
        state: { ...state, history: [], hazards: null, science: null },
      }),
    );
  } catch {
    /* In-memory session remains usable when browser storage is full/disabled. */
  }
  for (const notify of listeners) notify();
}
function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
export function useMissionSession() {
  return useSyncExternalStore(subscribe, getMissionSession, getMissionSession);
}
export function missionFingerprint(s) {
  return JSON.stringify({
    points: s.points.map(({ x, z }) => ({ x, z })),
    mission: s.mission,
    excluded: s.excluded,
    strategy: s.strategy,
  });
}
export function exportMission(s) {
  return {
    format: "bridges-mission-v1",
    source_sha256: MODEL_SHA,
    points: s.points,
    mission: s.mission,
    strategy: s.strategy,
    excluded_cells: s.excluded,
    results: s.results,
    notice:
      "Hypothetical planning; revalidate after import. Scientific data and original model are not included.",
  };
}
export function validateMissionImport(data, grid) {
  if (
    data.format !== "bridges-mission-v1" ||
    data.source_sha256 !== MODEL_SHA ||
    !Array.isArray(data.points) ||
    data.points.length > 200
  )
    throw new Error("Unsupported mission format or terrain source.");
  const types = ["Start", "Destination", "Waypoint"];
  const points = data.points.map((p, i) => {
    if (!types.includes(p.type) || !grid.isValidTerrainPosition(p.x, p.z))
      throw new Error(`Invalid imported point ${i + 1}.`);
    return {
      id: crypto.randomUUID(),
      type: p.type,
      label: String(p.label || p.type).slice(0, 60),
      x: p.x,
      z: p.z,
      y: grid.getVisualElevation(p.x, p.z),
    };
  });
  if (
    points.filter((p) => p.type === "Start").length > 1 ||
    points.filter((p) => p.type === "Destination").length > 1
  )
    throw new Error("Duplicate start or destination.");
  const mission = { ...DEFAULT_MISSION };
  for (const key of Object.keys(mission))
    if (data.mission?.[key] !== undefined) mission[key] = data.mission[key];
  const ranges = {
    velocity: [0.1, 10],
    max_slope: [0, 60],
    max_descent_slope: [0, 60],
    thermal_min: [-150, 100],
    thermal_max: [-150, 150],
    high_dust: [0.001, 10],
    high_wind: [0.001, 150],
    roughness_scale: [0.001, 1000],
    sol: [1, 669],
    slope_weight: [0, 20],
    roughness_weight: [0, 20],
    environment_weight: [0, 20],
    unknown_weight: [0, 20],
  };
  for (const [key, [min, max]] of Object.entries(ranges))
    if (
      !Number.isFinite(mission[key]) ||
      mission[key] < min ||
      mission[key] > max
    )
      throw new Error(`Invalid mission parameter: ${key}.`);
  if (
    mission.thermal_min >= mission.thermal_max ||
    !Number.isInteger(mission.sol) ||
    mission.mars_year !== 36 ||
    mission.climate_scenario !== "unavailable" ||
    mission.ls !== null ||
    mission.local_time !== null ||
    !["foot", "rover"].includes(mission.displacement) ||
    !["none", "my36"].includes(mission.dust_scenario) ||
    !["avoid", "penalize", "topography_only"].includes(mission.unknown_policy)
  )
    throw new Error("Unsupported mission assumptions or scenario.");
  if (
    points.some(
      (p, i) =>
        (p.type === "Start" && i !== 0) ||
        (p.type === "Destination" && i !== points.length - 1),
    )
  )
    throw new Error("Start must be first and Destination last.");
  if (
    !["shortest", "low_slope", "environmental", "balanced"].includes(
      data.strategy,
    )
  )
    throw new Error("Invalid strategy.");
  const excluded = data.excluded_cells || [];
  if (
    !Array.isArray(excluded) ||
    excluded.length > 20000 ||
    excluded.some(
      (cell) =>
        !Array.isArray(cell) ||
        cell.length !== 2 ||
        !cell.every(Number.isInteger) ||
        cell[0] < 0 ||
        cell[1] < 0 ||
        cell[0] >= grid.metadata.rows ||
        cell[1] >= grid.metadata.columns,
    )
  )
    throw new Error("Invalid excluded cells.");
  return {
    points,
    mission,
    strategy: data.strategy,
    excluded,
    results: null,
    stale: false,
    history: [],
  };
}
