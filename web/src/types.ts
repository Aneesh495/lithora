// Shared types for the Lithora atlas. These mirror the JSON exported by
// `lithora.export_web`, so a schema change in the exporter shows up here.

export interface StationRecord {
  lat: number;
  lon: number;
  obs_e: number;
  obs_n: number;
  sig_e: number;
  sig_n: number;
  rigid_e: number;
  rigid_n: number;
  local_e: number;
  local_n: number;
  fold: number;
}

export interface RegionPayload {
  frame: string;
  region: string;
  region_label: string;
  source: string;
  citation: string;
  n_stations: number;
  rigid_pole: { lat: number; lon: number; rate_deg_myr: number };
  units: string;
  stations: StationRecord[];
}

export interface QuakeEvent {
  id: string;
  lat: number;
  lon: number;
  depth_km: number;
  mag: number;
  mag_type: string;
  time_ms: number;
}

export interface QuakePayload {
  region: string;
  source: string;
  window: { start: string; end: string };
  min_magnitude: number;
  completeness_note: string;
  n_events: number;
  events: QuakeEvent[];
}

export type LayerKind = "obs" | "rigid" | "residual" | "local";

// Return the (east, north) velocity for the chosen layer in mm/yr.
export function layerVelocity(s: StationRecord, layer: LayerKind): [number, number] {
  switch (layer) {
    case "obs":
      return [s.obs_e, s.obs_n];
    case "rigid":
      return [s.rigid_e, s.rigid_n];
    case "local":
      return [s.local_e, s.local_n];
    case "residual":
      return [s.obs_e - s.rigid_e, s.obs_n - s.rigid_n];
  }
}
