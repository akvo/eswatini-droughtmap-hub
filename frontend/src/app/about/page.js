import { auth } from "@/lib";
import { LogoSection, Navbar } from "@/components";

const AboutPage = async () => {
  const session = await auth.getSession();
  return (
    <div className="w-full min-h-screen">
      <Navbar session={session} />
      <div className="container w-full h-full relative space-y-4 xl:space-y-8 pt-3 pb-9">
        <div className="w-full space-y-2">
          <div className="w-full border-b border-b-neutral-200 pb-4">
            <h1 className="text-2xl xl:text-3xl font-bold text-gray-800">
              About Eswatini Drought Monitor
            </h1>
          </div>
        </div>
        <p className="text-gray-700">
          EDM is a platform for exploring and sharing historical maps. It brings
          together a diverse range of historical maps from libraries around the
          world. With a growing selection of maps - EDM is a great resource for
          students, historians and history enthusiasts.
        </p>
        <h2 className="text-xl font-semibold text-gray-800">Drought Monitor</h2>
        <p className="text-gray-700">
          The drought monitor provides up-to-date information on drought
          conditions across different regions. It helps in understanding the
          severity and impact of droughts, enabling better planning and response
          strategies.
        </p>
        <h2 className="text-xl font-semibold text-gray-800">Contact Information</h2>
        <p className="text-gray-700">For more information, please contact us at:</p>
        <ul className="list-disc list-inside text-gray-700">
          <li>Email: info@ndma.org</li>
          <li>Phone: +123-456-7890</li>
        </ul>
        <h2 className="text-xl font-semibold text-gray-800">Data and Drought Severity</h2>
        <p className="text-gray-700">
          Our datasets include various indicators of drought severity, such as
          precipitation levels, soil moisture, and vegetation health. These
          datasets are crucial for analyzing and predicting drought conditions.
        </p>
        <h2 className="text-xl font-semibold text-gray-800">Resources and Tools</h2>
        <p className="text-gray-700">
          Access a range of resources for drought monitoring and planning,
          including interactive maps, data visualization tools, and reports
          provided by our partners.
        </p>
      </div>
      <LogoSection />
    </div>
  );
};

export default AboutPage;
