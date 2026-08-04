import { Footer, LogoSection } from "@/components";
import "./citizen-weather.css";
import { cwThemeVars } from "@/static/cw-theme";

export const metadata = {
  title: "Citizen Science Weather",
  description:
    "Monthly weather readings from community volunteers across Eswatini",
};

const CitizenWeatherLayout = ({ children }) => {
  return (
    <>
      <div className="cw-app" style={cwThemeVars}>
        {children}
        <div className="w-full bg-white border-t border-cardBorder">
          <LogoSection />
        </div>
      </div>
      <Footer />
    </>
  );
};

export default CitizenWeatherLayout;
