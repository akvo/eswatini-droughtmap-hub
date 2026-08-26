import { useEffect } from "react";
import Leaflet from "leaflet";
import * as ReactLeaflet from "react-leaflet";
import "leaflet/dist/leaflet.css";

import styles from "./Map.module.scss";

const { MapContainer, useMap } = ReactLeaflet;

// Set by the National Overview PDF export while it prepares a print. See
// app/print.css and track-1/national-overview-pdf-export.md D-10.
const PRINTING_CLASS = "printing";

const isPrinting = () =>
  typeof document !== "undefined" &&
  document.documentElement.classList.contains(PRINTING_CLASS);

// The union of every drawn layer's extent — what has to stay visible.
const contentBounds = (map) => {
  let bounds = null;
  map.eachLayer((layer) => {
    if (typeof layer.getBounds !== "function") {
      return;
    }
    const b = layer.getBounds();
    if (!b?.isValid?.()) {
      return;
    }
    bounds = bounds ? bounds.extend(b) : Leaflet.latLngBounds(b);
  });
  return bounds;
};

// Leaflet caches its container size at init. Inside a clipped/absolutely
// positioned parent (e.g. the compare slider) that size is wrong, so the map
// paints offset or blank until it re-measures.
const ResizeHandler = () => {
  const map = useMap();

  useEffect(() => {
    // Saved on the way into a print so the on-screen view can be put back
    // exactly as the user left it.
    let savedView = null;

    const invalidate = () => {
      map.invalidateSize();

      if (isPrinting()) {
        // invalidateSize preserves zoom, so a container that got shorter for
        // print simply shows LESS of the map — every one of these maps is a
        // fixed center + zoom 9 with no fitBounds anywhere, and at zoom 9 the
        // country is ~580px tall against a 480px print box. Re-measuring can
        // never fix that; only re-fitting can.
        const bounds = contentBounds(map);
        if (bounds) {
          if (!savedView) {
            savedView = {
              center: map.getCenter(),
              zoom: map.getZoom(),
              zoomSnap: map.options.zoomSnap,
            };
          }
          // fitBounds snaps to whole zoom levels by default, so a map needing
          // zoom 8.9 drops to 8 and prints at half the size it could. Paper is
          // not interactive — there is no reason to quantise the scale.
          map.options.zoomSnap = 0;
          map.fitBounds(bounds, { animate: false, padding: [12, 12] });
        }
        return;
      }

      if (savedView) {
        map.options.zoomSnap = savedView.zoomSnap;
        map.setView(savedView.center, savedView.zoom, { animate: false });
        savedView = null;
      }
    };

    invalidate();
    const observer = new ResizeObserver(invalidate);
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map]);

  return null;
};

const Map = ({ children, className, width, height, ...rest }) => {
  let mapClassName = styles.map;

  if (className) {
    mapClassName = `${mapClassName} ${className}`;
  }

  useEffect(() => {
    (async function init() {
      delete Leaflet.Icon.Default.prototype._getIconUrl;
      Leaflet.Icon.Default.mergeOptions({
        iconRetinaUrl: "/leaflet/images/marker-icon-2x.png",
        iconUrl: "/leaflet/images/marker-icon.png",
        shadowUrl: "/leaflet/images/marker-shadow.png",
      });
    })();
  }, []);

  return (
    <MapContainer className={mapClassName} attributionControl={false} {...rest}>
      <ResizeHandler />
      {children(ReactLeaflet, Leaflet)}
    </MapContainer>
  );
};

export default Map;
