(function() {
    function render(element, widget, helpers) {
        const props = widget.props || {};
        const path = props.path || "";
        const invert = !!props.invert;

        element.style.boxSizing = "border-box";
        element.style.border = "2px dashed #aaaaaa";
        element.style.backgroundColor = "#f5f5f5";
        element.style.display = "flex";
        element.style.alignItems = "center";
        element.style.justifyContent = "center";
        element.style.overflow = "hidden";

        if (path) {
            const filename = path.split("/").pop();

            element.innerHTML = "";

            const img = document.createElement("img");
            img.style.maxWidth = "100%";
            img.style.maxHeight = "100%";
            img.style.objectFit = "contain";
            img.draggable = false;

            if (invert) {
                img.style.filter = "invert(1)";
            }

            img.onerror = () => {
                element.innerHTML = "<div style='text-align:center;color:#666;font-size:11px;padding:8px;line-height:1.4;'>" +
                    "🖼️<br/><strong>" + filename + "</strong><br/>" +
                    "<span style='color:#999;font-size:9px;'>" +
                    (invert ? "(inverted) " : "") +
                    widget.width + "×" + widget.height + "px<br/>" +
                    "File not found or not accessible</span></div>";
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
                element.style.position = "relative";
                element.appendChild(overlay);
            };

            const proxyUrl = "/api/reterminal_dashboard/image_proxy?path=" + encodeURIComponent(path);
            img.src = proxyUrl;
            element.appendChild(img);
        } else {
            const placeholder = document.createElement("div");
            placeholder.style.textAlign = "center";
            placeholder.style.color = "#aaa";
            placeholder.style.fontSize = "11px";
            placeholder.innerHTML = "🖼️<br/>Image Widget<br/><span style='font-size:9px;color:#ccc;'>Enter path in properties →</span>";
            element.appendChild(placeholder);
        }
    }

    if (window.FeatureRegistry) {
        window.FeatureRegistry.register("image", { render });
    }
})();
