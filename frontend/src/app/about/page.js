import AboutSection from "@/components/AboutSection";
import AboutSectionChild from "@/components/AboutSectionChild";
import { FeedbackSection } from "@/components";
import { headerConfig } from "@/static/about/header";
import { howCdiComputedConfig } from "@/static/about/how-cdi-computed";
import { whatCdiCategoriesMeanConfig } from "@/static/about/what-cdi-categories-mean";
import { whoInvolvedValidationConfig } from "@/static/about/who-involved-validation";

const AboutPage = () => {
  return (
    <div className="w-full">
      {/* Header */}
      <div className="relative w-screen left-1/2 -translate-x-1/2">
        <div
          aria-hidden
          className="absolute inset-0 bg-dhi-pattern bg-cover bg-center bg-no-repeat opacity-30 pointer-events-none"
        />
        <AboutSection
          title={headerConfig.title}
          titleSize="text-3xl"
          description={headerConfig.description}
          textAlign="text-center"
          className="relative container mx-auto"
        />
      </div>
      <div className="relative w-full h-[300px] md:h-[400px] overflow-hidden">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={headerConfig.image_url}
          alt={headerConfig.title}
          className="w-full h-full object-cover"
        />
      </div>

      {/* How is the CDI Computed? */}
      <div className="relative w-screen left-1/2 -translate-x-1/2 border-b border-gray-200">
        <AboutSection
          title={howCdiComputedConfig.title}
          description={howCdiComputedConfig.description}
          className="container mx-auto"
        >
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-6">
            {howCdiComputedConfig.children.map((child) => (
              <AboutSectionChild
                key={child.id}
                icon={child.icon}
                title={child.title}
                description={child.description}
                flex="col"
              />
            ))}
          </div>
        </AboutSection>
      </div>

      {/* What Do the CDI Categories Mean? */}
      <div className="relative w-screen left-1/2 -translate-x-1/2 border-b border-gray-200">
        <AboutSection
          title={whatCdiCategoriesMeanConfig.title}
          description={whatCdiCategoriesMeanConfig.description}
          className="container mx-auto"
        >
          <div className="w-full overflow-x-auto mt-6">
            <table className="w-full border border-gray-200 [&_td]:border-0 [&_th]:border-0 [&_tr]:border-b [&_tr]:border-gray-200 [&_tr:last-child]:border-0">
              <thead>
                <tr className="bg-gray-100 text-left text-sm text-[#606060]">
                  <th className="p-3 font-semibold">Category</th>
                  <th className="p-3 font-semibold">Description</th>
                  <th className="p-3 font-semibold">CDI Percentile</th>
                  <th className="p-3 font-semibold">Meaning</th>
                </tr>
              </thead>
              <tbody>
                {whatCdiCategoriesMeanConfig.children.map((row) => (
                  <tr key={row.id} className="text-sm text-[#606060]">
                    <td className="p-3">
                      <span
                        className="inline-block px-2 py-0.5 rounded text-xs font-semibold"
                        style={{
                          backgroundColor: row.color,
                          color:
                            row.color === "#730000" || row.color === "#e60000"
                              ? "#fff"
                              : "#333",
                        }}
                      >
                        {row.category}
                      </span>
                    </td>
                    <td className="p-3">{row.description}</td>
                    <td className="p-3">{row.percentile}</td>
                    <td className="p-3">{row.meaning}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </AboutSection>
      </div>

      {/* Who is Involved in Validation? */}
      <div className="relative w-screen left-1/2 -translate-x-1/2">
        <AboutSection
          title={whoInvolvedValidationConfig.title}
          description={whoInvolvedValidationConfig.description}
          className="container mx-auto pt-16 pb-8"
        >
          <div className="flex flex-col md:flex-row gap-8 mt-6">
            <div className="flex flex-col gap-6 md:w-1/2">
              {whoInvolvedValidationConfig.children.map((child, index) => (
                <AboutSectionChild
                  key={index}
                  icon={child.icon}
                  title={child.title}
                  flex="row"
                />
              ))}
            </div>
            {whoInvolvedValidationConfig.image_url && (
              <div className="relative md:w-1/2 h-[200px] overflow-hidden">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={whoInvolvedValidationConfig.image_url}
                  alt="Validation process"
                  className="w-full h-full object-cover"
                />
              </div>
            )}
          </div>
        </AboutSection>
      </div>

      {/* Feedback */}
      <div className="my-8">
        <FeedbackSection />
      </div>
    </div>
  );
};

export default AboutPage;
