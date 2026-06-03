// Real satellite/aerial imagery of each area, by coordinates, via Esri World Imagery — free,
// no API key, hotlinkable. Coordinates are approximate centroids of Bahria Town Rawalpindi
// phases (Phase 4 Civic Centre is verified) and nearby Rawalpindi localities.

const COORDS: Record<string, [number, number]> = {
  // [lat, lng]
  "Phase 1": [33.5300, 73.1130],
  "Phase 2": [33.5360, 73.1180],
  "Phase 3": [33.5430, 73.1210],
  "Phase 4": [33.5500, 73.1245], // Civic Centre (the circular boulevard)
  "Phase 5": [33.5450, 73.1320],
  "Phase 6": [33.5390, 73.1290],
  "Phase 7": [33.5550, 73.1400],
  "Phase 8": [33.5600, 73.1350],
  "Bahria Hghts": [33.5500, 73.1255],
  "Chaklala 3": [33.5950, 73.1050],
  "Media Town": [33.6050, 73.0950],
  "Westridge": [33.5880, 73.0470],
  "Satellite Twn": [33.6340, 73.0680],
};

const DEFAULT: [number, number] = [33.5500, 73.1245];

// Deterministic small jitter so listings in the same phase don't all show the identical frame.
function jitter(seed: number): [number, number] {
  const dy = (((seed * 29) % 9) - 4) / 2000; // ~±0.002 lat
  const dx = (((seed * 53) % 9) - 4) / 1500; // ~±0.0027 lng
  return [dy, dx];
}

export function placeImage(phase: string, seed = 0, w = 800, h = 400): string {
  const [baseLat, baseLng] = COORDS[phase] ?? DEFAULT;
  const [dy, dx] = jitter(seed);
  const lat = baseLat + dy;
  const lng = baseLng + dx;
  const latHalf = 0.0024;
  const lngHalf = 0.0048;
  const bbox = `${lng - lngHalf},${lat - latHalf},${lng + lngHalf},${lat + latHalf}`;
  return (
    "https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/export" +
    `?bbox=${bbox}&bboxSR=4326&imageSR=4326&size=${w},${h}&format=jpg&f=image`
  );
}
