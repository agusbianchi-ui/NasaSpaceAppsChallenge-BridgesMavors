export default function TerrainPlanningControls({ planning, enabled, focus }) {
  const p = planning,
    selected = p.selected;
  return (
    <section
      className="terrain-planning"
      aria-label="Terrain inspection and manual route"
    >
      <div className="terrain-planning-actions">
        <label>
          Interaction{" "}
          <select
            aria-label="Interaction mode"
            value={p.mode}
            disabled={!enabled}
            onChange={(e) => p.setMode(e.target.value)}
          >
            <option value="navigation">Navigation mode</option>
            <option value="inspect">Inspect mode</option>
            <option value="planning">Route planning mode</option>
          </select>
        </label>
        {p.mode === "planning" && (
          <label>
            Place{" "}
            <select
              aria-label="Marker type"
              value={p.kind}
              disabled={!enabled}
              onChange={(e) => p.setKind(e.target.value)}
            >
              <option>Start</option>
              <option>Destination</option>
              <option>Waypoint</option>
            </select>
          </label>
        )}
        <button disabled={!enabled || p.importing} onClick={p.importReference}>
          {p.importing ? "Importing…" : "Import preliminary route"}
        </button>
        <button disabled={!p.canUndo} onClick={p.undo}>
          Undo route edit
        </button>
        <button disabled={!p.points.length} onClick={p.clear}>
          Clear route
        </button>
      </div>
      <p>
        Right-click or touch and hold to inspect. Click or tap to place in
        planning mode. Dragging always navigates.
      </p>
      <p>
        Manual lines follow visual blocks. Automatic statistics use the
        registered scientific DEM. No certified traversability assessment.
      </p>
      {p.message && <p role="status">{p.message}</p>}
      {p.route.error && (
        <p className="terrain-route-error" role="alert">
          {p.route.error} Markers are retained; only the valid route prefix is
          drawn.
        </p>
      )}
      <div className="terrain-marker-editor">
        <label>
          Markers ({p.points.length}
          {p.inspection ? " + inspection" : ""})
          <select
            size="4"
            aria-label="Terrain markers"
            value={p.selectedId || ""}
            onChange={(e) => p.select(e.target.value)}
          >
            {!selected && (
              <option value="" disabled>
                Select a marker
              </option>
            )}
            {[...p.points, ...(p.inspection ? [p.inspection] : [])].map(
              (point) => (
                <option key={point.id} value={point.id}>
                  {point.type} · {point.label}
                </option>
              ),
            )}
          </select>
        </label>
        {selected && (
          <form
            key={`${selected.id}:${selected.x}:${selected.z}:${selected.label}`}
            onSubmit={(event) => {
              event.preventDefault();
              const data = new FormData(event.currentTarget);
              p.edit(selected.id, {
                label: String(data.get("label")),
                x: Number(data.get("x")),
                z: Number(data.get("z")),
              });
            }}
          >
            <label>
              Label{" "}
              <input
                name="label"
                maxLength="60"
                defaultValue={selected.label}
                required
              />
            </label>
            <label>
              Local X{" "}
              <input
                name="x"
                type="number"
                step="any"
                defaultValue={selected.x}
                required
              />
            </label>
            <label>
              Local Z{" "}
              <input
                name="z"
                type="number"
                step="any"
                defaultValue={selected.z}
                required
              />
            </label>
            <output>
              Visual Y: {selected.y.toFixed(2)} · {selected.type}
              <br />
              ID: {selected.id}
            </output>
            <div className="terrain-planning-actions">
              <button type="submit" disabled={!enabled}>
                Save marker
              </button>
              <button
                type="button"
                disabled={!enabled}
                onClick={p.moveSelected}
              >
                {p.moving ? "Choose new surface position…" : "Move on terrain"}
              </button>
              <button
                type="button"
                onClick={() => focus([selected.x, selected.y, selected.z])}
              >
                Focus marker
              </button>
              <button type="button" onClick={() => p.remove(selected.id)}>
                Delete marker
              </button>
            </div>
          </form>
        )}
      </div>
    </section>
  );
}
