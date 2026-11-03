import { installIgnorableRejectionHandler, isIgnorableWindowRejection } from '../js/utils/ignorable_rejections.js';

const PANEL_TAG_NAME = 'esphome-designer-panel';
const PANEL_IFRAME_ID = 'esphome-designer-panel-frame';
const HA_AUTH_MESSAGE_TYPE = 'esphome-designer-ha-auth';
const HA_HASS_GLOBAL_KEY = '__ESPHOME_DESIGNER_HASS__';
const EDITOR_URL = '/esphome-designer/editor/index.html';
const PANEL_TITLE = 'ESPHome Designer';
const PANEL_HEADER_CLASS = 'esphome-designer-panel-header';
const HEADER_HEIGHT = 'calc(40px + var(--safe-area-inset-top, 0px))';
const MDI_MENU_PATH = 'M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z';
const SVG_NS = 'http://www.w3.org/2000/svg';

/**
 * Mirrors HA's ha-menu-button: when the sidebar collapses into a drawer, the
 * panel must provide its own toggle or the user cannot leave it (#321).
 * @param {any} hass
 * @param {boolean} narrow
 * @returns {boolean}
 */
export function shouldShowMenuButton(hass, narrow) {
    if (!hass || hass.kioskMode) {
        return false;
    }
    if (hass.auth?.external?.config?.hasSidebar === true) {
        return false;
    }
    return narrow || hass.dockedSidebar === 'always_hidden';
}

/**
 * @param {HTMLIFrameElement | null | undefined} iframe
 * @returns {boolean}
 */
export function iframeNeedsRehydration(iframe) {
    if (!iframe) {
        return true;
    }

    try {
        const frameLocation = iframe.contentWindow?.location?.href || '';
        if (frameLocation === 'about:blank') {
            return true;
        }

        const doc = iframe.contentDocument;
        if (!doc || doc.readyState === 'loading') {
            return false;
        }

        return !(
            doc.querySelector('.app-content')
            || doc.getElementById('canvasContainer')
            || doc.getElementById('canvas')
            || doc.getElementById('widgetPalette')
            || doc.getElementById('header-placeholder')
        );
    } catch {
        return false;
    }
}

/**
 * @param {unknown} reason
 * @returns {boolean}
 */
export function isIgnorableTransitionAbort(reason) {
    return isIgnorableWindowRejection(reason);
}

/**
 * @param {any} hass
 * @returns {string | null}
 */
function extractAccessToken(hass) {
    return (
        hass?.auth?.data?.access_token
        || hass?.connection?.options?.auth?.access_token
        || hass?.connection?._auth?.accessToken
        || null
    );
}

/**
 * @param {HTMLIFrameElement} iframe
 * @param {string | null} accessToken
 */
function syncIframeAuth(iframe, accessToken) {
    if (!accessToken) {
        return;
    }

    const payload = {
        type: HA_AUTH_MESSAGE_TYPE,
        accessToken,
    };
    const serialized = JSON.stringify(payload);
    iframe.name = serialized;

    try {
        iframe.contentWindow?.postMessage(payload, window.location.origin);
    } catch {
        // Ignore iframe timing races during initial navigation.
    }
}

installIgnorableRejectionHandler();

export class ESPHomeDesignerPanel extends HTMLElement {
    constructor() {
        super();
        this._rendered = false;
        this._iframe = null;
        this._header = null;
        this._hass = null;
        this._narrow = false;
        this._boundWake = () => {
            if (document.visibilityState === 'hidden') {
                return;
            }
            this._rehydrateIframeIfNeeded();
        };
        this._lifecycleHandlersAttached = false;
    }

    set hass(value) {
        this._hass = value;
        try {
            window[HA_HASS_GLOBAL_KEY] = value;
        } catch {
            // Ignore global exposure failures in restricted runtimes.
        }
        this._syncAuth();
        this._syncHeader();
    }

    get narrow() {
        return this._narrow;
    }

    set narrow(value) {
        this._narrow = Boolean(value);
        this._syncHeader();
    }

    connectedCallback() {
        this._applyHostStyles();
        this._attachLifecycleHandlers();

        if (this._rendered) {
            this._rehydrateIframeIfNeeded();
            return;
        }

        this._rendered = true;
        this._mountFreshIframe();
    }

    disconnectedCallback() {
        this._detachLifecycleHandlers();
    }

    _syncAuth() {
        if (!this._iframe) {
            return;
        }

        syncIframeAuth(this._iframe, extractAccessToken(this._hass));
    }

    _applyHostStyles() {
        this.style.display = 'flex';
        this.style.flexDirection = 'column';
        // HA 2026.8 no longer supplies custom panels with a definite height.
        // A definite height is also required for the iframe's percentage height.
        this.style.height = '100vh';
        this.style.height = '100dvh';
        this.style.minHeight = '0';
        this.style.overflow = 'hidden';
    }

    _createIframe() {
        const iframe = document.createElement('iframe');
        iframe.id = PANEL_IFRAME_ID;
        iframe.src = EDITOR_URL;
        iframe.title = 'ESPHome Designer';
        iframe.style.width = '100%';
        // Fills whatever the optional header leaves over.
        iframe.style.flex = '1 1 0';
        iframe.style.minHeight = '0';
        iframe.style.border = '0';
        iframe.style.display = 'block';
        iframe.referrerPolicy = 'same-origin';
        iframe.addEventListener('load', () => this._syncAuth());
        return iframe;
    }

    _createHeader() {
        const header = document.createElement('div');
        header.className = PANEL_HEADER_CLASS;
        Object.assign(header.style, {
            display: 'flex',
            alignItems: 'center',
            flex: '0 0 auto',
            height: HEADER_HEIGHT,
            boxSizing: 'border-box',
            padding: 'var(--safe-area-inset-top, 0px) 16px 0 4px',
            backgroundColor: 'var(--app-header-background-color, var(--primary-color, #03a9f4))',
            color: 'var(--app-header-text-color, white)',
            borderBottom: 'var(--app-header-border-bottom, none)',
            fontSize: 'var(--ha-font-size-l, 20px)',
            fontFamily: 'var(--ha-font-family-body, inherit)',
        });

        const button = document.createElement('button');
        button.type = 'button';
        button.setAttribute('aria-label', this._hass?.localize?.('ui.sidebar.sidebar_toggle') || 'Sidebar toggle');
        Object.assign(button.style, {
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '40px',
            height: '40px',
            padding: '0',
            border: '0',
            borderRadius: '50%',
            background: 'transparent',
            color: 'inherit',
            cursor: 'pointer',
        });
        button.addEventListener('click', () => {
            this.dispatchEvent(new CustomEvent('hass-toggle-menu', { bubbles: true, composed: true }));
        });

        const svg = document.createElementNS(SVG_NS, 'svg');
        svg.setAttribute('viewBox', '0 0 24 24');
        svg.setAttribute('width', '20');
        svg.setAttribute('height', '20');
        svg.setAttribute('aria-hidden', 'true');
        const path = document.createElementNS(SVG_NS, 'path');
        path.setAttribute('d', MDI_MENU_PATH);
        path.setAttribute('fill', 'currentColor');
        svg.appendChild(path);
        button.appendChild(svg);

        const title = document.createElement('div');
        title.textContent = PANEL_TITLE;
        Object.assign(title.style, {
            marginInlineStart: '8px',
            flexGrow: '1',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
        });

        header.append(button, title);
        return header;
    }

    _syncHeader() {
        if (!this._iframe) {
            return;
        }

        if (!shouldShowMenuButton(this._hass, this._narrow)) {
            this._header?.remove();
            this._header = null;
            return;
        }

        if (!this._header) {
            this._header = this._createHeader();
        }
        if (this._header.nextSibling !== this._iframe) {
            // Inserting a sibling leaves the iframe attached, so it does not reload.
            this.insertBefore(this._header, this._iframe);
        }
    }

    _mountFreshIframe() {
        const iframe = this._createIframe();
        this.replaceChildren(iframe);
        this._iframe = iframe;
        this._syncAuth();
        this._syncHeader();
    }

    _rehydrateIframeIfNeeded() {
        if (!this._iframe || !this._iframe.isConnected) {
            this._mountFreshIframe();
            return;
        }

        if (iframeNeedsRehydration(this._iframe)) {
            this._mountFreshIframe();
            return;
        }

        this._syncAuth();
    }

    _attachLifecycleHandlers() {
        if (this._lifecycleHandlersAttached) {
            return;
        }

        document.addEventListener('visibilitychange', this._boundWake);
        window.addEventListener('focus', this._boundWake);
        window.addEventListener('pageshow', this._boundWake);
        this._lifecycleHandlersAttached = true;
    }

    _detachLifecycleHandlers() {
        if (!this._lifecycleHandlersAttached) {
            return;
        }

        document.removeEventListener('visibilitychange', this._boundWake);
        window.removeEventListener('focus', this._boundWake);
        window.removeEventListener('pageshow', this._boundWake);
        this._lifecycleHandlersAttached = false;
    }
}

if (!customElements.get(PANEL_TAG_NAME)) {
    customElements.define(PANEL_TAG_NAME, ESPHomeDesignerPanel);
}
