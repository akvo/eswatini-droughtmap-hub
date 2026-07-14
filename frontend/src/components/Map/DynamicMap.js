import { useEffect } from "react";
import Leaflet from "leaflet";
import * as ReactLeaflet from "react-leaflet";
import "leaflet/dist/leaflet.css";

import styles from "./Map.module.scss";

const { MapContainer, useMap } = ReactLeaflet;

// Leaflet caches its container size at init. Inside a clipped/absolutely
// positioned parent (e.g. the compare slider) that size is wrong, so the map
// paints offset or blank until it re-measures.
const ResizeHandler = () => {
  const map = useMap();

  useEffect(() => {
    const invalidate = () => map.invalidateSize();
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
