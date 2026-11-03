const PROFILE_METADATA_KEYS = new Set([
    'name',
    'legacyAliasFor',
    'isUntestedProfile',
    'isComingSoon',
    'isUnavailable',
    'unavailableReason'
]);

/**
 * @param {unknown} value
 * @returns {string}
 */
function normalizeProfileName(value) {
    return String(value || '').toLowerCase().replace(/[^a-z0-9]/g, '');
}

/**
 * Deterministic serialization for profile data whose object-key order is not
 * part of its identity.
 *
 * @param {unknown} value
 * @returns {string}
 */
function stableSerialize(value) {
    if (Array.isArray(value)) {
        return `[${value.map(stableSerialize).join(',')}]`;
    }
    if (value && typeof value === 'object') {
        const entries = Object.entries(value)
            .filter(([, item]) => item !== undefined)
            .sort(([left], [right]) => left.localeCompare(right));
        return `{${entries.map(([key, item]) => `${JSON.stringify(key)}:${stableSerialize(item)}`).join(',')}}`;
    }
    return JSON.stringify(value);
}

/**
 * @param {Record<string, any>} profile
 * @returns {string}
 */
function hardwareDefinitionFingerprint(profile) {
    const hardwareDefinition = Object.fromEntries(
        Object.entries(profile).filter(([key]) => !PROFILE_METADATA_KEYS.has(key))
    );
    return stableSerialize(hardwareDefinition);
}

/**
 * Find duplicate or invalid device-profile declarations.
 *
 * Intentional compatibility aliases must declare `legacyAliasFor`. Canonical
 * profiles must have unique normalized names, hardware packages, and hardware
 * definitions. Profiles may still share a display controller or resolution as
 * long as the rest of their hardware definition differs.
 *
 * @param {Record<string, Record<string, any>>} profiles
 * @param {string[]} [supportedIds=[]]
 * @returns {string[]}
 */
export function findDeviceProfileConflicts(profiles, supportedIds = []) {
    const errors = [];
    const supported = new Set(supportedIds);
    const names = new Map();
    const packages = new Map();
    const definitions = new Map();

    for (const [id, profile] of Object.entries(profiles)) {
        if (!profile || typeof profile !== 'object') {
            errors.push(`${id} is not a device profile object`);
            continue;
        }

        if (Object.hasOwn(profile, 'legacyAliasFor')) {
            const targetId = profile.legacyAliasFor;
            if (typeof targetId !== 'string' || !targetId.trim()) {
                errors.push(`${id} has an invalid legacyAliasFor target`);
                continue;
            }

            const target = profiles[targetId];
            if (!target) {
                errors.push(`${id} points to missing legacy alias target ${targetId}`);
                continue;
            }
            if (target.legacyAliasFor) {
                errors.push(`${id} must point directly to a canonical profile, not alias ${targetId}`);
            }
            if (hardwareDefinitionFingerprint(profile) !== hardwareDefinitionFingerprint(target)) {
                errors.push(`${id} does not match hardware definition of ${targetId}`);
            }
            if (supported.has(id)) {
                errors.push(`${id} is a legacy alias but is included in SUPPORTED_DEVICE_IDS`);
            }
            continue;
        }

        const normalizedName = normalizeProfileName(profile.name);
        if (normalizedName) {
            const existingNameId = names.get(normalizedName);
            if (existingNameId) {
                errors.push(`${id} duplicates normalized device name of ${existingNameId}`);
            } else {
                names.set(normalizedName, id);
            }
        }

        if (typeof profile.hardwarePackage === 'string' && profile.hardwarePackage.trim()) {
            const existingPackageId = packages.get(profile.hardwarePackage);
            if (existingPackageId) {
                errors.push(`${id} reuses hardware package ${profile.hardwarePackage} from ${existingPackageId}`);
            } else {
                packages.set(profile.hardwarePackage, id);
            }
        }

        const definition = hardwareDefinitionFingerprint(profile);
        const existingDefinitionId = definitions.get(definition);
        if (existingDefinitionId) {
            errors.push(`${id} duplicates hardware definition of ${existingDefinitionId}`);
        } else {
            definitions.set(definition, id);
        }
    }

    return errors;
}
