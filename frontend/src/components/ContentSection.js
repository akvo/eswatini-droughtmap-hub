import classNames from "classnames";

// Heading + supporting copy + content, the section shape shared by the public
// pages. Pass `description` an array to get the design's two-column paragraphs.
const ContentSection = ({
  title,
  titleSize = "text-3xl",
  description,
  textAlign = "text-left",
  // Caps a single supporting paragraph. Body copy is 768px (max-w-3xl) in the
  // design; the centered hero is 720px (Figma 5416:116338). Ignored when
  // `description` is an array — those paragraphs are the full-width two-column
  // pair and cap themselves at half the container.
  descriptionWidth = "max-w-3xl",
  children,
  className = "",
}) => {
  const descriptions = Array.isArray(description) ? description : [description];
  return (
    <section className={classNames("w-full py-8", textAlign, className)}>
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
                [descriptionWidth]: descriptions.length === 1,
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

export default ContentSection;
