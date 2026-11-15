import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import "../../styles/terrain.css";
import { useTerrainPlanning } from "../../hooks/useTerrainPlanning.js";
import TerrainPlanningControls from "./TerrainPlanningControls.jsx";
import ScientificInspectionPanel from "../dashboard/ScientificInspectionPanel.jsx";
import {
  inspectMissionPoint,
  fetchHazardRegions,
} from "../../services/marsApi.js";
import {
  useMissionSession,
  getMissionSession,
  updateMissionSession,
} from "../../services/missionSession.js";
import MissionPlanningPanel from "./MissionPlanningPanel.jsx";

const BASE_URL = `${import.meta.env.BASE_URL}terrain`;

const MarsTerrainViewer = forwardRef(function MarsTerrainViewer(
  { onInspect, onPlaceMarker },
  ref,
) {
  const container = useRef(null),
    host = useRef(null),
    engine = useRef(null);
  const callbacks = useRef(null);
  const [grid, setGrid] = useState(null);
  const planning = useTerrainPlanning(grid, BASE_URL);
  const [attempt, setAttempt] = useState(0);
  const [status, setStatus] = useState("idle");
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState("");
  const [quality, setQuality] = useState("medium");
  const [fullscreen, setFullscreen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [notice, setNotice] = useState("");
  const [stats, setStats] = useState(null);
  const session = useMissionSession();
  const [science, setScience] = useState(() =>
    session.science
      ? { ...session.science, missionKey: JSON.stringify(session.mission) }
      : null,
  );
  const [inspectionKey, setInspectionKey] = useState(null);
  const [hazardError, setHazardError] = useState("");
  const [selectedHazard, setSelectedHazard] = useState(null);
  const [categories, setCategories] = useState([
    "steep_slope",
    "atmospheric_dust",
    "unknown_conditions",
    "extreme_heat",
    "extreme_cold",
    "strong_winds",
    "mobility_risk",
    "radiation_exposure",
  ]);
  const missionKey = JSON.stringify(session.mission);
  useEffect(() => {
    const controller = new AbortController();
    fetchHazardRegions(JSON.parse(missionKey), { signal: controller.signal })
      .then((result) => {
        if (
          !controller.signal.aborted &&
          JSON.stringify(getMissionSession().mission) === missionKey
        ) {
          updateMissionSession({ hazards: result });
          setSelectedHazard(null);
          setHazardError("");
        }
      })
      .catch((error) => {
        if (error.name !== "AbortError") setHazardError(error.message);
      });
    return () => controller.abort();
  }, [missionKey]);
  useEffect(() => {
    engine.current?.setHazards(
      session.hazards?.regions || [],
      categories,
      selectedHazard,
    );
  }, [session.hazards, categories, selectedHazard, status]);
  const scienceAbort = useRef(null);
  useEffect(() => () => scienceAbort.current?.abort(), []);
  useEffect(() => {
    callbacks.current = {
      inspect: (hit) => {
        if (hit?.hazardId) {
          setSelectedHazard(hit.hazardId);
          return;
        }
        planning.inspect(hit);
        onInspect?.(hit);
        if (!hit || !Number.isFinite(hit.x) || !Number.isFinite(hit.z)) return;
        scienceAbort.current?.abort();
        setScience({ loading: true, position: hit, variables: {} });
        setInspectionKey(
          JSON.stringify({
            x: hit.x,
            z: hit.z,
            requestId: crypto.randomUUID(),
          }),
        );
      },
      place: (hit) => {
        if (planning.mode === "inspect") {
          callbacks.current.inspect(hit);
          return;
        }
        if (hit?.hazardId) {
          setSelectedHazard(hit.hazardId);
          return;
        }
        planning.place(hit);
        onPlaceMarker?.(hit);
      },
    };
  });
  useEffect(() => {
    if (!inspectionKey) return undefined;
    const controller = new AbortController();
    scienceAbort.current = controller;
    inspectMissionPoint(
      (({ x, z }) => ({ x, z }))(JSON.parse(inspectionKey)),
      JSON.parse(missionKey),
      { signal: controller.signal },
    )
      .then((data) => {
        if (!controller.signal.aborted) {
          setScience({ ...data, loading: false, missionKey });
          updateMissionSession({ science: data });
        }
      })
      .catch((error) => {
        if (error.name !== "AbortError")
          setScience({
            error: error.message,
            position: JSON.parse(inspectionKey),
            variables: {},
            missionKey,
          });
      });
    return () => controller.abort();
  }, [inspectionKey, missionKey]);
  useEffect(() => {
    engine.current?.setAnnotations(
      planning.points,
      planning.route.vertices,
      planning.inspection,
      planning.selectedId,
    );
  }, [
    planning.points,
    planning.route.vertices,
    planning.inspection,
    planning.selectedId,
    status,
  ]);
  useImperativeHandle(
    ref,
    () => ({
      focusPosition: (position) => engine.current?.focus(position),
      resetView: () => engine.current?.reset(),
    }),
    [],
  );
  function start() {
    setStatus("loading");
    setProgress(null);
    setError("");
    setStats(null);
    setQuality("medium");
    setAttempt((a) => a + 1);
  }
  useEffect(() => {
    const change = () =>
      setFullscreen(document.fullscreenElement === container.current);
    document.addEventListener("fullscreenchange", change);
    return () => document.removeEventListener("fullscreenchange", change);
  }, []);
  async function toggleFullscreen() {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await container.current.requestFullscreen();
    } catch {
      setExpanded((value) => !value);
      setNotice("Expanded view enabled.");
    }
  }
  // Initialize the terrain engine with scientific inspection support
  useEffect(() => {
    if (!attempt) return undefined;
    let active = true,
      current = null,
      lastProgress = 0;
    import("../../terrain/createTerrainEngine.js")
      .then(({ createTerrainEngine }) => {
        if (!active) return;
        current = createTerrainEngine(host.current, {
          baseUrl: BASE_URL,
          onProgress: (value) => {
            if (
              active &&
              (performance.now() - lastProgress > 100 ||
                value.complete === value.count)
            ) {
              lastProgress = performance.now();
              setProgress(value);
            }
          },
          onReady: () => {
            if (active) setStatus("ready");
          },
          onError: (message) => {
            if (active) {
              setError(message);
              setStatus("error");
            }
          },
          onStats: (value) => {
            if (active) setStats(value);
          },
          onGeometry: (value) => {
            if (active) setGrid(value);
          },
          onInspect: (hit) => callbacks.current?.inspect(hit),
          onPlace: (hit) => callbacks.current?.place(hit),
        });
        engine.current = current;
      })
      .catch((err) => {
        if (active) {
          setError(`3D graphics could not start: ${err.message}`);
          setStatus("error");
        }
      });
    return () => {
      active = false;
      current?.dispose();
      engine.current = null;
    };
  }, [attempt]);

  const active = status !== "idle" && Boolean(attempt);
  const percent = progress
    ? Math.min(100, Math.floor((progress.bytes / progress.total) * 100))
    : null;

  return (
    <div
      ref={container}
      className={`terrain-viewer${expanded ? " terrain-viewer--expanded" : ""}`}
    >
      <div
        className="terrain-toolbar"
        role="toolbar"
        aria-label="3D camera controls"
      >
        <button
          type="button"
          disabled={!active}
          onClick={() => engine.current?.reset()}
        >
          Reset View
        </button>
        <button
          type="button"
          disabled={!active}
          onClick={() => engine.current?.top()}
        >
          Top View
        </button>
        <button
          type="button"
          disabled={!active}
          onClick={() => engine.current?.perspective()}
        >
          Perspective View
        </button>
        <label>
          Quality{" "}
          <select
            disabled={status !== "ready"}
            aria-label="Graphics quality"
            value={quality}
            onChange={(e) => {
              setQuality(e.target.value);
              engine.current?.setQuality(e.target.value);
            }}
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </label>
        <button type="button" onClick={toggleFullscreen}>
          {fullscreen
            ? "Exit Fullscreen"
            : expanded
              ? "Exit Expanded View"
              : "Fullscreen"}
        </button>
      </div>
      <div className="terrain-stage">
        <div className="terrain-canvas" ref={host} />
        <div
          className="terrain-orientation"
          title="Local model axes; not geographic north"
        >
          <span aria-hidden="true">↑</span>Local −Z
        </div>
        {status === "idle" && (
          <div className="terrain-overlay">
            <h3>Explore the surface</h3>
            <p>Navigate the original voxel terrain in 3D.</p>
            <button type="button" onClick={start}>
              Load 3D terrain
            </button>
            <small>Approximately 52 MiB · loads progressively</small>
          </div>
        )}
        {status === "loading" && (
          <div className="terrain-loading" role="status">
            <span>
              {percent === null
                ? "Preparing terrain…"
                : percent < 100
                  ? `Downloading terrain · ${percent}%`
                  : "Preparing final sectors…"}
            </span>
            <progress
              aria-label="Terrain download"
              max="100"
              {...(percent === null ? {} : { value: percent })}
            />
            {progress && (
              <small>
                {progress.complete} / {progress.count} sectors ready · partial
                terrain
              </small>
            )}
          </div>
        )}
        {status === "error" && (
          <div className="terrain-overlay" role="alert">
            <h3>Terrain unavailable</h3>
            <p>{error}</p>
            <p>Any visible sectors are incomplete.</p>
            <button type="button" onClick={start}>
              Retry terrain
            </button>
          </div>
        )}
        {active && (
          <div
            className="terrain-camera-buttons"
            role="group"
            aria-label="Accessible terrain navigation"
          >
            <button
              aria-label="Zoom in terrain"
              onClick={() => engine.current?.zoom(0.8)}
            >
              +
            </button>
            <button
              aria-label="Zoom out terrain"
              onClick={() => engine.current?.zoom(1.25)}
            >
              −
            </button>
            <button
              aria-label="Pan left"
              onClick={() => engine.current?.pan(60, 0)}
            >
              ←
            </button>
            <button
              aria-label="Pan right"
              onClick={() => engine.current?.pan(-60, 0)}
            >
              →
            </button>
            <button
              aria-label="Pan forward"
              onClick={() => engine.current?.pan(0, -60)}
            >
              ↑
            </button>
            <button
              aria-label="Pan backward"
              onClick={() => engine.current?.pan(0, 60)}
            >
              ↓
            </button>
            <button
              aria-label="Rotate left"
              onClick={() => engine.current?.orbit(-0.2, 0)}
            >
              ↶
            </button>
            <button
              aria-label="Rotate right"
              onClick={() => engine.current?.orbit(0.2, 0)}
            >
              ↷
            </button>
            <button
              aria-label="Tilt up"
              onClick={() => engine.current?.orbit(0, -0.1)}
            >
              Tilt +
            </button>
            <button
              aria-label="Tilt down"
              onClick={() => engine.current?.orbit(0, 0.1)}
            >
              Tilt −
            </button>
          </div>
        )}
      </div>

      {science && (
        <ScientificInspectionPanel
          data={science}
          outdated={science.missionKey !== missionKey}
          onUsePoint={planning.useInspected}
          onClose={() => {
            scienceAbort.current?.abort();
            setScience(null);
            setInspectionKey(null);
          }}
        />
      )}
      <TerrainPlanningControls
        planning={planning}
        enabled={status === "ready"}
        focus={(position) => engine.current?.focus(position)}
      />
      <MissionPlanningPanel
        grid={grid}
        planning={planning}
        enabled={status === "ready"}
      />
      <section className="hazard-controls" aria-label="Hazard indicators">
        <h3>Hazard indicators</h3>
        <p>
          Scientific gradients and historical conditions. Unknown is not safe.
          Icon positions mark connected regions, not isolated point hazards.
        </p>
        {hazardError && <p role="alert">{hazardError}</p>}
        <div className="terrain-planning-actions">
          {[
            "steep_slope",
            "atmospheric_dust",
            "unknown_conditions",
            "extreme_heat",
            "extreme_cold",
            "strong_winds",
            "mobility_risk",
            "radiation_exposure",
          ].map((category) => (
            <label key={category}>
              <input
                type="checkbox"
                checked={categories.includes(category)}
                onChange={(e) =>
                  setCategories((previous) =>
                    e.target.checked
                      ? [...previous, category]
                      : previous.filter((c) => c !== category),
                  )
                }
              />
              {category.replaceAll("_", " ")}
              {session.hazards?.category_availability?.[category] ===
              "Unavailable"
                ? " (Unavailable)"
                : ""}
            </label>
          ))}
        </div>
        <label>
          Connected regions ({session.hazards?.regions?.length || 0})
          <select
            aria-label="Hazard region"
            value={selectedHazard || ""}
            onChange={(e) => {
              setSelectedHazard(e.target.value);
              const r = session.hazards?.regions.find(
                (r) => r.id === e.target.value,
              );
              if (r) engine.current?.focus([r.x, r.y, r.z]);
            }}
          >
            <option value="">Select a region</option>
            {session.hazards?.regions
              ?.filter((r) => categories.includes(r.category))
              .map((r) => (
                <option key={r.id} value={r.id}>
                  {r.label} · {r.severity} · {r.cell_count} cells · {r.id}
                </option>
              ))}
          </select>
        </label>
        {selectedHazard &&
          session.hazards?.regions
            ?.filter((r) => r.id === selectedHazard)
            .map((r) => (
              <div key={r.id} role="status">
                <strong>
                  {r.label} · {r.severity}
                </strong>
                <p>{r.cause}</p>
                <p>
                  {(r.max_value ?? r.value)?.toFixed(2)} {r.unit} · threshold{" "}
                  {r.threshold} · {r.cell_count} affected cells
                </p>
                <p>
                  {r.scope ||
                    "Connected scientific cells; boundary samples shown on terrain."}{" "}
                  {r.limitations}
                </p>
                <button
                  disabled={r.category !== "steep_slope"}
                  onClick={() =>
                    updateMissionSession(
                      {
                        excluded: [
                          ...session.excluded,
                          ...(r.bounds && r.category === "steep_slope"
                            ? Array.from(
                                { length: r.bounds[2] - r.bounds[0] + 1 },
                                (_, i) =>
                                  Array.from(
                                    { length: r.bounds[3] - r.bounds[1] + 1 },
                                    (_, j) => [
                                      i + r.bounds[0],
                                      j + r.bounds[1],
                                    ],
                                  ),
                              ).flat()
                            : []),
                        ],
                      },
                      true,
                    )
                  }
                >
                  Exclude region bounding cells
                </button>
              </div>
            ))}
        <p>{session.hazards?.notice}</p>
      </section>
      <div className="terrain-caption">
        <p>
          Left drag: pan · Right drag: orbit · Wheel: zoom
          <br />
          Touch: drag to pan · Pinch to zoom · Twist to rotate · Two-finger
          vertical drag to tilt
        </p>
        <p>
          Local grid axes. Geographic coordinates and scientific metres are
          reported by the science service. Visual relief remains exaggerated 3×.
        </p>
        {status === "ready" && (
          <span role="status">Terrain ready · 44 sectors</span>
        )}
        {notice && <p role="status">{notice}</p>}
      </div>
      {stats && (
        <details className="terrain-diagnostics">
          <summary>Rendering diagnostics</summary>
          <output>{JSON.stringify(stats)}</output>
        </details>
      )}
    </div>
  );
});
export default MarsTerrainViewer;
