import Image from "next/image";
import {
  ContentSection,
  FeatureItem,
  FeedbackSection,
  SectionLine,
} from "@/components";
import { DroughtScore } from "@/components/DS";
import {
  formulaConfig,
  heroConfig,
  notesConfig,
  sectionsConfig,
} from "@/static/methodology";

/**
 * Static reference table (Figma 3217:34504 header / 3217:34521 cell).
 *
 * ponytail: a plain <table>, not antd's — nothing on this page sorts, filters
 * or paginates, and antd's Table would drag the whole page over the client
 * boundary for a fixed lookup grid.
 */
const ReferenceTable = ({ columns, rows }) => (
  <div className="w-full overflow-x-auto border border-cardBorder">
    <table className="w-full min-w-[720px] text-left">
      <thead>
        <tr className="border-b border-cardBorder bg-tableHeaderBg">
          {columns.map((col) => (
            <th
              key={col.key}
              style={col.width ? { width: col.width } : undefined}
              className="px-4 py-3 text-xs font-normal leading-[18px] text-textSecondary"
            >
              {col.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr
            key={index}
            className="border-b border-sectionBorder last:border-b-0"
          >
            {columns.map((col) => (
              <td
                key={col.key}
                className="h-16 px-4 py-3 text-sm leading-5 text-textSecondary"
              >
                {col.type === "drought" ? (
                  <DroughtScore level={row[col.key]} />
                ) : (
                  row[col.key]
                )}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

// One term of the risk product: a solid tile with the white glyph centred.
const FormulaTile = ({ iconSrc, label, className, size }) => (
  <div
    className={`flex shrink-0 items-center justify-center ${className}`}
    aria-label={label}
  >
    <Image src={iconSrc} alt={label} width={size} height={size} />
  </div>
);

const FormulaOperator = ({ children }) => (
  <span
    aria-hidden
    className="shrink-0 text-3xl font-light leading-none text-primary"
  >
    {children}
  </span>
);

const FormulaCard = () => (
  <section className="flex w-full flex-col items-center gap-4 border border-cardBorder bg-brandTint p-6 text-center md:p-10 mb-24">
    <h2 className="text-2xl font-bold leading-tight text-[#333333] md:text-[34px] md:leading-10">
      {formulaConfig.title}
    </h2>
    <p className="text-base leading-6 text-textSecondary">
      {formulaConfig.description}
    </p>
    <div className="w-full overflow-x-auto">
      <div className="mx-auto flex w-fit items-center gap-6 bg-white p-2">
        {/* Dashed group = the three multiplied components */}
        <div className="flex h-24 items-center gap-6 border-2 border-dashed border-[#3856A8] bg-brandTint px-2 md:gap-9">
          {formulaConfig.terms.map((term, index) => (
            <div key={term.key} className="flex items-center gap-6 md:gap-9">
              {index > 0 && <FormulaOperator>×</FormulaOperator>}
              <FormulaTile
                iconSrc={term.iconSrc}
                label={term.label}
                size={62}
                className="h-20 w-[78px] bg-primary"
              />
            </div>
          ))}
        </div>
        <FormulaOperator>=</FormulaOperator>
        {/* material-theme/key-colors/secondary — the alert red used for risk */}
        <FormulaTile
          iconSrc={formulaConfig.result.iconSrc}
          label={formulaConfig.result.label}
          size={64}
          className="size-24 bg-[#B10D0B]"
        />
      </div>
    </div>
  </section>
);

const MethodologyPage = () => {
  return (
    <div className="w-full">
      {/* Hero */}
      <div className="relative">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-dhi-pattern bg-cover bg-center bg-no-repeat opacity-30"
        />
        <ContentSection
          title={heroConfig.title}
          titleSize="text-[34px] leading-10"
          description={heroConfig.description}
          descriptionWidth="max-w-[620px]"
          textAlign="text-center"
          className="relative"
        />
      </div>

      <FormulaCard />

      {/* Rescale / lookup tables */}
      {sectionsConfig.map((section) => (
        <div key={section.key}>
          <SectionLine />
          <ContentSection
            title={section.title}
            description={section.description}
          >
            <ReferenceTable columns={section.columns} rows={section.rows} />
          </ContentSection>
        </div>
      ))}

      <SectionLine />

      {/* Notes on applying this methodology */}
      <ContentSection
        title={notesConfig.title}
        description={notesConfig.description}
      >
        <div className="grid grid-cols-1 gap-12 md:grid-cols-3">
          {notesConfig.children.map((note) => (
            <FeatureItem
              key={note.iconSrc}
              iconSrc={note.iconSrc}
              title={note.title}
              titleClass="text-xl font-medium leading-[30px]"
              flex="col"
            />
          ))}
        </div>
      </ContentSection>

      <div className="my-8">
        <FeedbackSection />
      </div>
    </div>
  );
};

export default MethodologyPage;
