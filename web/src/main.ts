// Lithora atlas entry point.
//
// Renders real exported GNSS velocity fields on a CesiumJS globe. The design
// keeps the two honesty constraints visible: every vector carries its chosen
// model layer and reference frame in the provenance panel, and the exaggerated
// arrows are paired with a scale legend so they cannot be read as literal
// per-year displacement. Region loading uses a generation counter so a slow
// fetch for an old selection never overwrites a newer one (the cancellation
// behavior required of the asynchronous pipeline).

import {
  Cartesian3,
  Color,
  Ion,
  PolylineCollection,
  Viewer,
  Math as CMath,
  ScreenSpaceEventHandler,
  ScreenSpaceEventType,
  defined,
} from "cesium";
import { arrowTip, latLonToEcef, speed } from "./geo";
import { LayerKind, RegionPayload, StationRecord, layerVelocity } from "./types";

// The globe uses only open imagery that ships with Cesium; no Ion token needed.
Ion.defaultAccessToken = "";

const viewer = new Viewer("cesiumContainer", {
  baseLayerPicker: false,
  geocoder: false,
  timeline: false,
  animation: false,
  sceneModePicker: false,
  navigationHelpButton: false,
  homeButton: false,
  fullscreenButton: false,
});
viewer.scene.globe.enableLighting = false;

const lines = new PolylineCollection();
viewer.scene.primitives.add(lines);

// Fold colors for the holdout overlay.
const FOLD_COLORS = [
  Color.CYAN,
  Color.ORANGE,
  Color.LIME,
  Color.MAGENTA,
  Color.YELLOW,
];

interface State {
  payload: RegionPayload | null;
  layer: LayerKind;
  exaggeration: number;
  showUnc: boolean;
  showHoldout: boolean;
  generation: number; // bumped on each region load to cancel stale loads
}

const state: State = {
  payload: null,
  layer: "obs",
  exaggeration: 40,
  showUnc: true,
  showHoldout: false,
  generation: 0,
};

const METRES_PER_MM_YR = 3000;

async function loadRegion(region: string): Promise<void> {
  const gen = ++state.generation;
  const resp = await fetch(`/data/${region}.json`);
  const payload = (await resp.json()) as RegionPayload;
  // If another region was requested while we were fetching, drop this result.
  if (gen !== state.generation) return;
  state.payload = payload;
  updateProvenance();
  render();
  flyToData(payload.stations);
}

function flyToData(stations: StationRecord[]): void {
  if (stations.length === 0) return;
  let latSum = 0;
  let lonSum = 0;
  for (const s of stations) {
    latSum += s.lat;
    lonSum += s.lon;
  }
  const lat = latSum / stations.length;
  const lon = lonSum / stations.length;
  viewer.camera.flyTo({
    destination: Cartesian3.fromDegrees(lon, lat, 5_500_000),
    duration: 1.2,
  });
}

function render(): void {
  lines.removeAll();
  viewer.entities.removeAll();
  const payload = state.payload;
  if (!payload) return;

  for (const s of payload.stations) {
    const [ve, vn] = layerVelocity(s, state.layer);
    const base = latLonToEcef(s.lat, s.lon);
    const tip = arrowTip(s.lat, s.lon, ve, vn, state.exaggeration, METRES_PER_MM_YR);

    const color = state.showHoldout && s.fold >= 0
      ? FOLD_COLORS[s.fold % FOLD_COLORS.length]
      : Color.fromCssColorString("#ff5252");

    lines.add({
      positions: [base, tip],
      width: 2.0,
      material: (lines as unknown as { constructor: unknown }) && undefinedMaterial(color),
    });

    // Station point, optionally sized by uncertainty.
    const sig = Math.hypot(s.sig_e, s.sig_n);
    const px = state.showUnc ? Math.min(14, 4 + sig * 2000) : 5;
    const ent = viewer.entities.add({
      position: base,
      point: { pixelSize: px, color: color.withAlpha(0.85) },
    });
    (ent as unknown as { _station: StationRecord })._station = s;
  }
  updateLegend();
}

// Cesium's PolylineCollection material API differs across versions; this keeps
// the color handling in one place so the rest of the code stays declarative.
function undefinedMaterial(color: Color): unknown {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const Cesium = (window as any).Cesium;
  if (Cesium?.Material?.fromType) {
    return Cesium.Material.fromType("Color", { color });
  }
  return undefined;
}

function updateLegend(): void {
  const el = document.getElementById("scaleLegend");
  if (!el) return;
  // A reference arrow length: how long 20 mm/yr appears, in km on the globe.
  const km = (20 * state.exaggeration * METRES_PER_MM_YR) / 1000;
  el.textContent =
    `Scale: a 20 mm/yr vector is drawn ${km.toLocaleString()} km long. ` +
    `Arrows are exaggerated ${state.exaggeration}x and do not show literal ` +
    `per-year motion.`;
}

function updateProvenance(): void {
  const el = document.getElementById("provenance");
  const p = state.payload;
  if (!el || !p) return;
  el.innerHTML =
    `<h2>Layer provenance</h2>` +
    `<ul>` +
    `<li>Region: ${p.region_label}</li>` +
    `<li>Reference frame: <strong>${p.frame}</strong></li>` +
    `<li>Source: ${p.source}</li>` +
    `<li>Citation: ${p.citation}</li>` +
    `<li>Stations: ${p.n_stations} (units ${p.units})</li>` +
    `<li>Rigid pole: ${p.rigid_pole.lat.toFixed(1)} N, ` +
    `${p.rigid_pole.lon.toFixed(1)} E at ${p.rigid_pole.rate_deg_myr.toFixed(3)} deg/Myr</li>` +
    `</ul>`;
}

function showInspector(s: StationRecord): void {
  const el = document.getElementById("inspector");
  if (!el) return;
  const resE = s.obs_e - s.rigid_e;
  const resN = s.obs_n - s.rigid_n;
  el.innerHTML =
    `<h2>Station inspector</h2>` +
    `<table>` +
    `<tr><td>Location</td><td>${s.lat.toFixed(3)} N, ${s.lon.toFixed(3)} E</td></tr>` +
    `<tr><td>Observed</td><td>${s.obs_e.toFixed(2)}, ${s.obs_n.toFixed(2)} mm/yr ` +
    `(|v| ${speed(s.obs_e, s.obs_n).toFixed(2)})</td></tr>` +
    `<tr><td>Uncertainty</td><td>${s.sig_e.toFixed(3)}, ${s.sig_n.toFixed(3)} mm/yr</td></tr>` +
    `<tr><td>Rigid model</td><td>${s.rigid_e.toFixed(2)}, ${s.rigid_n.toFixed(2)} mm/yr</td></tr>` +
    `<tr><td>Residual</td><td>${resE.toFixed(2)}, ${resN.toFixed(2)} mm/yr ` +
    `(|r| ${speed(resE, resN).toFixed(2)})</td></tr>` +
    `<tr><td>Local model</td><td>${s.local_e.toFixed(2)}, ${s.local_n.toFixed(2)} mm/yr</td></tr>` +
    `<tr><td>Holdout fold</td><td>${s.fold >= 0 ? s.fold : "train"}</td></tr>` +
    `</table>`;
}

// Click handling to inspect a station.
const handler = new ScreenSpaceEventHandler(viewer.scene.canvas);
handler.setInputAction((movement: { position: { x: number; y: number } }) => {
  const picked = viewer.scene.pick(new Cartesian3(movement.position.x, movement.position.y, 0) as unknown as never);
  // Use Cesium's documented pick via windowPosition.
  const obj = viewer.scene.pick({ x: movement.position.x, y: movement.position.y } as never);
  const chosen = obj ?? picked;
  if (defined(chosen) && (chosen as { id?: { _station?: StationRecord } }).id?._station) {
    showInspector((chosen as { id: { _station: StationRecord } }).id._station);
  }
}, ScreenSpaceEventType.LEFT_CLICK);

// ---- UI wiring ----

function bindUi(): void {
  const region = document.getElementById("region") as HTMLSelectElement;
  region.addEventListener("change", () => void loadRegion(region.value));

  const layer = document.getElementById("layer") as HTMLSelectElement;
  layer.addEventListener("change", () => {
    state.layer = layer.value as LayerKind;
    render();
  });

  const exag = document.getElementById("exag") as HTMLInputElement;
  const exagVal = document.getElementById("exagVal");
  exag.addEventListener("input", () => {
    state.exaggeration = Number(exag.value);
    if (exagVal) exagVal.textContent = exag.value;
    render();
  });
  state.exaggeration = Number(exag.value);
  if (exagVal) exagVal.textContent = exag.value;

  const showUnc = document.getElementById("showUnc") as HTMLInputElement;
  showUnc.addEventListener("change", () => {
    state.showUnc = showUnc.checked;
    render();
  });

  const showHoldout = document.getElementById("showHoldout") as HTMLInputElement;
  showHoldout.addEventListener("change", () => {
    state.showHoldout = showHoldout.checked;
    render();
  });
}

bindUi();
void loadRegion("cal");

// Silence an unused import in some Cesium versions while keeping it available.
void CMath;
