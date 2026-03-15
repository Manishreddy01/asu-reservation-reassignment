const BASE = '/api/v1';

/**
 * @param {{ buildingId?: number, resourceType?: string }} opts
 * @returns {Promise<Array>}
 */
export async function fetchResources({ buildingId, resourceType } = {}) {
  const params = new URLSearchParams();
  if (buildingId != null)  params.set('building_id', buildingId);
  if (resourceType)        params.set('resource_type', resourceType);

  const res = await fetch(`${BASE}/resources?${params}`);
  if (!res.ok) throw new Error('Failed to load resources.');
  return res.json();
}

/** @returns {Promise<Array>} */
export async function fetchBuildings() {
  const res = await fetch(`${BASE}/buildings`);
  if (!res.ok) throw new Error('Failed to load buildings.');
  return res.json();
}
