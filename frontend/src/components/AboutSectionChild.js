import classNames from "classnames";

const AboutSectionChild = ({
  icon: Icon,
  title,
  description,
  flex = "col",
}) => {
  return (
    <div
      className={classNames("flex gap-3", {
        "flex-col": flex === "col",
        "flex-row items-center": flex === "row",
      })}
    >
      {Icon && (
        <div className="shrink-0 w-10 h-10 flex items-center justify-center bg-white border border-[#D2D2D2]">
          <Icon style={{ fontSize: 20, color: "#3E5EB9" }} />
        </div>
      )}
      <div className="flex flex-col gap-1">
        {title && (
          <h3 className="text-base font-semibold text-[#333333]">{title}</h3>
        )}
        {description && (
          <p className="text-sm leading-6 text-[#606060]">{description}</p>
        )}
      </div>
    </div>
  );
};

export default AboutSectionChild;
