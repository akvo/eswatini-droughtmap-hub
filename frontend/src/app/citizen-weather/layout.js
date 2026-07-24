import "./citizen-weather.css";

export const metadata = {
  title: "Citizen Science Weather",
  description:
    "Monthly weather readings from community volunteers across Eswatini",
};

const CitizenWeatherLayout = ({ children }) => {
  return <div className="cw-app">{children}</div>;
};

export default CitizenWeatherLayout;
