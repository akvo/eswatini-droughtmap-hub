"use client";

const CWHeader = ({
  isAdmin = false,
  subtitle,
  userName,
  userInitials,
}) => {
  return (
    <div className="cw-header">
      <div className={`cw-logo ${isAdmin ? "admin" : "observer"}`}>
        {isAdmin ? "⚙" : "🌦"}
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
            style={{ background: isAdmin ? "#1C2B3A" : "#F5B840" }}
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
