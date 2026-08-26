"use client";

import { SettingOutlined } from "@ant-design/icons";
import { CloudSun } from "@/components/CitizenWeather/CWIcons";

const CWHeader = ({ isAdmin = false, subtitle, userName, userInitials }) => {
  return (
    <div className="cw-header">
      <div className={`cw-logo ${isAdmin ? "admin" : "observer"}`}>
        {isAdmin ? <SettingOutlined /> : <CloudSun size={18} />}
      </div>
      <div>
        <div className="cw-title">
          Citizen Science Weather{isAdmin ? " · Admin" : ""}
        </div>
        {subtitle && <div className="cw-subtitle">{subtitle}</div>}
      </div>
      {userName && (
        <div className="cw-user">
          <div
            className="cw-avatar"
            style={{
              background: isAdmin ? "var(--cw-navy)" : "var(--cw-gold)",
            }}
          >
            {userInitials}
          </div>
          <div>{userName}</div>
          <button className="cw-signout">Sign out</button>
        </div>
      )}
    </div>
  );
};

export default CWHeader;
