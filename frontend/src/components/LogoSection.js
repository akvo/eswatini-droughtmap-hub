import { APP_SETTINGS } from "@/static/config";
import Image from "next/image";

const LogoSection = () => {
  return (
    <div
      className="w-full min-h-36 bg-image-login bg-no-repeat bg-center bg-cover"
      id="edm-about"
    >
      <div className="container w-full py-9 flex flex-col items-center justify-center gap-9">
        <h2 className="text-xl xl:text-2xl text-primary font-bold">
          ABOUT EDM
        </h2>
        <p className="w-5/12 text-center">{APP_SETTINGS.about}</p>
        <ul className="flex flex-row items-center gap-12 mb-12">
          <li>
            <Image
              src="/images/home-about-1.png"
              width={255}
              height={95}
              alt="Ministry of Agriculture"
            />
          </li>
          <li>
            <Image
              src="/images/home-about-2.png"
              width={255}
              height={95}
              alt="Ministry of Natural Resources"
            />
          </li>
          <li>
            <Image
              src="/images/home-about-3.png"
              width={255}
              height={95}
              alt="Ministry of Environment"
            />
          </li>
        </ul>
      </div>
    </div>
  );
};

export default LogoSection;
