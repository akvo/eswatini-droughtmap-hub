import Link from "next/link";
import { Button } from "antd";

const FeedbackSection = () => {
  return (
    <div className="relative w-full overflow-hidden bg-primary p-8 flex items-start justify-between gap-8">
      {/* Topo pattern: source is gray lines on white, so invert + screen
          drops the white bg (blue preserved) and shows lines as faint highlights */}
      <div
        aria-hidden
        className="absolute inset-0 bg-image-login bg-cover bg-center pointer-events-none [filter:invert(1)] [mix-blend-mode:screen]"
      />
      <div className="relative flex flex-col gap-2 max-w-3xl text-white">
        <h2 className="text-2xl font-bold leading-[30px]">
          Your Feedback Matters
        </h2>
        <p className="text-base leading-6">
          Get in touch with us for support or feedback on the Eswatini Drought
          Monitor platform.
        </p>
      </div>
      <Link href="/feedback" className="relative shrink-0">
        <Button>Get in touch</Button>
      </Link>
    </div>
  );
};

export default FeedbackSection;
