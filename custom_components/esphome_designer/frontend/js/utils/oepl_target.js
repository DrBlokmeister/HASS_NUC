const OEPL_PLACEHOLDER_TARGET = 'open_epaper_link.0000000000000000';

/**
 * OEPL 3.x drawcustom only accepts device targets; dotted ids are kept as legacy entity targets.
 * @param {string | undefined | null} id
 * @returns {{ entity_id: string } | { device_id: string }}
 */
export function getOEPLTarget(id) {
    const value = (id || '').trim() || OEPL_PLACEHOLDER_TARGET;
    return value.includes('.') ? { entity_id: value } : { device_id: value };
}
