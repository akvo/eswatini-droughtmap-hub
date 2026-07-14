import classNames from "classnames";

const AboutSection = ({
  title,
  titleSize = "text-3xl",
  description,
  textAlign = "text-left",
  children,
  className = "",
}) => {
  const descriptions = Array.isArray(description) ? description : [description];
  return (
    <section className={classNames("w-full py-16", textAlign, className)}>
      {title && (
        <h2 className={classNames("font-bold text-[#333333] mb-4", titleSize)}>
          {title}
        </h2>
      )}
      {description && (
        <div
          className={classNames("mb-8", {
            "grid grid-cols-1 md:grid-cols-2 gap-6": descriptions.length > 1,
          })}
        >
          {descriptions.map((text, i) => (
            <p
              key={i}
              className={classNames("text-base leading-7 text-[#606060]", {
                "max-w-3xl": descriptions.length === 1,
                "mx-auto":
                  textAlign === "text-center" && descriptions.length === 1,
              })}
            >
              {text}
            </p>
          ))}
        </div>
      )}
      {children}
    </section>
  );
};

export default AboutSection;
