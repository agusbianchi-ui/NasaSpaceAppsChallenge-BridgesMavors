import { useEffect, useRef, useState } from "react";
import {
  useMissionSession,
  getMissionSession,
  updateMissionSession,
  missionFingerprint,
  exportMission,
  validateMissionImport,
} from "../../services/missionSession.js";
import {
  startPlanning,
  fetchPlanningJob,
  cancelPlanningJob,
} from "../../services/marsApi.js";

export default function MissionPlanningPanel({ grid, planning, enabled }) {
  const session = useMissionSession(),
    [status, setStatus] = useState("idle"),
    [error, setError] = useState(""),
    [compare, setCompare] = useState(true);
  const running = useRef(null),
    file = useRef(null);
  function cancel() {
    const current = running.current;
    if (current) {
      current.abort.abort();
      if (current.job) cancelPlanningJob(current.job).catch(() => {});
      running.current = null;
    }
    setStatus("cancelled");
  }
  useEffect(
    () => () => {
      const c = running.current;
      if (c) {
        c.abort.abort();
        if (c.job) cancelPlanningJob(c.job).catch(() => {});
      }
    },
    [],
  );
  const fingerprint = missionFingerprint(session);
  useEffect(() => {
    const current = running.current;
    if (current && current.fingerprint !== fingerprint) {
      current.abort.abort();
      if (current.job) cancelPlanningJob(current.job).catch(() => {});
      running.current = null;
    }
  }, [fingerprint]);
  function change(key, value) {
    const defaults =
      key === "displacement"
        ? value === "rover"
          ? { velocity: 2, max_slope: 15, max_descent_slope: 15 }
          : { velocity: 1, max_slope: 25, max_descent_slope: 25 }
        : {};
    updateMissionSession(
      { mission: { ...session.mission, ...defaults, [key]: value } },
      true,
    );
  }
  async function calculate() {
    if (
      !session.points.some((p) => p.type === "Start") ||
      !session.points.some((p) => p.type === "Destination")
    ) {
      setError("Select a Start and Destination.");
      return;
    }
    cancel();
    const current = { abort: new AbortController(), fingerprint, job: null };
    running.current = current;
    setStatus("calculating");
    setError("");
    try {
      const started = await startPlanning(
        {
          points: session.points.map(({ x, z }) => ({ x, z })),
          mission: session.mission,
          strategy: session.strategy,
          excluded_cells: session.excluded,
          compare,
        },
        { signal: current.abort.signal },
      );
      current.job = started.id;
      for (;;) {
        current.abort.signal.throwIfAborted();
        const job = await fetchPlanningJob(started.id, {
          signal: current.abort.signal,
        });
        if (job.status === "complete") {
          if (
            running.current === current &&
            missionFingerprint(getMissionSession()) === current.fingerprint
          ) {
            const active =
              job.result.routes.find(
                (r) => r.success && r.strategy === session.strategy,
              ) || job.result.routes.find((r) => r.success);
            updateMissionSession({
              results: job.result,
              activeStrategy: active?.strategy || session.strategy,
              stale: false,
            });
            setStatus("complete");
            if (!job.result.success)
              setError(
                job.result.error ||
                  "No valid route found. Review constraints and unknown-data policy.",
              );
          }
          break;
        }
        if (job.status === "error" || job.status === "cancelled")
          throw new Error(job.error || "Calculation cancelled.");
        await new Promise((resolve, reject) => {
          const onAbort = () => {
            clearTimeout(timer);
            reject(new DOMException("Cancelled", "AbortError"));
          };
          const timer = setTimeout(() => {
            current.abort.signal.removeEventListener("abort", onAbort);
            resolve();
          }, 300);
          current.abort.signal.addEventListener("abort", onAbort, {
            once: true,
          });
        });
      }
    } catch (e) {
      if (e.name !== "AbortError") {
        setError(e.message);
        setStatus("error");
      } else setStatus("cancelled");
    } finally {
      if (running.current === current) running.current = null;
    }
  }
  function download() {
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(exportMission(session), null, 2)], {
        type: "application/json",
      }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "bridges-mission.json";
    a.click();
    URL.revokeObjectURL(url);
  }
  async function importFile(event) {
    try {
      const selected = event.target.files[0];
      if (!selected) return;
      if (selected.size > 5e6) throw new Error("Mission file exceeds 5 MB.");
      const next = validateMissionImport(
        JSON.parse(await selected.text()),
        grid,
      );
      cancel();
      updateMissionSession(next);
      setError(
        "Imported points and assumptions. Recalculate to verify costs and statistics.",
      );
    } catch (e) {
      setError(e.message);
    }
    event.target.value = "";
  }
  const chosen = session.results?.routes?.find(
    (r) => r.strategy === session.activeStrategy && r.success,
  );
  const numeric = (key, label, min, max, step = 1) => (
    <label>
      {label}
      <input
        aria-label={label}
        type="number"
        min={min}
        max={max}
        step={step}
        value={session.mission[key]}
        onChange={(event) => {
          const value = Number(event.target.value);
          if (Number.isFinite(value) && value >= min && value <= max)
            change(key, value);
        }}
      />
    </label>
  );
  return (
    <section
      className="mission-planning"
      aria-label="Mission conditions and automatic routes"
    >
      <h3>Mission conditions</h3>
      <p>
        User assumptions for hypothetical expeditions. Limits are not NASA
        safety limits. Travel mode applies editable speed/slope defaults, not a
        soil stability model.
      </p>
      <div className="mission-fields">
        <label>
          Travel mode
          <select
            aria-label="Travel mode"
            value={session.mission.displacement}
            onChange={(e) => change("displacement", e.target.value)}
          >
            <option value="foot">Walking</option>
            <option value="rover">Rover</option>
          </select>
        </label>
        {numeric("velocity", "Estimated speed (m/s)", 0.1, 10, 0.1)}
        {numeric("max_slope", "Maximum ascent / terrain slope (°)", 0, 60)}
        {numeric("max_descent_slope", "Maximum descent (°)", 0, 60)}
        {numeric("thermal_min", "Thermal minimum (°C)", -150, 100)}
        {numeric("thermal_max", "Thermal maximum (°C)", -150, 150)}
        <label>
          Climate scenario
          <select disabled value="unavailable" onChange={() => {}}>
            <option value="unavailable">Unavailable — MCD not installed</option>
          </select>
        </label>
        <label>
          Solar longitude Ls
          <input disabled placeholder="Unavailable without climate model" />
        </label>
        <label>
          Local solar time
          <input disabled placeholder="Unavailable; dust is a daily mean" />
        </label>
        <label>
          Dust scenario
          <select
            aria-label="Dust scenario"
            value={session.mission.dust_scenario}
            onChange={(e) => change("dust_scenario", e.target.value)}
          >
            <option value="none">Not evaluated</option>
            <option value="my36">Historical MY36 daily CDOD</option>
          </select>
        </label>
        {session.mission.dust_scenario === "my36" &&
          numeric("sol", "MY36 sol of year", 1, 669)}
        {numeric("high_dust", "Dust warning threshold (Pa/Pa)", 0.01, 10, 0.01)}
        <label>
          Unknown-data policy
          <select
            aria-label="Unknown-data policy"
            value={session.mission.unknown_policy}
            onChange={(e) => change("unknown_policy", e.target.value)}
          >
            <option value="topography_only">Topography-only planning</option>
            <option value="penalize">Allow unknown with penalty</option>
            <option value="avoid">Avoid unknown areas</option>
          </select>
        </label>
      </div>
      <details>
        <summary>Planning priorities and method</summary>
        <div className="mission-fields">
          {numeric("slope_weight", "Slope weight", 0, 20, 0.1)}
          {numeric("roughness_weight", "Roughness weight", 0, 20, 0.1)}
          {numeric("environment_weight", "Environment weight", 0, 20, 0.1)}
          {numeric("unknown_weight", "Unknown-data weight", 0, 20, 0.1)}
          {numeric(
            "roughness_scale",
            "Roughness normalization (m RMS)",
            1,
            1000,
          )}
        </div>
        <p>
          Cost = horizontal distance × (1 + weighted normalized penalties).
          Shortest uses distance alone with hard restrictions. Unknown avoidance
          can block the entire region. One native dust cell covers the terrain;
          temperature, wind, soil mechanics and ionizing radiation remain
          unknown. No time-varying exposure optimization.
        </p>
      </details>
      <div className="terrain-planning-actions">
        <label>
          Strategy
          <select
            aria-label="Planning strategy"
            value={session.strategy}
            onChange={(e) =>
              updateMissionSession({ strategy: e.target.value }, true)
            }
          >
            <option value="shortest">Shortest route</option>
            <option value="low_slope">Low-slope route</option>
            <option
              value="environmental"
              disabled={
                session.mission.dust_scenario !== "my36" ||
                session.mission.unknown_policy === "topography_only"
              }
            >
              Environmental risk route (partial)
            </option>
            <option value="balanced">Balanced route</option>
          </select>
        </label>
        <label>
          <input
            type="checkbox"
            checked={compare}
            onChange={(e) => setCompare(e.target.checked)}
          />
          Compare all strategies
        </label>
        <button
          disabled={session.points.length < 3}
          onClick={() =>
            updateMissionSession(
              {
                history: [...session.history, session.points].slice(-50),
                points: session.points.filter(
                  (p) => p.type === "Start" || p.type === "Destination",
                ),
              },
              true,
            )
          }
        >
          Use endpoints only
        </button>
        <button
          disabled={!enabled || status === "calculating"}
          onClick={calculate}
        >
          Calculate routes
        </button>
        <button disabled={status !== "calculating"} onClick={cancel}>
          Cancel calculation
        </button>
        <button disabled={!session.points.length} onClick={download}>
          Export mission
        </button>
        <button disabled={!grid} onClick={() => file.current.click()}>
          Import mission
        </button>
        <input
          ref={file}
          type="file"
          accept=".json,application/json"
          hidden
          onChange={importFile}
        />
        <button
          disabled={!planning.inspection}
          onClick={() => {
            const p = planning.inspection,
              cell = grid.modelToGrid(p.x, p.z);
            if (cell)
              updateMissionSession(
                { excluded: [...session.excluded, [cell.row, cell.column]] },
                true,
              );
          }}
        >
          Exclude inspected cell
        </button>
        <button
          disabled={!session.excluded.length}
          onClick={() => updateMissionSession({ excluded: [] }, true)}
        >
          Clear exclusions ({session.excluded.length})
        </button>
      </div>
      <p role="status">
        {status === "calculating"
          ? "Calculating on the server…"
          : status === "cancelled"
            ? "Calculation cancelled or conditions changed."
            : status === "complete"
              ? "Calculation complete."
              : ""}
      </p>
      {error && <p role="alert">{error}</p>}
      {session.stale && (
        <p role="alert">
          Route outdated: mission conditions or points changed. Recalculate.
        </p>
      )}
      {session.results?.snapping?.some((p) => p.changed) && (
        <details>
          <summary>Points adjusted to 250 m cell centers</summary>
          <pre>
            {JSON.stringify(
              session.results.snapping.filter((p) => p.changed),
              null,
              2,
            )}
          </pre>
        </details>
      )}
      {session.results && (
        <>
          <h3>Route comparison</h3>
          <div className="route-table">
            <table>
              <thead>
                <tr>
                  <th>Strategy</th>
                  <th>Distance</th>
                  <th>Duration</th>
                  <th>Max / mean slope</th>
                  <th>Gain / loss</th>
                  <th>Unknown environment</th>
                  <th>Cost</th>
                </tr>
              </thead>
              <tbody>
                {session.results.routes.map((r) => (
                  <tr key={r.strategy}>
                    <td>
                      <button
                        disabled={!r.success}
                        aria-pressed={session.activeStrategy === r.strategy}
                        onClick={() =>
                          updateMissionSession({ activeStrategy: r.strategy })
                        }
                      >
                        {r.strategy}
                      </button>
                    </td>
                    {r.success ? (
                      <>
                        <td>
                          {(r.analysis.horizontal_distance_m / 1000).toFixed(2)}{" "}
                          km
                        </td>
                        <td>
                          {(r.analysis.estimated_duration_s / 3600).toFixed(2)}{" "}
                          h
                        </td>
                        <td>
                          {r.analysis.max_slope_deg.toFixed(2)}° /{" "}
                          {r.analysis.mean_slope_deg.toFixed(2)}°
                        </td>
                        <td>
                          {r.analysis.elevation_gain_m.toFixed(1)} /{" "}
                          {r.analysis.elevation_loss_m.toFixed(1)} m
                        </td>
                        <td>
                          {(
                            r.analysis.unknown_environment_fraction * 100
                          ).toFixed(0)}
                          %
                        </td>
                        <td>{r.total_cost.toFixed(1)}</td>
                      </>
                    ) : (
                      <td colSpan="6">{r.error}</td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p>{session.results.notice}</p>
        </>
      )}
      {chosen && (
        <>
          <p>
            {chosen.explanation} Used:{" "}
            {chosen.analysis.used_variables.join(", ")}. Mobility / temperature
            / solar / ionizing exposure: Unavailable.
          </p>
          <ElevationProfile profile={chosen.analysis.profile} />
          <details>
            <summary>Scientific statistics and scenario</summary>
            <pre>
              {JSON.stringify(
                { ...chosen.analysis, profile: undefined },
                null,
                2,
              )}
            </pre>
          </details>
        </>
      )}
    </section>
  );
}
function ElevationProfile({ profile }) {
  const values = profile.map((p) => p.elevation_m),
    low = Math.min(...values),
    high = Math.max(...values),
    distance = profile.at(-1)?.distance_m || 1;
  const coordinates = profile
    .map(
      (p) =>
        `${(p.distance_m / distance) * 600},${140 - ((p.elevation_m - low) / Math.max(1, high - low)) * 120}`,
    )
    .join(" ");
  return (
    <figure className="route-profile">
      <figcaption>
        Scientific elevation profile · {low.toFixed(1)} to {high.toFixed(1)} m ·{" "}
        {(distance / 1000).toFixed(2)} km
      </figcaption>
      <svg
        viewBox="0 0 600 160"
        role="img"
        aria-label="Scientific elevation along the calculated route"
      >
        <polyline
          points={coordinates}
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        />
      </svg>
    </figure>
  );
}
