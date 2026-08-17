// Section separators run edge-to-edge in the design while the content stays in
// the shell's centered container — same breakout idiom used across the app.
const SectionLine = () => (
  <hr className="relative left-1/2 w-screen -translate-x-1/2 border-t border-cardBorder" />
);

export default SectionLine;
