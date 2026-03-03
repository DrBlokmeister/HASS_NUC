# AI Coding Agent Instructions for HASS_NUC

This Home Assistant configuration uses a modular package-based architecture. Below is essential knowledge for productivity.

## Project Architecture

**Core Structure:**
- **Configuration root** ([configuration.yaml](../configuration.yaml)): Main HA config loading packages from four categories
- **Packages** ([packages/](../packages/)): Organized as `areas/` (room-specific), `system/` (backend), `security/`, and `misc/`
- **ESPHome** ([esphome/](../esphome/)): ~60 firmware projects using YAML packages (templates/)
- **Custom Components** ([custom_components/](../custom_components/)): HACS integrations (Powercalc, Nordpool, Spook, etc.)
- **Frontend** ([lovelace/](../lovelace/), [decluttering-templates.yaml](../decluttering-templates.yaml)): Multiple dashboard views with reusable card templates

**Data Flow:** IoT devices (Zigbee/Shelly/ESPHome) → HA entities → Automations/Scripts → UI/Notifications → MariaDB recorder

## Configuration Patterns

**Package Structure** - Each area has consistent sections:
```yaml
homeassistant:
  customize:           # Set icons/attributes per entity
  customize_glob:      # Glob patterns for groups
automation:            # Automations specific to this area
script:                # Scripts for this area
sensor:                # Template/derived sensors
binary_sensor:         # Motion, door, occupancy, etc.
input_boolean:         # Toggles (vacation mode, guest mode, etc.)
input_number:          # Sliders (temperatures, thresholds)
input_select:          # Dropdowns (cleaning modes, scenes)
light:                 # Light groups for this area
climate:               # Climate control (rarely used)
```

**Database Optimization:** Recorder includes/excludes are aggressive—only record essential sensors (energy, occupancy). Battery sensors excluded but tracked via `battery_notes` custom component. High-frequency sensors (HX711 scale readings) explicitly excluded.

**ESPHome Packaging:** Device configs heavily reference shared templates in `esphome/templates/` for DRY components (WiFi, OTA, API, etc.). AQM devices use structured sub-packages (`climate.yaml`, `co2.yaml`, etc.).

## Critical Patterns to Preserve

1. **Entity Naming**: `<domain>.<device>_<attribute>` (e.g., `sensor.plug_nas_energy_today`, `binary_sensor.bedroom_motion_sensor`)
2. **Automation Mode**: Preserve `mode: single` or `mode: queued` declarations—these control concurrency behavior
3. **Template Sensors**: Use `template:` domain (not deprecated `template.sensor`). Group high-frequency updates with `availability_template`
4. **Recorder Exclusions**: Always exclude battery entities created by `battery_notes`, internal timestamps (`date_time`, `time_date`), and high-frequency raw values
5. **Decluttering Templates**: Card templates use `[[parameter]]` syntax for reuse across dashboards
6. **Script Consistency**: All scripts must define `mode` to prevent conflicts (motion-triggered automations often use scripts)

## Workflow & Key Commands

**Validation**: Home Assistant automatically validates YAML syntax on startup. Check `home-assistant.log` for errors after modifying `configuration.yaml`.

**ESPHome Build**: Configs are compiled to `.bin` files—USB serial connection required for flashing.

**Database**: MariaDB runs in addon—use `mysql://homeassistant:...@core-mariadb/homeassistant` URL. Aggressive purging enabled (14 days max storage).

**Dashboards**: Multiple views in [ui-lovelace.yaml](../ui-lovelace.yaml), [limited-lovelace.yaml](../limited-lovelace.yaml), [epaper-lovelace.yaml](../epaper-lovelace.yaml) for mobile/display use.

## Integration Points

- **Hyperion Ambilight**: UDP E1.31 protocol to AtmoOrbs/Falcon LEGO builds
- **Vacuum automations**: Support three vacuum cleaners (Moeke, Argus, Alfred) with shared scripts
- **Custom Components**: Spook (enhanced UI), Powercalc (energy estimation), Nordpool (electricity pricing)
- **InfluxDB**: Parallel time-series database for long-term trends (separate from MariaDB)

---

## Commit Message Guidelines

For **all commits**, follow this structure:

- Start with **two emojis**: first for category, second for change type
- Add a **single space**, then write a concise, imperative sentence (max 72 characters, no period)
- Use [gitmoji.dev](https://gitmoji.dev/) for change-type emojis (2nd emoji)
- If unsure about category, **omit it**—use only the change-type emoji

### Category Emojis (1st)

| Category             | Emoji |
| -------------------- | :---: |
| Dashboard (Lovelace) | 🖼️    |
| Automations          | 🤖    |
| Scripts              | 🎬    |
| Template Sensors     | 🧮    |
| YAML Cleanup         | 🧹    |
| New Integration      | 🧩    |
| Git/Docs/Meta        | 📚    |
| Secrets/Env/Keys     | 🔐    |
| UI Theme             | 🎨    |
| Add-on Updates       | ⬆️    |
| Logging / Debug      | 🪵    |
| Firmware             | 📦    |

> ⚠️ Only use 🖼️ for files in `lovelace/` folder starting with `view_`

---

## Change-Type Emojis (2nd emoji)

Use gitmoji for this:
https://gitmoji.dev/

Some common examples:
| Type        | Emoji | Description                 |
|-------------|:-----:|-----------------------------|
| New         | ➕    | Adding a new feature        |
| Fix         | 🐛    | Bugfix                      |
| Refactor    | ♻️    | Code improvement            |
| Remove      | ➖    | Removing code or files      |
| Feature     | ✨    | Significant new capability  |
| Cleanup     | 🔥    | Removing unused code/config |
| Docs        | 📝    | Documentation               |

---

## Examples

These examples are here to **teach Copilot** the expected format:

```text
🎨➕ Refactor device tracker card layout and add missing entities
🖼️➕ Add person badges and improve sensor activity view on security dashboard
🧮🐛 Fix crash in vacuum power estimate sensors due to missing battery level
🤖♻️ Restructure morning routine automation for readability
📚➖ Remove deprecated gitignore rules
🧩✨ Add Spook custom component for enhanced UI controls

