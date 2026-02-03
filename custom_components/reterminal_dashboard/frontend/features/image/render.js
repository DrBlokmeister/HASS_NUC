(() => {
    // Check if we're running in Home Assistant (has API) or offline (file:// protocol)
    const isOffline = () => window.location.protocol === 'file:' || !window.location.hostname;

    const render = (el, widget, { getColorStyle }) => {
        const props = widget.props || {};
        const url = (props.url || "").trim();
        // Strip any surrounding quotes and whitespace from path
        const path = (props.path || "").replace(/^"|"$/g, '').trim();
        const invert = !!props.invert;

        el.style.boxSizing = "border-box";
        el.style.backgroundColor = "#f5f5f5";
        el.style.display = "flex";
        el.style.alignItems = "center";
        el.style.justifyContent = "center";
        el.style.overflow = "hidden";
        el.style.color = "#666";

        // Clear previous content
        el.innerText = "";
        el.style.backgroundImage = "";

        // For local ESPHome paths, use the image_proxy endpoint (or direct path if offline)
        if (path) {
            const filename = path.split(/[/\\]/).pop() || path;
            el.innerHTML = "";

            const img = document.createElement("img");
            img.style.maxWidth = "100%";
            img.style.maxHeight = "100%";
            img.style.objectFit = "contain";
            img.draggable = false;

            if (invert) {
                img.style.filter = "invert(1)";
            }

            img.onerror = () => {
                // Show placeholder with file info when image can't be loaded
                const offlineNote = isOffline() ? "<br/><span style='color:#e67e22;font-size:8px;'>⚠️ Offline mode - preview in HA</span>" : "";
                el.innerHTML = "<div style='text-align:center;color:#666;font-size:11px;padding:8px;line-height:1.4;'>" +
                    "🖼️<br/><strong>" + filename + "</strong><br/>" +
                    "<span style='color:#999;font-size:9px;'>" +
                    (invert ? "(inverted) " : "") +
                    widget.width + "×" + widget.height + "px</span>" + offlineNote + "</div>";
            };

            img.onload = () => {
                const overlay = document.createElement("div");
                overlay.style.position = "absolute";
                overlay.style.bottom = "2px";
                overlay.style.right = "2px";
                overlay.style.background = "rgba(0,0,0,0.6)";
                overlay.style.color = "white";
                overlay.style.padding = "2px 4px";
                overlay.style.fontSize = "8px";
                overlay.style.borderRadius = "2px";
                overlay.textContent = filename + " • " + widget.width + "×" + widget.height + "px";
                // el.style.position = "relative"; // REMOVED: Breaks absolute positioning
                el.appendChild(overlay);
            };

            // Determine the image source based on environment
            let imgSrc;
            if (isOffline()) {
                // Offline: try to load directly from path (works for absolute local paths)
                // Convert Windows paths if needed
                if (path.match(/^[A-Za-z]:\\/)) {
                    // Windows absolute path like C:\Users\...
                    imgSrc = "file:///" + path.replace(/\\/g, '/');
                } else if (path.startsWith('/config/')) {
                    // ESPHome path - can't preview offline, show placeholder
                    imgSrc = null;
                } else {
                    // Try as-is (relative or other path)
                    imgSrc = path;
                }
            } else {
                // Online: use Home Assistant image_proxy endpoint
                imgSrc = "/api/reterminal_dashboard/image_proxy?path=" + encodeURIComponent(path);
            }

            if (imgSrc) {
                img.src = imgSrc;
                el.appendChild(img);
            } else {
                // Can't preview this path offline - show informative placeholder
                el.innerHTML = "<div style='text-align:center;color:#666;font-size:11px;padding:8px;line-height:1.4;'>" +
                    "🖼️<br/><strong>" + filename + "</strong><br/>" +
                    "<span style='color:#999;font-size:9px;'>" +
                    (invert ? "(inverted) " : "") +
                    widget.width + "×" + widget.height + "px</span><br/>" +
                    "<span style='color:#e67e22;font-size:8px;'>⚠️ Preview available in Home Assistant</span></div>";
            }
            return;
        }

        if (url) {
            const img = document.createElement("img");
            img.style.maxWidth = "100%";
            img.style.maxHeight = "100%";
            img.style.objectFit = "contain";
            img.draggable = false;

            if (invert) {
                img.style.filter = "invert(1)";
            }

            img.onerror = () => {
                el.innerHTML = "<div style='text-align:center;color:#666;font-size:11px;padding:8px;line-height:1.4;'>" +
                    "🖼️<br/><strong>Image</strong><br/>" +
                    "<span style='color:#999;font-size:9px;'>" +
                    (invert ? "(inverted) " : "") +
                    "Load Failed</span></div>";
            };

            img.onload = () => {
                // Overlay info
                const filename = url.split("/").pop();
                const overlay = document.createElement("div");
                overlay.style.position = "absolute";
                overlay.style.bottom = "2px";
                overlay.style.right = "2px";
                overlay.style.background = "rgba(0,0,0,0.6)";
                overlay.style.color = "white";
                overlay.style.padding = "2px 4px";
                overlay.style.fontSize = "8px";
                overlay.style.borderRadius = "2px";
                overlay.textContent = filename;
                // el.style.position = "relative"; // REMOVED: Breaks absolute positioning
                el.appendChild(overlay);
            };

            img.src = url;
            el.appendChild(img);
        } else {
            // No path or URL set
            const placeholder = document.createElement("div");
            placeholder.style.textAlign = "center";
            placeholder.style.color = "#aaa";
            placeholder.style.fontSize = "11px";
            placeholder.innerHTML = "🖼️<br/>Image Widget<br/><span style='font-size:9px;color:#ccc;'>Enter path in properties →</span>";
            el.appendChild(placeholder);
        }
    };

    if (window.FeatureRegistry) {
        window.FeatureRegistry.register("image", { render });
    }
})();
