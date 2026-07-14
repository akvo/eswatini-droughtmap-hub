import {
  DataRetrievalIcon,
  ProcessingIcon,
  WeightAdjustmentIcon,
  CDIMapGenIcon,
  ValidationIcon,
  FinalPublicationIcon,
} from "./icons";

export const howCdiComputedConfig = {
  title: "How is the CDI Computed?",
  description:
    "The CDI is generated in a mostly automated process that includes the following steps:",
  children: [
    {
      id: 1,
      icon: DataRetrievalIcon,
      title: "Data Retrieval",
      description:
        "The system checks for the latest datasets from global sources, and automatically downloads and stores LST, NDVI, SPI, and Soil Moisture data.",
    },
    {
      id: 2,
      icon: ProcessingIcon,
      title: "Processing",
      description:
        "Computes percentile ranks and long-term trends using 40+ years of data where available.",
    },
    {
      id: 3,
      icon: WeightAdjustmentIcon,
      title: "Weight Adjustment",
      description:
        "If needed, experts can change the weight of each dataset depending on data quality or relevance.",
    },
    {
      id: 4,
      icon: CDIMapGenIcon,
      title: "CDI Map Generation",
      description:
        "Monthly drought maps (CDI) are produced indicating the drought levels per Inkundla (region).",
    },
    {
      id: 5,
      icon: ValidationIcon,
      title: "Validation",
      description:
        "The Technical Working Group (TWG) reviews the maps and provides expert feedback.",
    },
    {
      id: 6,
      icon: FinalPublicationIcon,
      title: "Final Publication",
      description:
        "Once validated, the CDI is published and made available to the public on this platform.",
    },
  ],
};
