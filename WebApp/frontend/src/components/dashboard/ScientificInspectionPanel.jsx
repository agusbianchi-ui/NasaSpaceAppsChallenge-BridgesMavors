import Panel from "../Panel.jsx";
const GROUPS = {
  Topography: [
    "scientific_elevation",
    "slope",
    "aspect",
    "roughness",
    "local_relief",
  ],
  Thermal: [
    "surface_temperature",
    "atmospheric_temperature",
    "thermal_inertia_day",
    "thermal_inertia_night",
  ],
  Atmosphere: [
    "atmospheric_dust",
    "dust_optical_depth",
    "wind_speed",
    "wind_direction",
    "pressure",
  ],
  Surface: ["surface_dust", "rock_abundance", "geology", "mineralogy"],
  Radiation: ["solar_flux", "solar_exposure", "ionizing_radiation"],
};
export default function ScientificInspectionPanel({
  data,
  onClose,
  onUsePoint,
  outdated,
}) {
  const position = data.position || {},
    available = Object.values(data.variables || {}).filter(
      (v) => v.value !== null,
    ).length;
  return (
    <div className="scientific-inspection">
      <Panel
        title="Scientific Inspection"
        eyebrow="Source-referenced terrain query"
      >
        <div className="terrain-planning-actions">
          <button onClick={onClose}>Close inspection</button>
          {["Start", "Destination", "Waypoint"].map((type) => (
            <button
              key={type}
              disabled={data.loading || Boolean(data.error) || outdated}
              onClick={() => onUsePoint(type)}
            >
              Use as {type}
            </button>
          ))}
        </div>
        {(data.loading || outdated) && (
          <p role="status">Updating this point for the selected mission…</p>
        )}
        {data.error && <p role="alert">{data.error}</p>}
        <p>
          Local X: {position.x?.toFixed(2)} · Z: {position.z?.toFixed(2)} ·
          Visual Y: {position.visual_elevation?.toFixed(2)}
        </p>
        {position.geographic && (
          <p>
            Planetocentric latitude: {position.geographic.latitude.toFixed(5)}°
            · East longitude: {position.geographic.longitude.toFixed(5)}°
          </p>
        )}
        <p>
          {data.notice} {available} variables available.
        </p>
        {data.warnings?.map((w) => (
          <p key={w.category} className="science-warning">
            {w.label} · {w.severity}: {w.cause}
          </p>
        ))}
        <p>
          Estimated mobility difficulty:{" "}
          {data.mobility_difficulty?.reason || "Unknown mobility conditions."}
        </p>
        {!outdated &&
          Object.entries(GROUPS).map(([group, keys]) => (
            <details key={group} open={group === "Topography"}>
              <summary>{group}</summary>
              <dl>
                {keys.map((id) => {
                  const value = data.variables?.[id];
                  if (!value) return null;
                  return (
                    <div key={id}>
                      <dt>
                        {value.name} · {value.classification}
                      </dt>
                      <dd>
                        {value.value === null
                          ? value.reason || "Unavailable"
                          : `${value.value.toFixed(3)} ${value.unit || ""}`}
                      </dd>
                      <dd>
                        <details>
                          <summary>Source, resolution and limitations</summary>
                          <p>
                            {value.product} ·{" "}
                            {value.source && (
                              <a
                                href={value.source}
                                target="_blank"
                                rel="noreferrer"
                              >
                                Source
                              </a>
                            )}
                          </p>
                          <pre>
                            {JSON.stringify(
                              {
                                unit: value.unit,
                                spatial_resolution: value.spatial_resolution,
                                temporal_resolution: value.temporal_resolution,
                                date_or_scenario: value.date_or_scenario,
                                classification: value.classification,
                                availability: value.availability,
                                method: value.method,
                                uncertainty: value.uncertainty,
                                sample: value.sample,
                                limitations:
                                  value.reason ||
                                  "Source resolution and datum limits apply; no certified safety assessment.",
                              },
                              null,
                              2,
                            )}
                          </pre>
                        </details>
                      </dd>
                    </div>
                  );
                })}
              </dl>
            </details>
          ))}
      </Panel>
    </div>
  );
}
